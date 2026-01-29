import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import (
    Business,
    User,
)
from src.services.whatsapp_service import WhatsappService
from src.services.template_service import TemplateService
from src.uimodels import HelpTool

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
def template_service():
    return TemplateService()


@pytest.mark.asyncio
async def test_help_tool_integration(
    test_session: AsyncSession, template_service: TemplateService
):
    # Setup User
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()
    user = User(phone_number="123456789", business_id=biz.id, role="OWNER")
    test_session.add(user)
    await test_session.commit()

    # Mock Parser to return HelpTool
    mock_parser = AsyncMock()
    mock_parser.parse.return_value = HelpTool()

    # Mock HelpService
    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
        mock_help_instance = MockHelpService.return_value
        mock_help_instance.generate_help_response = AsyncMock(
            return_value="RAG Response"
        )

        service = WhatsappService(test_session, mock_parser, template_service)
        user_phone = "123456789"

        response = await service.handle_message("Help me", user_phone=user_phone)

        assert response == "RAG Response"
        MockHelpService.assert_called_once_with(test_session, mock_parser)
        mock_help_instance.generate_help_response.assert_called_once_with(
            user_query="Help me",
            business_id=biz.id,
            user_id=user.id,
            channel="WHATSAPP",
        )
