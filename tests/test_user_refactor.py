import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from src.database import Base
from src.models import Business, User, ConversationState
from src.repositories import UserRepository, ConversationStateRepository

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
async def test_user_creation_and_lookup(test_session: AsyncSession):
    # Setup
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user_repo = UserRepository(test_session)

    # 1. Create user with phone
    user1 = User(phone_number="12345", business_id=biz.id)
    test_session.add(user1)
    await test_session.commit()
    
    assert user1.id is not None
    assert user1.phone_number == "12345"

    # 2. Lookup by ID
    found = await user_repo.get_by_id(user1.id)
    assert found.id == user1.id
    assert found.phone_number == "12345"

    # 3. Lookup by phone
    found_by_phone = await user_repo.get_by_phone("12345")
    assert found_by_phone.id == user1.id

    # 4. Create user with email
    user2 = User(email="test@example.com", business_id=biz.id)
    test_session.add(user2)
    await test_session.commit()

    assert user2.id is not None
    assert user2.id != user1.id
    assert user2.email == "test@example.com"
    assert user2.phone_number is None

    # 5. Lookup by email
    found_by_email = await user_repo.get_by_email("test@example.com")
    assert found_by_email.id == user2.id

@pytest.mark.asyncio
async def test_conversation_state_linkage(test_session: AsyncSession):
    # Setup
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123", business_id=biz.id)
    test_session.add(user)
    await test_session.flush()

    state_repo = ConversationStateRepository(test_session)
    
    # 1. Create state
    state = ConversationState(user_id=user.id)
    state_repo.add(state)
    await test_session.flush()

    found_state = await state_repo.get_by_user_id(user.id)
    assert found_state.user_id == user.id
    
    # 2. Verify link
    res = await test_session.execute(select(User).where(User.id == user.id))
    u = res.scalar_one()
    assert u.conversation_state.user_id == user.id
