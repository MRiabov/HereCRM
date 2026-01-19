import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, ConversationState, ConversationStatus
from src.services.whatsapp_service import WhatsappService
from src.services.template_service import TemplateService
from src.llm_client import LLMParser
from unittest.mock import MagicMock
from src.uimodels import AddServiceTool, ListServicesTool, DeleteServiceTool, ExitSettingsTool
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

@pytest.fixture
def mock_parser():
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = None  # Default to no tool call
    return parser

@pytest.fixture
def mock_template_service():
    return TemplateService()

@pytest.mark.asyncio
async def test_settings_flow(test_session, mock_parser, mock_template_service):
    # Setup
    biz = Business(name="TestBiz")
    test_session.add(biz)
    await test_session.flush()
    
    user = User(phone_number="123", business_id=biz.id)
    test_session.add(user)
    await test_session.commit()
    
    service = WhatsappService(test_session, mock_parser, mock_template_service)
    
    # 1. Enter Settings
    response = await service.handle_message("123", "settings")
    assert "Settings Mode" in response
    
    state = await service.state_repo.get_by_user_id(user.id)
    assert state.state == ConversationStatus.SETTINGS
    
    # 2. Add Service
    mock_parser.parse_settings.return_value = AddServiceTool(name="Window Clean", price=50.0)
    response = await service.handle_message("123", "Add Service Window Clean 50")
    assert "Window Clean" in response
    assert "added" in response
    assert "50.00" in response
    
    # Verify DB
    from src.repositories import ServiceRepository
    repo = ServiceRepository(test_session)
    services = await repo.get_all_for_business(biz.id)
    assert len(services) == 1
    assert services[0].name == "Window Clean"
    assert services[0].default_price == 50.0
    
    # 3. List Services
    mock_parser.parse_settings.return_value = ListServicesTool()
    response = await service.handle_message("123", "List")
    assert "Window Clean" in response
    assert "50.00" in response
    
    # 4. Delete Service
    mock_parser.parse_settings.return_value = DeleteServiceTool(name="Window Clean")
    response = await service.handle_message("123", "Delete Service")
    assert "deleted" in response
    
    services = await repo.get_all_for_business(biz.id)
    assert len(services) == 0
    
    # 5. Exit
    mock_parser.parse_settings.return_value = ExitSettingsTool()
    response = await service.handle_message("123", "Exit")
    assert "Welcome back" in response
    
    state = await service.state_repo.get_by_user_id(user.id)
    assert state.state == ConversationStatus.IDLE
