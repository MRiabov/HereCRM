import pytest
from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Customer, JobStatus
from src.services.crm_service import CRMService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.mark.asyncio
async def test_schedule_timezone_filtering():
    """
    Test that jobs are correctly filtered by local date when a timezone is provided.
    """
    # 1. Setup In-Memory DB
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # 2. Seed Data
        biz = Business(name="TZ Biz")
        session.add(biz)
        await session.flush()
        
        cust = Customer(name="Local Cust", business_id=biz.id)
        session.add(cust)
        await session.flush()
        
        # Target: Jan 27, 2026. TZ: EST (UTC-5)
        target_date = date(2026, 1, 27)
        tz_str = "America/New_York"
        
        # Job A: Jan 27 09:00 EST = Jan 27 14:00 UTC (Within range)
        job_a = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Morning Job",
            scheduled_at=datetime(2026, 1, 27, 14, 0, tzinfo=timezone.utc),
            status=JobStatus.PENDING
        )
        
        # Job B: Jan 27 20:00 EST = Jan 28 01:00 UTC (Stored as next day in UTC, but should be in range)
        job_b = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Evening Job",
            scheduled_at=datetime(2026, 1, 28, 1, 0, tzinfo=timezone.utc),
            status=JobStatus.PENDING
        )
        
        # Job C: Jan 26 20:00 EST = Jan 27 01:00 UTC (Stored as target day in UTC, but is actually yesterday in local time)
        job_c = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Yesterday Late Job",
            scheduled_at=datetime(2026, 1, 27, 1, 0, tzinfo=timezone.utc),
            status=JobStatus.PENDING
        )
        
        session.add_all([job_a, job_b, job_c])
        await session.commit()
        
        # 3. Test CRMService
        service = CRMService(session, biz.id)
        
        # Query for Jan 27 in EST
        schedule = await service.get_employee_schedules(target_date, timezone_str=tz_str)
        
        all_jobs = []
        for emp_jobs in schedule.values():
            all_jobs.extend(emp_jobs)
            
        found_descriptions = [j.description for j in all_jobs]
        
        # Assertions
        assert "Morning Job" in found_descriptions
        assert "Evening Job" in found_descriptions
        assert "Yesterday Late Job" not in found_descriptions
        assert len(all_jobs) == 2
