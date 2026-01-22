import logging
from src.repositories import CustomerRepository, JobRepository
from src.models import PipelineStage
import src.database
from src.events import event_bus, JOB_CREATED, CONTACT_EVENT

logger = logging.getLogger(__name__)

@event_bus.on(JOB_CREATED)
async def handle_job_created(data: dict) -> None:
    """
    Handle JOB_CREATED event.
    Updates customer stage to CONVERTED_ONCE or CONVERTED_RECURRENT.
    """
    customer_id = data.get("customer_id")
    business_id = data.get("business_id")
    
    if not customer_id or not business_id:
        logger.error("Missing customer_id or business_id in JOB_CREATED event")
        return

    async with src.database.AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        customer_repo = CustomerRepository(session)
        
        # Check current job count
        count = await job_repo.get_count_by_customer(customer_id, business_id)
        
        customer = await customer_repo.get_by_id(customer_id, business_id)
        if not customer:
            logger.error(f"Customer {customer_id} not found for pipeline update")
            return

        new_stage = None
        if count == 1:
            new_stage = PipelineStage.CONVERTED_ONCE
        elif count > 1:
            new_stage = PipelineStage.CONVERTED_RECURRENT

        if new_stage and customer.pipeline_stage != new_stage:
            old_stage = customer.pipeline_stage
            customer.pipeline_stage = new_stage
            await session.commit()
            logger.info(f"Updated customer {customer_id} stage: {old_stage} -> {new_stage} (Jobs: {count})")

@event_bus.on(CONTACT_EVENT)
async def handle_contact_event(data: dict) -> None:
    """
    Handle CONTACT_EVENT.
    Updates customer stage to CONTACTED if currently NOT_CONTACTED.
    """
    customer_id = data.get("customer_id")
    business_id = data.get("business_id")
    
    if not customer_id or not business_id:
        return

    async with src.database.AsyncSessionLocal() as session:
        customer_repo = CustomerRepository(session)
        customer = await customer_repo.get_by_id(customer_id, business_id)
        
        if customer and customer.pipeline_stage == PipelineStage.NOT_CONTACTED:
            customer.pipeline_stage = PipelineStage.CONTACTED
            await session.commit()
            logger.info(f"Updated customer {customer_id} to CONTACTED")
