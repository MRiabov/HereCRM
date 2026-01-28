import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, UserRole, Job, Customer, JobStatus
from src.services.scheduler import scheduler_service
from src.services.messaging_service import messaging_service

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.mark.asyncio
async def test_check_shifts_sends_notification():
    # Setup In-Memory DB
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Seed Data
    async with SessionLocal() as session:
        biz = Business(name="Test Biz")
        session.add(biz)
        await session.flush()
        
        # 1. Employee
        emp = User(
            name="Alice",
            phone_number="12345",
            business_id=biz.id,
            role=UserRole.EMPLOYEE
        )
        session.add(emp)
        
        # 2. Customer
        cust = Customer(name="Bob", business_id=biz.id)
        session.add(cust)
        await session.flush()
        
        # 3. Job Scheduled Today
        now = datetime.now(timezone.utc)
        
        job_today = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Morning Job",
            scheduled_at=now,
            employee_id=emp.id,
            status=JobStatus.SCHEDULED,
            location="123 Main St"
        )
        session.add(job_today)
        
        # 4. Job Tomorrow (Should NOT be picked up)
        job_tomorrow = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Tomorrow Job",
            scheduled_at=now + timedelta(days=1, hours=1),
            employee_id=emp.id,
            status="SCHEDULED"
        )
        session.add(job_tomorrow)
        
        await session.commit()

    # Match the patching logic from the WP04 version but clean it up
    with patch("src.services.scheduler.AsyncSessionLocal", side_effect=SessionLocal):
        with patch.object(messaging_service, "enqueue_message", new_callable=AsyncMock) as mock_send:
            
            # Execute
            await scheduler_service.check_shifts()
            
            # Verify
            assert mock_send.called
            assert mock_send.call_count == 1 # Only Alice, only today's job
            
            args, kwargs = mock_send.call_args
            assert kwargs['recipient_phone'] == "12345"
            content = kwargs['content']
            
            print(f"DEBUG CONTENT: {content}")
            
            assert "Morning Overview for Alice" in content
            assert "Morning Job" in content
            assert "Tomorrow Job" not in content
            assert "123 Main St" in content
            assert "Reply 'Start shift'" in content
