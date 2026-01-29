import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, ConversationStatus, UserRole
from src.services.whatsapp_service import WhatsappService
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


@pytest.fixture
def template_service():
    return TemplateService()


@pytest.mark.asyncio
async def test_onboarding_flow_create(
    test_session: AsyncSession, template_service: TemplateService
):
    # Setup User (New user)
    biz = Business(name="Temp Biz")
    test_session.add(biz)
    await test_session.flush()
    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.commit()

    mock_parser = AsyncMock()
    service = WhatsappService(test_session, mock_parser, template_service)
    user_phone = "123456789"

    # 1. First message -> Welcome message + choice
    response = await service.handle_message(
        "Hi", user_phone=user_phone, is_new_user=True
    )
    assert "Welcome to HereCRM!" in response
    assert "1. *Create a new business*" in response
    assert "2. *Join an existing one*" in response

    # 2. Choose 1 (Create)
    response = await service.handle_message("1", user_phone=user_phone)
    assert template_service.render("onboarding_create_success") in response

    # 3. Verify state is IDLE
    from src.repositories import ConversationStateRepository

    state_repo = ConversationStateRepository(test_session)
    state = await state_repo.get_by_user_id(user.id)
    assert state.state == ConversationStatus.IDLE


@pytest.mark.asyncio
async def test_onboarding_flow_join(
    test_session: AsyncSession, template_service: TemplateService
):
    # Setup User (New user)
    biz = Business(name="Temp Biz")
    test_session.add(biz)
    await test_session.flush()
    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)

    # Create an invitation
    from src.models import Invitation, InvitationStatus

    inviter = User(phone_number="999", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(inviter)
    await test_session.flush()

    invite = Invitation(
        business_id=biz.id,
        inviter_id=inviter.id,
        invitee_identifier="123456789",
        token="INVITE123",
        status=InvitationStatus.PENDING,
    )
    test_session.add(invite)
    await test_session.commit()

    mock_parser = AsyncMock()
    service = WhatsappService(test_session, mock_parser, template_service)
    user_phone = "123456789"

    # 1. First message
    await service.handle_message("Hi", user_phone=user_phone, is_new_user=True)

    # 2. Choose 2 (Join)
    response = await service.handle_message("2", user_phone=user_phone)
    assert template_service.render("onboarding_join_prompt") in response

    # 3. Provide code
    response = await service.handle_message("INVITE123", user_phone=user_phone)
    assert "Welcome to Temp Biz!" in response

    # 4. Verify state is IDLE
    from src.repositories import ConversationStateRepository

    state_repo = ConversationStateRepository(test_session)
    state = await state_repo.get_by_user_id(user.id)
    assert state.state == ConversationStatus.IDLE
