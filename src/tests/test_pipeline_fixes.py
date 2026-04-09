import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Customer, PipelineStage, Job, JobStatus, Business
from src.services.crm_service import CRMService
from src.repositories import CustomerRepository, JobRepository
from src.services.pipeline_handlers import handle_job_created, handle_contact_event, handle_quote_sent
from src.events import event_bus

@pytest.fixture(autouse=True)
def setup_event_subscriptions():
    event_bus._subscribers = {}
    event_bus.subscribe("JOB_CREATED", handle_job_created)
    event_bus.subscribe("CONTACT_EVENT", handle_contact_event)
    event_bus.subscribe("QUOTE_SENT", handle_quote_sent)
    yield
    event_bus._subscribers = {}

@pytest.mark.asyncio
async def test_new_lead_to_contacted(session: AsyncSession):
    business_id = 1
    # Manually set to NEW_LEAD
    customer = Customer(name="New Lead", business_id=business_id, pipeline_stage=PipelineStage.NEW_LEAD)
    session.add(customer)
    await session.commit()

    # Emit CONTACT_EVENT
    await event_bus.emit(
        "CONTACT_EVENT", {"customer_id": customer.id, "business_id": business_id}
    )
    # Handlers are async but in this test setup we might need to await them if they were real background tasks
    # But here we are calling the handler directly effectively via the bus?
    # Wait, the event bus in this codebase seems to be a simple synchronous dispatcher or async one?
    # The handlers are async functions. The event_bus.emit likely awaits them or schedules them.
    # In 'src/events.py' usually it awaits if it's async.
    # Let's check src/events.py later if this fails. Assuming it works like in test_pipeline_logic.py.

    # We might need to manually invoke the handler if the bus is mocked or not working as expected in this isolated file?
    # But test_pipeline_logic.py uses event_bus.emit.

    # Force handler execution if emit is fire-and-forget (though test_pipeline_logic suggests otherwise)
    # Actually, let's call the handler directly to be sure for reproduction,
    # OR rely on the existing pattern. I'll rely on the pattern.

    # Wait for any background tasks? The test_pipeline_logic just awaits emit.

    await session.commit()
    await session.refresh(customer)

    # BUG: Expected CONTACTED, but if logic is strict == NOT_CONTACTED, it will stay NEW_LEAD
    assert customer.pipeline_stage == PipelineStage.CONTACTED, f"Customer stage is {customer.pipeline_stage}, expected CONTACTED"

@pytest.mark.asyncio
async def test_cancelled_job_progression(session: AsyncSession):
    business_id = 1
    crm = CRMService(session, business_id)
    customer = Customer(name="Cancelled Job Customer", business_id=business_id)
    session.add(customer)
    await session.commit()

    # Create a job and immediately cancel it (or create as cancelled)
    # create_job default status is PENDING
    job = await crm.create_job(customer_id=customer.id, description="Job 1", status=JobStatus.CANCELLED)
    await session.commit()

    await session.refresh(customer)
    # If cancelled jobs count, this will be CONVERTED_ONCE
    # If we consider this a bug, we assert it should NOT be CONVERTED_ONCE (or maybe stay NOT_CONTACTED or CONTACTED?)
    # But wait, if I create a job, I probably contacted them.

    # Let's say we want to avoid "Converted" for cancelled jobs.
    # But for now I just want to see what happens.
    # The current logic counts ALL jobs.
    print(f"Stage after 1 cancelled job: {customer.pipeline_stage}")

    # Create another cancelled job
    job2 = await crm.create_job(customer_id=customer.id, description="Job 2", status=JobStatus.CANCELLED)
    await session.commit()

    await session.refresh(customer)
    print(f"Stage after 2 cancelled jobs: {customer.pipeline_stage}")

    # Since we excluded CANCELLED jobs from the count, the stage should NOT update to CONVERTED
    # It should remain as it was (likely NOT_CONTACTED if these are the only jobs)
    # However, create_job might trigger other side effects?
    # But specifically the pipeline handler relies on count.

    # If 0 jobs (all cancelled), stage should be NOT_CONTACTED (initial state)
    assert customer.pipeline_stage == PipelineStage.NOT_CONTACTED

@pytest.mark.asyncio
async def test_quoted_disabled_transition(session: AsyncSession):
    business_id = 1
    # Disable QUOTED stage workflow
    business = await session.get(Business, business_id)
    if not business:
        business = Business(id=business_id, name="Test Biz", workflow_pipeline_quoted_stage=False)
        session.add(business)
    else:
        business.workflow_pipeline_quoted_stage = False
    await session.commit()

    customer = Customer(name="Quote Customer", business_id=business_id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    session.add(customer)
    await session.commit()

    # Emit QUOTE_SENT
    await event_bus.emit(
        "QUOTE_SENT", {"customer_id": customer.id, "business_id": business_id}
    )

    # We need to wait for the handler to run.
    # In test_pipeline_logic they just await emit.

    await session.commit() # commit transaction
    await session.refresh(customer)

    # Should be CONTACTED because QUOTED is disabled
    assert customer.pipeline_stage == PipelineStage.CONTACTED
    assert customer.pipeline_stage != PipelineStage.QUOTED
