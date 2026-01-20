import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Customer, User
from src.tool_executor import ToolExecutor
from src.uimodels import SendStatusTool
from src.services.template_service import TemplateService
from datetime import datetime, timedelta

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

@pytest.fixture
def template_service():
    return TemplateService()

@pytest.mark.asyncio
async def test_send_status_named_customer(test_session, template_service):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role="owner")
    test_session.add(user)
    
    customer = Customer(name="John Doe", phone="123456", business_id=biz.id)
    test_session.add(customer)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, user.id, user.phone_number, template_service)
    
    with patch("src.tool_executor.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock()
        
        tool = SendStatusTool(query="John", status_type="on_way")
        result, metadata = await executor.execute(tool)
        
        assert "Sent status update to John Doe" in result
        assert metadata["status_type"] == "on_way"
        
        mock_bus.emit.assert_called_once()
        args = mock_bus.emit.call_args
        assert args[0][0] == "SEND_STATUS_MESSAGE"
        payload = args[0][1]
        assert payload["customer_id"] == customer.id
        assert payload["status_type"] == "on_way"

@pytest.mark.asyncio
async def test_send_status_next_client(test_session, template_service):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role="owner")
    test_session.add(user)
    
    customer = Customer(name="Next Client", phone="999999", business_id=biz.id)
    test_session.add(customer)
    await test_session.flush()
    
    # Create a scheduled job in the future
    future_time = datetime.now() + timedelta(hours=1)
    job = Job(
        business_id=biz.id,
        customer_id=customer.id,
        status="scheduled",
        scheduled_at=future_time
    )
    
    test_session.add(job)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, user.id, user.phone_number, template_service)
    
    with patch("src.tool_executor.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock()
        
        tool = SendStatusTool(query="next_scheduled_client", status_type="running_late")
        result, metadata = await executor.execute(tool)
        
        assert "Sent status update to Next Client" in result
        assert metadata["status_type"] == "running_late"
        
        mock_bus.emit.assert_called_once()
        args = mock_bus.emit.call_args
        payload = args[0][1]
        assert payload["customer_id"] == customer.id
