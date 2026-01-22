import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool, ScheduleJobTool
from src.models import Customer, Job, Business, User, UserRole
from src.services.template_service import TemplateService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
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
async def test_add_job_emits_event(test_session):
    # Setup
    business = Business(name="Test Biz")
    test_session.add(business)
    await test_session.flush()
    
    user_id = 999
    user = User(id=user_id, business_id=business.id, role=UserRole.OWNER, phone_number="+1234567890")
    test_session.add(user)
    await test_session.flush()
    
    user_phone = "+1234567890"
    template_service = AsyncMock(spec=TemplateService)
    template_service.render.return_value = "Mocked Template"
    
    executor = ToolExecutor(test_session, business.id, user_id, user_phone, template_service)
    
    # Mock event bus
    with patch("src.events.event_bus.emit", new_callable=AsyncMock) as mock_emit:
        # Execute
        tool = AddJobTool(
            customer_name="Test Customer",
            customer_phone="+1987654321",
            description="Test Job",
            location="Test Location",
            price=100.0,
            status="pending"
        )
        
        await executor.execute(tool)
        
        # Verify JOB_CREATED was emitted (from CRMService)
        found = False
        for call in mock_emit.call_args_list:
            if call[0][0] == "JOB_CREATED":
                found = True
                data = call[0][1]
                assert data["business_id"] == business.id
                break
        assert found, "JOB_CREATED event not emitted"

@pytest.mark.asyncio
async def test_schedule_job_emits_event(test_session):
    # Setup
    business = Business(name="Test Biz")
    test_session.add(business)
    await test_session.flush()

    user_id = 999
    user = User(id=user_id, business_id=business.id, role=UserRole.OWNER, phone_number="+1234567890")
    test_session.add(user)
    await test_session.flush()
    
    user_phone = "+1234567890"
    template_service = AsyncMock(spec=TemplateService)
    template_service.render.return_value = "Mocked Template"
    
    executor = ToolExecutor(test_session, business.id, user_id, user_phone, template_service)
    
    # Create existing job and customer
    customer = Customer(
        business_id=business.id,
        name="Test Customer",
        phone="+1987654321"
    )
    test_session.add(customer)
    await test_session.flush()
    
    job = Job(
        business_id=business.id,
        customer_id=customer.id,
        description="Test Job",
        status="pending"
    )
    test_session.add(job)
    await test_session.commit()
    
    # Mock event bus
    with patch("src.events.event_bus.emit", new_callable=AsyncMock) as mock_emit:
        # Execute
        tool = ScheduleJobTool(
            job_id=job.id,
            time="Tomorrow at 2pm",
            iso_time="2026-01-16T14:00:00Z"
        )
        
        await executor.execute(tool)
        
        # Verify JOB_SCHEDULED was emitted
        found = False
        for call in mock_emit.call_args_list:
            if call[0][0] == "JOB_SCHEDULED":
                found = True
                data = call[0][1]
                assert data["job_id"] == job.id
                assert data["business_id"] == business.id
                assert "2026-01-16T14:00:00" in data["scheduled_at"]
                break
        assert found, "JOB_SCHEDULED event not emitted"
