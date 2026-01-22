import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from src.services.scheduler import scheduler_service
from src.models import User, Job, Business, UserRole, Customer

@pytest.mark.asyncio
async def test_scheduler_check_shifts(async_session):
    # Setup data
    business = Business(name="Test Biz", created_at=datetime.now(timezone.utc))
    async_session.add(business)
    await async_session.flush()

    user = User(
        name="Test Employee",
        phone_number="+15551234567",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(user)
    await async_session.flush()
    
    customer = Customer(name="Test Customer", business_id=business.id, created_at=datetime.now(timezone.utc))
    async_session.add(customer)
    await async_session.flush()

    now = datetime.now(timezone.utc)
    # Job today (should be included)
    job_today = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=user.id,
        description="Job Today",
        scheduled_at=now,
        created_at=now
    )
    async_session.add(job_today)
    
    # Job tomorrow (should be excluded)
    job_tomorrow = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=user.id,
        description="Job Tomorrow",
        scheduled_at=now + timedelta(days=2),
        created_at=now
    )
    async_session.add(job_tomorrow)
    
    await async_session.commit()

    # Mock context manager for AsyncSessionLocal
    class MockSessionContext:
        def __init__(self, session):
            self.session = session
        async def __aenter__(self):
            return self.session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch messaging_service
    with patch("src.services.scheduler.messaging_service", new_callable=AsyncMock) as mock_msg_service:
        # Patch AsyncSessionLocal to use our test session
        with patch("src.services.scheduler.AsyncSessionLocal", side_effect=lambda: MockSessionContext(async_session)):
            
            await scheduler_service.check_shifts()
            
            # Assertions
            assert mock_msg_service.enqueue_message.called, "enqueue_message should be called"
            call_args = mock_msg_service.enqueue_message.call_args
            assert call_args, "Call args should exist"
            kwargs = call_args.kwargs
            
            assert kwargs['recipient_phone'] == "+15551234567"
            assert "Job Today" in kwargs['content']
            assert "Job Tomorrow" not in kwargs['content']
            assert kwargs['trigger_source'] == "scheduler_shift_start"
