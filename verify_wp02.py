import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.getcwd())

from src.services.help_service import HelpService
from src.models import Message, MessageRole

async def verify_help_service():
    # Mock DB Session
    mock_db = AsyncMock()
    
    # Mock history records
    msg1 = Message(
        business_id=1,
        from_number="+123456",
        body="How do I add a lead?",
        role=MessageRole.USER,
        created_at=datetime.now(timezone.utc)
    )
    
    # Mock result from DB
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [msg1]
    mock_db.execute.return_value = mock_result
    
    service = HelpService(mock_db)
    
    print("Testing manual load...")
    manual = service._load_manual()
    print(f"Manual length: {len(manual)}")
    assert "HereCRM Product Manual" in manual
    print("✓ Manual loaded.")

    print("\nTesting get_chat_history...")
    history = await service.get_chat_history(1, "+123456")
    assert len(history) == 1
    assert history[0].body == "How do I add a lead?"
    print("✓ get_chat_history works.")

    print("\nTesting construct_help_prompt...")
    prompt = service.construct_help_prompt(history, "whatsapp")
    # Prompt should have system message + history (1 message) = 2 total
    assert len(prompt) == 2
    assert prompt[0]["role"] == "system"
    assert "concise" in prompt[0]["content"]
    assert prompt[1]["role"] == "user"
    assert "How do I add a lead?" in prompt[1]["content"]
    print("✓ construct_help_prompt works.")

if __name__ == "__main__":
    asyncio.run(verify_help_service())
