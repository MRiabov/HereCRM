
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Customer, User, UserRole
from src.services.dashboard_service import DashboardService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine

async def run_reproduction():
    engine = await setup_db()
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # Create Business
        biz = Business(name="Test Biz")
        session.add(biz)
        await session.flush()
        
        # Create Owner
        owner = User(name="Owner", business_id=biz.id, role=UserRole.OWNER, email="owner@test.com")
        session.add(owner)
        await session.flush()
        
        # Create Employee
        emp = User(name="Employee", business_id=biz.id, role=UserRole.EMPLOYEE, email="emp@test.com")
        session.add(emp)
        await session.flush()
        
        # Create Customer
        cust = Customer(name="Test Customer", business_id=biz.id)
        session.add(cust)
        await session.flush()
        
        # Create Job 1: Assigned to Employee, Today
        today = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        job1 = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Assigned Job",
            scheduled_at=today,
            employee_id=emp.id,
            status="pending"
        )
        session.add(job1)
        
        # Create Job 2: Unassigned, Today
        job2 = Job(
            business_id=biz.id,
            customer_id=cust.id,
            description="Unassigned Job",
            scheduled_at=today,
            employee_id=None,
            status="pending"
        )
        session.add(job2)
        
        await session.commit()
        
        # Test DashboardService.get_employee_schedules
        ds = DashboardService(session)
        schedules = await ds.get_employee_schedules(biz.id, today.date())
        
        print(f"Schedules found for {len(schedules)} employees")
        all_jobs_in_schedules = []
        for jobs in schedules.values():
            all_jobs_in_schedules.extend([j.description for j in jobs])
        
        print(f"Jobs in schedules: {all_jobs_in_schedules}")
        
        # Check if unassigned job is missing (Expected to be True currently)
        missing_unassigned = "Unassigned Job" not in all_jobs_in_schedules
        print(f"Unassigned Job missing from get_employee_schedules: {missing_unassigned}")
        
        # Test API list_jobs (mocking services and current_user)
        from src.services.crm_service import CRMService
        crm_service = CRMService(session, business_id=biz.id)
        
        # We need to mock get_services dependency or just call the function directly if we can
        # For simplicity, we just check what list_jobs returns using our services
        
        # In jobs.py, list_jobs does:
        # schedules = await dashboard_service.get_employee_schedules(crm_service.business_id, target_date)
        # ...
        # return [JobListResponse(date=target_date.isoformat(), jobs=[JobSchema.model_validate(j) for j in daily_jobs])]
        
        # Let's see what daily_jobs would contain based on current jobs.py logic
        daily_jobs = []
        seen_job_ids = set()
        for user, jobs in schedules.items():
            for job in jobs:
                if job.id not in seen_job_ids:
                    daily_jobs.append(job)
                    seen_job_ids.add(job.id)
        
        print(f"Daily jobs for API: {[j.description for j in daily_jobs]}")
        
        if "Unassigned Job" not in [j.description for j in daily_jobs]:
            print("FAILURE: Unassigned job is missing from dispatch view (daily_jobs)")
        else:
            print("SUCCESS: Unassigned job found (Wait, this shouldn't happen yet!)")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_reproduction())
