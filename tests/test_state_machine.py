import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import (
    Business,
    User,
    ConversationState,
    ConversationStatus,
    Job,
    Request,
)
from src.services.whatsapp_service import WhatsappService
from src.uimodels import AddJobTool, StoreRequestTool

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
async def test_state_idle_to_confirm(test_session: AsyncMock):
    # Mock Parser
    mock_parser = AsyncMock()
    tool_call = AddJobTool(
        customer_name="John Doe", description="Fix window", price=50.0
    )
    mock_parser.parse.return_value = tool_call

    service = WhatsappService(test_session, mock_parser)
    user_phone = "123456789"

    # Send message in IDLE state
    response = await service.handle_message(
        user_phone, "Add job John Doe Fix window 50"
    )

    assert "Please confirm" in response

    # Verify state updated in DB
    from sqlalchemy import select

    res = await test_session.execute(
        select(ConversationState).where(ConversationState.phone_number == user_phone)
    )
    state = res.scalar_one()
    assert state.state == ConversationStatus.WAITING_CONFIRM
    assert state.draft_data["tool_name"] == "AddJobTool"


@pytest.mark.asyncio
async def test_state_confirm_yes(test_session: AsyncSession):
    # Setup: User in WAITING_CONFIRM state
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id)
    state = ConversationState(
        phone_number="123456789",
        state=ConversationStatus.WAITING_CONFIRM,
        draft_data={
            "tool_name": "AddJobTool",
            "arguments": {
                "customer_name": "John Doe",
                "description": "Fix window",
                "price": 50.0,
            },
        },
    )
    test_session.add(user)
    test_session.add(state)
    await test_session.commit()

    mock_parser = AsyncMock()
    service = WhatsappService(test_session, mock_parser)

    # Confirm
    response = await service.handle_message("123456789", "Yes")

    assert "Job added" in response

    # Verify job created
    from sqlalchemy import select

    res = await test_session.execute(select(Job))
    job = res.scalar_one()
    assert job.description == "Fix window"
    assert job.business_id == biz.id

    # Verify state reset
    res = await test_session.execute(
        select(ConversationState).where(ConversationState.phone_number == "123456789")
    )
    state = res.scalar_one()
    assert state.state == ConversationStatus.IDLE
    assert state.draft_data is None


@pytest.mark.asyncio
async def test_undo_functionality(test_session: AsyncSession):
    # Setup: Just finished an operation
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id)
    test_session.add(user)

    job = Job(
        business_id=biz.id, customer_id=1, description="To be undone", status="pending"
    )
    test_session.add(job)
    await test_session.flush()

    state = ConversationState(
        phone_number="123456789",
        state=ConversationStatus.IDLE,
        last_action_metadata={"action": "create", "entity": "job", "id": job.id},
    )
    test_session.add(state)
    await test_session.commit()

    mock_parser = AsyncMock()
    service = WhatsappService(test_session, mock_parser)

    # Undo
    response = await service.handle_message("123456789", "undo")

    assert "Undone: Deleted job" in response

    # Verify job deleted
    from sqlalchemy import select

    res = await test_session.execute(select(Job))
    assert res.scalar_one_or_none() is None
