import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import load_channels_config
from src.llm_client import parser


async def verify():
    print("--- Verifying Channel Config ---")
    try:
        config = load_channels_config()
        print(f"Loaded config: {config}")
        assert "whatsapp" in config.channels
        assert config.channels["whatsapp"].max_length == 150
        assert config.channels["email"].style == "detailed"
        print("✅ Channel Config verified.")
    except Exception as e:
        print(f"❌ Channel Config failed: {e}")
        return

    print("\n--- Verifying Chat Completion ---")
    messages = [{"role": "user", "content": "Say hello in one word."}]
    try:
        response = await parser.chat_completion(messages)
        print(f"Response: {response}")
        assert len(response) > 0
        print("✅ Chat Completion verified.")
    except Exception as e:
        print(f"❌ Chat Completion failed: {e}")


if __name__ == "__main__":
    asyncio.run(verify())
