import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import (
    Business, Job, Quote, QuoteStatus, MessageLog, MessageType, MessageStatus, Customer, MessageTriggerSource
)
from src.events import event_bus, QUOTE_SENT, JOB_PAID
from src.services.messaging_service import messaging_service

logger = logging.getLogger(__name__)

class AutomationService:
    def __init__(self):
        self._running = False
        self._worker_task = None

    def register_handlers(self):
        """Register event handlers for automation."""
        event_bus.subscribe(QUOTE_SENT, self.handle_quote_sent)
        event_bus.subscribe(JOB_PAID, self.handle_job_paid)
        logger.info("AutomationService handlers registered")

    async def handle_quote_sent(self, data: dict):
        """Logic for scheduling quote follow-up."""
        quote_id = data.get("quote_id")
        business_id = data.get("business_id")
        
        async with AsyncSessionLocal() as db:
            business = await db.get(Business, business_id)
            if not business or not business.workflow_auto_quote_followup:
                return
            
            # Follow-up will be picked up by the background checker
            logger.info(f"Quote {quote_id} sent, follow-up automation active for business {business_id}")

    async def handle_job_paid(self, data: dict):
        """Logic for scheduling review request."""
        job_id = data.get("job_id")
        business_id = data.get("business_id")
        customer_id = data.get("customer_id")
        
        async with AsyncSessionLocal() as db:
            business = await db.get(Business, business_id)
            if not business or not business.workflow_auto_review_requests:
                return
            
            # Review requests are also picked up by the background checker based on JOB_PAID status
            logger.info(f"Job {job_id} paid, review automation active for business {business_id}")

    async def check_and_trigger_automations(self):
        """
        Background job that scans for pending automations.
        - Quotes sent > X hours ago with no follow-up draft.
        - Jobs paid > X hours ago with no review request sent.
        """
        while self._running:
            try:
                await self._process_quote_followups()
                await self._process_review_requests()
            except Exception as e:
                logger.error(f"Error in automation checker: {e}")
            
            await asyncio.sleep(300) # Check every 5 minutes

    async def _process_quote_followups(self):
        async with AsyncSessionLocal() as db:
            # 1. Find businesses with quote follow-up enabled
            stmt = select(Business).where(Business.workflow_auto_quote_followup == True)
            result = await db.execute(stmt)
            businesses = result.scalars().all()
            
            for business in businesses:
                delay = business.workflow_quote_followup_delay_hrs or 48
                cutoff = datetime.now(timezone.utc) - timedelta(hours=delay)
                
                # 2. Find quotes in SENT status older than delay, with no follow-up draft yet
                # We check MessageLog for existing 'quote_followup' trigger_source for this quote
                stmt_quotes = (
                    select(Quote)
                    .join(Customer)
                    .where(
                        Quote.business_id == business.id,
                        Quote.status == QuoteStatus.SENT,
                        Quote.updated_at <= cutoff
                    )
                )
                q_result = await db.execute(stmt_quotes)
                quotes = q_result.scalars().all()
                
                for quote in quotes:
                    # Check if we already drafted or sent a follow-up
                    stmt_check = select(MessageLog).where(
                        MessageLog.business_id == business.id,
                        MessageLog.trigger_source == MessageTriggerSource.QUOTE_FOLLOWUP,
                        MessageLog.log_metadata["quote_id"].as_integer() == quote.id
                    )
                    log_check = await db.execute(stmt_check)
                    if log_check.scalar_one_or_none():
                        continue
                    
                    # 3. Use LLM to generate follow-up draft
                    logger.info(f"Generating follow-up draft for Quote {quote.id}")
                    prompt = f"Write a professional, friendly follow-up message for a quote of ${quote.total_amount:.2f} sent to {quote.customer.name} for service catalog items. The quote was sent a few days ago."
                    # For now, simplistic draft generation. In real app, provide more context.
                    draft_content = f"Hi {quote.customer.name}, just checking in on the quote we sent for ${quote.total_amount:.2f}. Do you have any questions or would you like to proceed?"
                    
                    # 4. Save as DRAFT in MessageLog
                    draft = MessageLog(
                        business_id=business.id,
                        recipient_phone=quote.customer.phone or "",
                        content=draft_content,
                        message_type=MessageType.WHATSAPP,
                        status=MessageStatus.DRAFT,
                        trigger_source=MessageTriggerSource.QUOTE_FOLLOWUP,
                        log_metadata={"quote_id": quote.id, "type": "quote_followup"}
                    )
                    db.add(draft)
            
            await db.commit()

    async def _process_review_requests(self):
        async with AsyncSessionLocal() as db:
            stmt = select(Business).where(
                Business.workflow_auto_review_requests == True,
                Business.workflow_review_link != None
            )
            result = await db.execute(stmt)
            businesses = result.scalars().all()
            
            for business in businesses:
                delay = business.workflow_review_request_delay_hrs or 2
                cutoff = datetime.now(timezone.utc) - timedelta(hours=delay)
                
                # Find paid jobs older than delay with no review request sent
                stmt_jobs = (
                    select(Job)
                    .join(Customer)
                    .where(
                        Job.business_id == business.id,
                        Job.paid == True,
                        Job.scheduled_at <= cutoff # Using scheduled_at as proxy for completion time if begun_at not reliable
                    )
                )
                j_result = await db.execute(stmt_jobs)
                jobs = j_result.scalars().all()
                
                for job in jobs:
                    stmt_check = select(MessageLog).where(
                        MessageLog.business_id == business.id,
                        MessageLog.trigger_source == MessageTriggerSource.REVIEW_REQUEST,
                        MessageLog.log_metadata["job_id"].as_integer() == job.id
                    )
                    log_check = await db.execute(stmt_check)
                    if log_check.scalar_one_or_none():
                        continue
                    
                    # 4. Auto-send review request (No draft needed for reviews per spec "Auto-sent")
                    logger.info(f"Sending automated review request for Job {job.id}")
                    content = f"Hi {job.customer.name}, thank you for your business! We'd love to hear your feedback. Please leave us a review here: {business.workflow_review_link}"
                    
                    await messaging_service.enqueue_message(
                        recipient_phone=job.customer.phone or "",
                        content=content,
                        channel=MessageType.WHATSAPP,
                        trigger_source=MessageTriggerSource.REVIEW_REQUEST,
                        business_id=business.id
                    )
                    
                    # Log that we sent it to avoid duplicates
                    sent_log = MessageLog(
                        business_id=business.id,
                        recipient_phone=job.customer.phone or "",
                        content=content,
                        message_type=MessageType.WHATSAPP,
                        status=MessageStatus.SENT,
                        trigger_source=MessageTriggerSource.REVIEW_REQUEST,
                        log_metadata={"job_id": job.id, "type": "review_request"},
                        sent_at=datetime.now(timezone.utc)
                    )
                    db.add(sent_log)
            
            await db.commit()

    async def start(self):
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self.check_and_trigger_automations())
            logger.info("AutomationService worker started")

    async def stop(self):
        self._running = False
        if self._worker_task:
            await self._worker_task
            logger.info("AutomationService worker stopped")

automation_service = AutomationService()
