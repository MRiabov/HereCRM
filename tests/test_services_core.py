import pytest
from datetime import date, datetime, time
from src.models import Business, User, Job, Customer, UserRole
from src.services.dashboard_service import DashboardService
from src.services.assignment_service import AssignmentService
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.database import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_assignment_service(test_session: AsyncSession):
    # Setup
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(business_id=biz.id, phone_number="12345", role=UserRole.MEMBER)
    test_session.add(user)
    
    customer = Customer(business_id=biz.id, name="Test Customer")
    test_session.add(customer)
    await test_session.flush()

    job = Job(business_id=biz.id, customer_id=customer.id, description="Test Job", status="pending")
    test_session.add(job)
    await test_session.commit()

    # Test assign_job
    assignment_service = AssignmentService(test_session, biz.id)
    updated_job = await assignment_service.assign_job(job.id, user.id)
    
    assert updated_job.employee_id == user.id
    
    # Verify persistence
    await test_session.refresh(job)
    assert job.employee_id == user.id

    # Test unassign_job
    await assignment_service.unassign_job(job.id)
    await test_session.refresh(job)
    assert job.employee_id is None

@pytest.mark.asyncio
async def test_dashboard_service_schedules(test_session: AsyncSession):
    # Setup
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user1 = User(business_id=biz.id, phone_number="111", role=UserRole.OWNER)
    user2 = User(business_id=biz.id, phone_number="222", role=UserRole.MEMBER)
    test_session.add_all([user1, user2])
    
    customer = Customer(business_id=biz.id, name="Test Customer")
    test_session.add(customer)
    await test_session.flush()

    today = date.today()
    job1 = Job(
        business_id=biz.id, 
        customer_id=customer.id, 
        description="Job 1", 
        scheduled_at=datetime.combine(today, time(10, 0)),
        employee_id=user1.id
    )
    job2 = Job(
        business_id=biz.id, 
        customer_id=customer.id, 
        description="Job 2", 
        scheduled_at=datetime.combine(today, time(14, 0)),
        employee_id=user2.id
    )
    test_session.add_all([job1, job2])
    await test_session.commit()

    dashboard_service = DashboardService(test_session, biz.id)
    schedules = await dashboard_service.get_employee_schedules(biz.id, today)
    
    assert len(schedules) == 2
    # Check if user1 and user2 are in keys
    user_ids = [u.id for u in schedules.keys()]
    assert user1.id in user_ids
    assert user2.id in user_ids
    
    # Check jobs
    for user, jobs in schedules.items():
        if user.id == user1.id:
            assert len(jobs) == 1
            assert jobs[0].description == "Job 1"
        if user.id == user2.id:
            assert len(jobs) == 1
            assert jobs[0].description == "Job 2"

@pytest.mark.asyncio
async def test_dashboard_service_unscheduled(test_session: AsyncSession):
    # Setup
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    customer = Customer(business_id=biz.id, name="Test Customer")
    test_session.add(customer)
    await test_session.flush()

    job1 = Job(business_id=biz.id, customer_id=customer.id, description="Unscheduled Job", employee_id=None, status="pending")
    job2 = Job(business_id=biz.id, customer_id=customer.id, description="Scheduled Job", employee_id=999, status="pending")
    test_session.add_all([job1, job2])
    await test_session.commit()

    dashboard_service = DashboardService(test_session, biz.id)
    unscheduled = await dashboard_service.get_unscheduled_jobs(biz.id)
    
    assert len(unscheduled) == 1
    assert unscheduled[0].description == "Unscheduled Job"
