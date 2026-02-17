import pytest
from sqlalchemy import text
from src.database import AsyncSessionLocal, Base, engine
from src.repositories import CustomerRepository, JobRepository
from src.models import Customer, Job, JobStatus, PipelineStage
from src.services.pipeline_handlers import handle_job_created, handle_contact_event
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
async def setup_database():
    """Create database tables before each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_cancelled_job_counting_fix():
    """
    Regression test: Ensure cancelled jobs do NOT contribute to pipeline progression count.
    If a customer has 1 cancelled job and 1 valid job, they should be CONVERTED_ONCE (count=1).
    """
    async with AsyncSessionLocal() as session:
        customer_repo = CustomerRepository(session)
        job_repo = JobRepository(session)

        # 1. Create a customer
        customer = Customer(name="Test Customer", pipeline_stage=PipelineStage.NOT_CONTACTED, business_id=1)
        customer_repo.add(customer)
        await session.commit()
        await session.refresh(customer)
        customer_id = customer.id

        # 2. Create a CANCELLED job
        job1 = Job(
            customer_id=customer_id,
            description="Cancelled Job",
            status=JobStatus.CANCELLED,
            business_id=1
        )
        job_repo.add(job1)
        await session.commit()

        # Trigger pipeline update for job 1
        await handle_job_created({
            "job_id": job1.id,
            "customer_id": customer_id,
            "business_id": 1
        })

        # 3. Create a VALID job
        job2 = Job(
            customer_id=customer_id,
            description="Valid Job",
            status=JobStatus.PENDING,
            business_id=1
        )
        job_repo.add(job2)
        await session.commit()

        # Trigger pipeline update for job 2
        await handle_job_created({
            "job_id": job2.id,
            "customer_id": customer_id,
            "business_id": 1
        })

        # 4. Verify Final Stage
        result = await session.execute(
            text("SELECT pipeline_stage FROM customers WHERE id = :id"),
            {"id": customer_id}
        )
        stage = result.scalar()

        # Correct behavior: CONVERTED_ONCE because only 1 valid job exists
        assert stage == PipelineStage.CONVERTED_ONCE, \
            f"Regression: Customer stage is {stage}, expected CONVERTED_ONCE"

@pytest.mark.asyncio
async def test_contact_event_transitions_fix():
    """
    Regression test: Ensure contact events trigger pipeline transitions from both NOT_CONTACTED and NEW_LEAD.
    """
    async with AsyncSessionLocal() as session:
        customer_repo = CustomerRepository(session)

        # 1. Test NOT_CONTACTED -> CONTACTED
        customer1 = Customer(name="Test Customer 1", pipeline_stage=PipelineStage.NOT_CONTACTED, business_id=1)
        customer_repo.add(customer1)
        await session.commit()
        customer1_id = customer1.id

        await handle_contact_event({
            "customer_id": customer1_id,
            "business_id": 1
        })

        await session.refresh(customer1)
        assert customer1.pipeline_stage == PipelineStage.CONTACTED, \
            f"Expected CONTACTED, got {customer1.pipeline_stage}"

        # 2. Test NEW_LEAD -> CONTACTED
        customer2 = Customer(name="Test Customer 2", pipeline_stage=PipelineStage.NEW_LEAD, business_id=1)
        customer_repo.add(customer2)
        await session.commit()
        customer2_id = customer2.id

        await handle_contact_event({
            "customer_id": customer2_id,
            "business_id": 1
        })

        await session.refresh(customer2)
        assert customer2.pipeline_stage == PipelineStage.CONTACTED, \
            f"Expected CONTACTED from NEW_LEAD, got {customer2.pipeline_stage}"
