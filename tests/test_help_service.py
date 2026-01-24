import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.help_service import HelpService
from src.models import Message, MessageRole, Business
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_get_chat_history(async_session: AsyncSession):
    # Setup: Create a business
    biz = Business(name="Test Biz")
    async_session.add(biz)
    await async_session.commit()
    await async_session.refresh(biz)

    # Create a user
    user = User(business_id=biz.id, phone_number="123", role="owner")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create some messages
    m1 = Message(
        business_id=biz.id,
        user_id=user.id,
        from_number="123",
        body="Hello",
        role=MessageRole.USER,
        created_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    m2 = Message(
        business_id=biz.id,
        user_id=user.id,
        from_number="456",
        to_number="123",
        body="Hi there",
        role=MessageRole.ASSISTANT,
        created_at=datetime(2026, 1, 1, 10, 1, 0, tzinfo=timezone.utc)
    )
    m3 = Message(
        business_id=biz.id,
        user_id=user.id,
        from_number="123",
        body="How are you?",
        role=MessageRole.USER,
        created_at=datetime(2026, 1, 1, 10, 2, 0, tzinfo=timezone.utc)
    )
    
    async_session.add_all([m1, m2, m3])
    await async_session.commit()

    service = HelpService(async_session, MagicMock())
    
    history = await service.get_chat_history(biz.id, user.id, limit=2)
    assert len(history) == 2
    assert history[0].body == "Hi there"
    assert history[1].body == "How are you?"
    
    history_all = await service.get_chat_history(biz.id, user.id, limit=5)
    assert len(history_all) == 3

@pytest.mark.asyncio
async def test_construct_help_prompt(async_session: AsyncSession):
    service = HelpService(async_session, MagicMock())
    
    m1 = Message(
        body="Help me",
        role=MessageRole.USER
    )
    m2 = Message(
        body="Sure",
        role=MessageRole.ASSISTANT,
        log_metadata={"error": "Something went wrong"}
    )
    
    prompt = service.construct_help_prompt([m1, m2], "whatsapp")
    
    assert len(prompt) == 3 # System + 2 messages
    assert prompt[0]["role"] == "system"
    assert "MANUAL CONTENT" in prompt[0]["content"]
    assert "150" in prompt[0]["content"] or "concise" in prompt[0]["content"].lower()
    
    assert prompt[1]["role"] == "user"
    assert prompt[1]["content"] == "Help me"
    
    assert prompt[2]["role"] == "assistant"
    assert "Sure" in prompt[2]["content"]
    assert "Something went wrong" in prompt[2]["content"]

@pytest.mark.asyncio
async def test_manual_loading_caching(async_session: AsyncSession):
    service = HelpService(async_session, MagicMock())
    
    manual1 = service._load_manual()
    assert manual1 is not None
    assert "CRM" in manual1
    
    assert service._manual_cache == manual1
    
    service._manual_cache = "Modified Cache"
    manual2 = service._load_manual()
    assert manual2 == "Modified Cache"

@pytest.mark.asyncio
async def test_generate_help_response(async_session: AsyncSession):
    # Setup business
    biz = Business(name="Test Biz")
    async_session.add(biz)
    await async_session.commit()
    await async_session.refresh(biz)
    
    # Create a user
    user = User(business_id=biz.id, phone_number="123", role="owner")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Add a previous message to history
    m1 = Message(
        business_id=biz.id,
        user_id=user.id,
        from_number="123",
        body="Previous message",
        role=MessageRole.USER
    )
    async_session.add(m1)
    await async_session.commit()

    mock_llm = MagicMock()
    mock_llm.chat_completion = AsyncMock(return_value="To add a job, type 'add job'.")
    
    service = HelpService(async_session, mock_llm)
    user_query = "How do I add a job?"
    response = await service.generate_help_response(user_query, biz.id, user.id, "whatsapp")
    
    assert response == "To add a job, type 'add job'."
    mock_llm.chat_completion.assert_called_once()
    
    args, _ = mock_llm.chat_completion.call_args
    prompt = args[0]
    assert prompt[0]["role"] == "system"
    assert prompt[1]["role"] == "user"
    assert prompt[1]["content"] == "Previous message"
    assert prompt[2]["role"] == "user"
    assert prompt[2]["content"] == user_query
