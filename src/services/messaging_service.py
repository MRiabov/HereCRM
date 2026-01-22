import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from src.models import MessageLog, MessageType, MessageStatus
from src.events import event_bus
from src.database import AsyncSessionLocal
from src.repositories import CustomerRepository

logger = logging.getLogger(__name__)


class MessagingService:
    """
    Service responsible for consuming events and sending messages via WhatsApp/SMS.
    Uses an async queue for buffering messages and processes them asynchronously.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def send_message(
        self,
        recipient_phone: str,
        content: str,
        channel: str = "whatsapp",
        trigger_source: str = "manual",
        business_id: Optional[int] = None,
    ) -> MessageLog:
        """
        Send a message to a recipient via the specified channel.
        
        Args:
            recipient_phone: Phone number of the recipient
            content: Message content to send
            channel: Channel to use ("whatsapp" or "sms")
            trigger_source: Source that triggered this message
            
        Returns:
            MessageLog: The created message log entry
        """
        # Determine message type
        message_type = MessageType.WHATSAPP if channel == "whatsapp" else MessageType.SMS
        
        # Create MessageLog entry with PENDING status
        async with AsyncSessionLocal() as db:
            message_log = MessageLog(
                business_id=business_id,
                recipient_phone=recipient_phone,
                content=content,
                message_type=message_type,
                status=MessageStatus.PENDING,
                trigger_source=trigger_source,
            )
            db.add(message_log)
            await db.commit()
            await db.refresh(message_log)
            
            try:
                # Mock sending message (in production, this would call external API)
                logger.info(
                    f"[MOCK] Sending {channel} message to {recipient_phone}: {content[:50]}..."
                )
                
                # Simulate API call delay
                await asyncio.sleep(0.1)
                
                # Update status to SENT
                async with AsyncSessionLocal() as db:
                    # Reload message_log in this session
                    from sqlalchemy import select
                    stmt = select(MessageLog).where(MessageLog.id == message_log.id)
                    result = await db.execute(stmt)
                    msg_log = result.scalar_one()
                    
                    msg_log.status = MessageStatus.SENT
                    msg_log.sent_at = datetime.now(timezone.utc)
                    msg_log.external_id = f"mock_{msg_log.id}_{int(datetime.now(timezone.utc).timestamp())}"
                    
                    await db.commit()
                
                # Track usage if business_id is known
                if business_id:
                    from src.services.billing_service import BillingService
                    billing_service = BillingService(db)
                    await billing_service.track_message_sent(business_id)
                
                logger.info(f"Message {message_log.id} sent successfully")
                
            except Exception as e:
                # Update status to FAILED on error
                logger.error(f"Failed to send message {message_log.id}: {e}")
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import select
                    stmt = select(MessageLog).where(MessageLog.id == message_log.id)
                    result = await db.execute(stmt)
                    msg_log = result.scalar_one()
                    msg_log.status = MessageStatus.FAILED
                    msg_log.error_message = str(e)
                    await db.commit()
            
            return message_log

    async def enqueue_message(
        self,
        recipient_phone: str,
        content: str,
        channel: str = "whatsapp",
        trigger_source: str = "event",
        business_id: Optional[int] = None,
    ):
        """
        Add a message to the queue for async processing.
        
        Args:
            recipient_phone: Phone number of the recipient
            content: Message content to send
            channel: Channel to use ("whatsapp" or "sms")
            trigger_source: Source that triggered this message
            business_id: ID of the business for billing
        """
        await self._queue.put({
            "recipient_phone": recipient_phone,
            "content": content,
            "channel": channel,
            "trigger_source": trigger_source,
            "business_id": business_id,
        })
        logger.debug(f"Enqueued message for {recipient_phone}")

    async def process_queue(self):
        """
        Background worker that processes messages from the queue.
        Runs indefinitely until stopped.
        """
        logger.info("MessagingService queue processor started")
        self._running = True
        
        while self._running:
            try:
                # Wait for message with timeout to allow checking _running flag
                message_data = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                
                # Process the message
                await self.send_message(**message_data)
                
                # Mark task as done
                self._queue.task_done()
                
            except asyncio.TimeoutError:
                # No message in queue, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing message from queue: {e}")
                # Continue processing other messages

        logger.info("MessagingService queue processor stopped")

    async def start(self):
        """Start the background queue processor."""
        if not self._running:
            self._worker_task = asyncio.create_task(self.process_queue())
            logger.info("MessagingService started")

    async def stop(self):
        """Stop the background queue processor."""
        self._running = False
        if self._worker_task:
            await self._worker_task
            logger.info("MessagingService stopped")

    # Event Handlers

    async def handle_job_created(self, data: dict):
        """
        Handle JOB_CREATED event.
        """
        job_id = data.get("job_id")
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")
        
        if job_id is None or customer_id is None or business_id is None:
            logger.error(f"Missing data in JOB_CREATED event: {data}")
            return
            
        logger.info(f"Handling JOB_CREATED for job {job_id}")
        
        async with AsyncSessionLocal() as db:
            customer_repo = CustomerRepository(db)
            customer = await customer_repo.get_by_id(customer_id, business_id)
            
            if not customer or not customer.phone:
                logger.warning(f"Could not find phone number for customer {customer_id}")
                return

            content = f"Your job has been booked! Job ID: {job_id}"
            
            await self.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source="job_booked",
                business_id=business_id,
            )

    async def handle_job_scheduled(self, data: dict):
        """
        Handle JOB_SCHEDULED event.
        """
        job_id = data.get("job_id")
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")
        scheduled_at_str = data.get("scheduled_at")
        
        if job_id is None or customer_id is None or business_id is None:
            logger.error(f"Missing data in JOB_SCHEDULED event: {data}")
            return
            
        logger.info(f"Handling JOB_SCHEDULED for job {job_id}")
        
        async with AsyncSessionLocal() as db:
            customer_repo = CustomerRepository(db)
            customer = await customer_repo.get_by_id(customer_id, business_id)
            
            if not customer or not customer.phone:
                logger.warning(f"Could not find phone number for customer {customer_id}")
                return

            content = f"Your job has been scheduled for {scheduled_at_str}"
            
            await self.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source="job_scheduled",
                business_id=business_id,
            )

    async def handle_on_my_way(self, data: dict):
        """
        Handle ON_MY_WAY event.
        """
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")
        eta_minutes = data.get("eta_minutes")
        
        if customer_id is None or business_id is None:
            logger.error(f"Missing data in ON_MY_WAY event: {data}")
            return
            
        logger.info(f"Handling ON_MY_WAY for customer {customer_id}")
        
        async with AsyncSessionLocal() as db:
            customer_repo = CustomerRepository(db)
            customer = await customer_repo.get_by_id(customer_id, business_id)
            
            if not customer or not customer.phone:
                logger.warning(f"Could not find phone number for customer {customer_id}")
                return

            eta_text = f" ETA: {eta_minutes} minutes" if eta_minutes else ""
            content = f"We're on our way!{eta_text}"
            
            await self.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source="on_my_way",
                business_id=business_id,
            )

    def register_handlers(self):
        """
        Register this service's event handlers with the EventBus.
        Should be called during application startup.
        """
        event_bus.subscribe("JOB_CREATED", self.handle_job_created)
        event_bus.subscribe("JOB_SCHEDULED", self.handle_job_scheduled)
        event_bus.subscribe("ON_MY_WAY", self.handle_on_my_way)
        logger.info("MessagingService handlers registered with EventBus")


# Global singleton instance
messaging_service = MessagingService()
