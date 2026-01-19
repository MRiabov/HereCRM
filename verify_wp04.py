import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.services.help_service import HelpService
from src.models import Message, MessageRole

async def verify_wp04():
    mock_db = AsyncMock()
    service = HelpService(mock_db)
    
    print("Testing fallback manual...")
    # Temporarily rename manual.md if it exists
    manual_path = "src/assets/manual.md"
    temp_path = "src/assets/manual.md.bak"
    has_manual = os.path.exists(manual_path)
    if has_manual:
        os.rename(manual_path, temp_path)
    
    try:
        service._manual_cache = None # Clear cache
        manual = service._load_manual()
        print(f"Fallback manual: {manual}")
        assert "try 'add lead John Doe'" in manual
        print("✓ Fallback manual works.")
    finally:
        if has_manual:
            os.rename(temp_path, manual_path)

    print("\nTesting error context in prompt...")
    msg = Message(
        business_id=1,
        from_number="+1",
        body="Why did it fail?",
        role=MessageRole.USER,
        log_metadata={"error": "Customer not found"}
    )
    prompt = service.construct_help_prompt([msg], "whatsapp")
    # Prompt[0] is system, Prompt[1] is user message with metadata
    user_content = prompt[1]["content"]
    print(f"User content with metadata: {user_content}")
    assert "System Note: Context/Error: Customer not found" in user_content
    print("✓ Error context included in prompt.")

if __name__ == "__main__":
    asyncio.run(verify_wp04())
