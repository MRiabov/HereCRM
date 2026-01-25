import logging
from datetime import timedelta
from src.events import event_bus, QUOTE_SENT, JOB_PAID
from src.services.scheduler import scheduler_service

logger = logging.getLogger(__name__)

async def check_quote_followup(quote_id: int, customer_id: int, business_id: int):
    """
    Task to check if a quote needs follow-up and generate a draft.
    """
    logger.info(f"Checking quote follow-up for quote {quote_id} (Customer {customer_id}, Business {business_id})")
    # TODO: Implement logic to check quote status and generate LLM draft
    # 1. Get quote
    # 2. If status == SENT:
    # 3. Generate draft
    # 4. Notify business user

async def send_review_request(job_id: int, customer_id: int, business_id: int):
    """
    Task to send a review request after a job is paid.
    """
    logger.info(f"Sending review request for job {job_id} (Customer {customer_id}, Business {business_id})")
    # TODO: Implement logic to send review request
    # 1. Check if review already requested?
    # 2. Send message via MessagingService

class AutomationEventHandler:
    @event_bus.on(QUOTE_SENT)
    @staticmethod
    async def handle_quote_sent(data: dict) -> None:
        quote_id = data.get("quote_id")
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")

        if not quote_id:
            return

        # Schedule follow-up in 48 hours
        # Using 48h as per spec (default)
        scheduler_service.add_delayed_job(
            check_quote_followup,
            timedelta(hours=48),
            quote_id=quote_id,
            customer_id=customer_id,
            business_id=business_id
        )
        logger.info(f"Scheduled quote follow-up for {quote_id}")

    @event_bus.on(JOB_PAID)
    @staticmethod
    async def handle_job_paid(data: dict) -> None:
        job_id = data.get("job_id")
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")

        if not job_id:
            return

        # Schedule review request in 2 hours
        # Using 2h as per spec
        scheduler_service.add_delayed_job(
            send_review_request,
            timedelta(hours=2),
            job_id=job_id,
            customer_id=customer_id,
            business_id=business_id
        )
        logger.info(f"Scheduled review request for {job_id}")
