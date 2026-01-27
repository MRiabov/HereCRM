import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Customer, JobStatus
from src.services.dashboard_service import DashboardService
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_get_unscheduled_jobs_logic(async_session: AsyncSession):
    business_id = 1
    dashboard = DashboardService(async_session)
    
    # Setup - Need a customer
    customer = Customer(name="Test Customer", business_id=business_id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)
    
    # 1. Unscheduled job (scheduled_at is None)
    job1 = Job(
        business_id=business_id,
        customer_id=customer.id,
        description="Unscheduled Job",
        status=JobStatus.pending,
        scheduled_at=None,
        employee_id=1
    )
    
    # 2. Unassigned job (employee_id is None)
    job2 = Job(
        business_id=business_id,
        customer_id=customer.id,
        description="Unassigned Job",
        status=JobStatus.pending,
        scheduled_at=datetime.now(timezone.utc),
        employee_id=None
    )
    
    # 3. Scheduled and Assigned job (should NOT be returned)
    job3 = Job(
        business_id=business_id,
        customer_id=customer.id,
        description="Properly Scheduled Job",
        status=JobStatus.pending,
        scheduled_at=datetime.now(timezone.utc),
        employee_id=1
    )
    
    # 4. Completed job (should NOT be returned even if unscheduled)
    job4 = Job(
        business_id=business_id,
        customer_id=customer.id,
        description="Completed Job",
        status=JobStatus.completed,
        scheduled_at=None,
        employee_id=None
    )

    async_session.add_all([job1, job2, job3, job4])
    await async_session.commit()
    
    unscheduled = await dashboard.get_unscheduled_jobs(business_id)
    
    assert len(unscheduled) == 2
    descriptions = [j.description for j in unscheduled]
    assert "Unscheduled Job" in descriptions
    assert "Unassigned Job" in descriptions
    assert "Properly Scheduled Job" not in descriptions
    assert "Completed Job" not in descriptions
    
    # Verify relationships are loaded
    for job in unscheduled:
        assert job.customer is not None
        assert job.customer.name == "Test Customer"
