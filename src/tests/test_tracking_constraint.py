import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.time_tracking import TimeTrackingService
from src.models import Business, Customer, Job, JobStatus, User


@pytest.mark.asyncio
async def test_start_job_constraint(session: AsyncSession):
    # Setup business, user, customer
    business = Business(name="Test Biz")
    session.add(business)
    await session.flush()

    user = User(name="Test Tech", business_id=business.id)
    session.add(user)
    await session.flush()

    customer = Customer(name="Test Cust", business_id=business.id)
    session.add(customer)
    await session.flush()

    tt_service = TimeTrackingService(session)

    # Create two jobs
    job1 = Job(
        customer_id=customer.id,
        business_id=business.id,
        description="Job 1",
        employee_id=user.id,
    )
    job2 = Job(
        customer_id=customer.id,
        business_id=business.id,
        description="Job 2",
        employee_id=user.id,
    )
    session.add_all([job1, job2])
    await session.flush()

    # Start first job
    await tt_service.start_job(job1.id, user.id)
    await session.refresh(job1)
    assert job1.status == JobStatus.IN_PROGRESS

    # Try to start second job - should fail
    with pytest.raises(ValueError) as excinfo:
        await tt_service.start_job(job2.id, user.id)
    assert "already have an active job in progress" in str(excinfo.value)

    # Pause first job
    await tt_service.pause_job(job1.id)
    await session.refresh(job1)
    assert job1.status == JobStatus.PAUSED

    # Now starting second job should succeed
    await tt_service.start_job(job2.id, user.id)
    await session.refresh(job2)
    assert job2.status == JobStatus.IN_PROGRESS
