import pytest
from datetime import datetime, timezone
from src.services.time_tracking import TimeTrackingService
from src.models import User, Job, Business, UserRole, Customer

@pytest.mark.asyncio
async def test_time_tracking_flow(async_session):
    # Setup data
    business = Business(name="Time Biz", created_at=datetime.now(timezone.utc))
    async_session.add(business)
    await async_session.flush()

    user = User(
        name="Time Employee",
        phone_number="+15555555555",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(user)
    await async_session.flush()
    
    customer = Customer(name="Time Customer", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()

    job = Job(
        business_id=business.id,
        customer_id=customer.id,
        description="Time Job",
        scheduled_at=datetime.now(timezone.utc),
    )
    async_session.add(job)
    await async_session.flush()

    service = TimeTrackingService(async_session)

    # 1. Test Check In
    user = await service.check_in(user.id)
    assert user.current_shift_start is not None
    
    # 2. Test Check In Idempotency/Refresh (Optional in spec, but basic behavior check)
    original_start = user.current_shift_start
    # ... actually spec says "Check if already checked in? (Optional)"
    
    # 3. Test Check Out
    user, start, end = await service.check_out(user.id)
    assert user.current_shift_start is None
    assert start == original_start
    assert end > start

    # 4. Test Check Out without Check In
    with pytest.raises(ValueError, match="Not checked in"):
        await service.check_out(user.id)

    # 5. Test Start Job
    job = await service.start_job(job.id, user.id)
    assert job.begun_at is not None
    assert job.status == "in_progress"
    assert job.employee_id == user.id

    # 6. Test Finish Job
    original_job_start = job.begun_at
    job, total_duration = await service.finish_job(job.id)
    assert job.begun_at is None
    assert job.status == "completed"
    assert total_duration >= 0

    # 7. Test Finish Job without Start
    with pytest.raises(ValueError, match="Job not started"):
        await service.finish_job(job.id)

