import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Customer, PipelineStage, RequestStatus
from src.services.crm_service import CRMService
from src.repositories import CustomerRepository
from src.services.pipeline_handlers import handle_job_created, handle_contact_event

# Since we use EventBus which is global, we need to mock or ensure it works in tests.
from src.events import event_bus


# Integration test using the real EventBus subscriptions
@pytest.fixture(autouse=True)
def setup_event_subscriptions():
    # Ensure handlers are subscribed (usually done in main.py)
    # Clear existing to avoid double-processing if test runners reuse process
    event_bus._subscribers = {}
    event_bus.subscribe("JOB_CREATED", handle_job_created)
    event_bus.subscribe("CONTACT_EVENT", handle_contact_event)
    yield
    event_bus._subscribers = {}


@pytest.mark.asyncio
async def test_customer_creation_default_stage(session: AsyncSession):
    business_id = 1
    customer = Customer(name="Test Lead", business_id=business_id)
    repo = CustomerRepository(session)
    repo.add(customer)
    await session.flush()

    assert customer.pipeline_stage == PipelineStage.NOT_CONTACTED


@pytest.mark.asyncio
async def test_job_creation_progression(session: AsyncSession):
    # Setup
    business_id = 1
    crm = CRMService(session, business_id)
    customer = Customer(name="Test Progression", business_id=business_id)
    session.add(customer)
    await session.commit()

    assert customer.pipeline_stage == PipelineStage.NOT_CONTACTED

    # Act 1: Create First Job
    # create_job now emits JOB_CREATED which should trigger progression automatically
    await crm.create_job(customer_id=customer.id, description="Job 1")
    await session.commit()

    # Refresh customer
    await session.refresh(customer)
    assert customer.pipeline_stage == PipelineStage.CONVERTED_ONCE

    # Act 2: Create Second Job
    await crm.create_job(customer_id=customer.id, description="Job 2")
    await session.commit()

    await session.refresh(customer)
    assert customer.pipeline_stage == PipelineStage.CONVERTED_RECURRENT


@pytest.mark.asyncio
async def test_convert_request_progression(session: AsyncSession):
    business_id = 1
    crm = CRMService(session, business_id)
    name = "Target Customer"
    customer = Customer(name=name, business_id=business_id)
    from src.models import Request

    req = Request(
        business_id=business_id,
        description=f"Request from {name}",
        status=RequestStatus.PENDING,
    )
    session.add(customer)
    session.add(req)
    await session.commit()

    # Act: Convert Request to Job (using the name as query to match customer)
    # This should now emit JOB_CREATED because convert_request calls create_job
    await crm.convert_request(query=name, action="SCHEDULE")
    await session.commit()

    await session.refresh(customer)
    assert customer.pipeline_stage == PipelineStage.CONVERTED_ONCE


@pytest.mark.asyncio
async def test_contact_event_progression(session: AsyncSession):
    business_id = 1
    customer = Customer(name="Test Contact", business_id=business_id)
    session.add(customer)
    await session.commit()

    assert customer.pipeline_stage == PipelineStage.NOT_CONTACTED

    # Act: Emit CONTACT_EVENT
    await event_bus.emit(
        "CONTACT_EVENT", {"customer_id": customer.id, "business_id": business_id}
    )
    await session.commit()

    await session.refresh(customer)
    assert customer.pipeline_stage == PipelineStage.CONTACTED


@pytest.mark.asyncio
async def test_pipeline_summary(session: AsyncSession):
    business_id = 1
    crm = CRMService(session, business_id)

    # Setup some customers in different stages
    c1 = Customer(
        name="C1", business_id=business_id, pipeline_stage=PipelineStage.NOT_CONTACTED
    )
    c2 = Customer(
        name="C2", business_id=business_id, pipeline_stage=PipelineStage.CONTACTED
    )
    c3 = Customer(
        name="C3", business_id=business_id, pipeline_stage=PipelineStage.CONVERTED_ONCE
    )
    c4 = Customer(
        name="C4", business_id=business_id, pipeline_stage=PipelineStage.CONVERTED_ONCE
    )

    session.add_all([c1, c2, c3, c4])
    await session.commit()

    # Act
    summary = await crm.get_pipeline_summary()

    # Assert
    assert summary[PipelineStage.NOT_CONTACTED.value]["count"] == 1
    assert summary[PipelineStage.CONTACTED.value]["count"] == 1
    assert summary[PipelineStage.CONVERTED_ONCE.value]["count"] == 2
    assert "C1" in summary[PipelineStage.NOT_CONTACTED.value]["examples"]

    # Test formatting
    report = await crm.format_pipeline_summary()
    assert "### Pipeline Breakdown" in report
    assert "**Not Contacted**: 1 customer" in report
    assert "**Converted Once**: 2 customers" in report
    # The order of names might vary, so check presence individually
    assert "C3" in report
    assert "C4" in report
