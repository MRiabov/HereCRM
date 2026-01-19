import pytest
import os
from unittest.mock import AsyncMock, patch
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

    # Create some messages
    # We use explicit created_at to ensure order
    m1 = Message(
        business_id=biz.id,
        from_number="123",
        to_number="456",
        body="Hello",
        role=MessageRole.USER,
        created_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    m2 = Message(
        business_id=biz.id,
        from_number="456",
        to_number="123",
        body="Hi there",
        role=MessageRole.ASSISTANT,
        created_at=datetime(2026, 1, 1, 10, 1, 0, tzinfo=timezone.utc)
    )
    m3 = Message(
        business_id=biz.id,
        from_number="123",
        to_number="456",
        body="How are you?",
        role=MessageRole.USER,
        created_at=datetime(2026, 1, 1, 10, 2, 0, tzinfo=timezone.utc)
    )
    
    async_session.add_all([m1, m2, m3])
    await async_session.commit()

    service = HelpService(async_session)
    
    # Test limit=2
    history = await service.get_chat_history(biz.id, "123", limit=2)
    assert len(history) == 2
    assert history[0].body == "Hi there"
    assert history[1].body == "How are you?"
    
    # Test limit=5
    history_all = await service.get_chat_history(biz.id, "123", limit=5)
    assert len(history_all) == 3
    assert history_all[0].body == "Hello"
    assert history_all[1].body == "Hi there"
    assert history_all[2].body == "How are you?"

@pytest.mark.asyncio
async def test_construct_help_prompt(async_session: AsyncSession):
    service = HelpService(async_session)
    
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
    # Check if channel restrictions are present (whatsapp is mapped to concise/150 in config)
    assert "150" in prompt[0]["content"] or "concise" in prompt[0]["content"].lower()
    
    assert prompt[1]["role"] == "user"
    assert prompt[1]["content"] == "Help me"
    
    assert prompt[2]["role"] == "assistant"
    assert "Sure" in prompt[2]["content"]
    assert "Something went wrong" in prompt[2]["content"]

@pytest.mark.asyncio
async def test_manual_loading_caching(async_session: AsyncSession):
    service = HelpService(async_session)
    
    # First call loads from file
    manual1 = service._load_manual()
    assert manual1 is not None
    assert "CRM" in manual1
    
    # Cache should be set
    assert service._manual_cache == manual1
    
    # Second call should use cache
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
    
    # Add a message to history
    m1 = Message(
        business_id=biz.id,
        from_number="123",
        body="How do I add a job?",
        role=MessageRole.USER
    )
    async_session.add(m1)
    await async_session.commit()

    with patch("src.services.help_service.parser") as mock_parser:
        mock_parser.chat_completion = AsyncMock(return_value="To add a job, type 'add job'.")
        
        service = HelpService(async_session)
        response = await service.generate_help_response(biz.id, "123", "whatsapp")
        
        assert response == "To add a job, type 'add job'."
        mock_parser.chat_completion.assert_called_once()
        
        # Verify the prompt passed to chat_completion
        args, _ = mock_parser.chat_completion.call_args
        prompt = args[0]
        assert prompt[0]["role"] == "system"
        assert "MANUAL CONTENT" in prompt[0]["content"]
        assert prompt[1]["role"] == "user"
        assert prompt[1]["content"] == "How do I add a job?"
