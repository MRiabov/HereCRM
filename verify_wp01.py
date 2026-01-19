import asyncio
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.config import channels_config
from src.llm_client import parser

async def verify():
    print("Checking channels_config...")
    print(f"Channels: {list(channels_config.channels.keys())}")
    assert "whatsapp" in channels_config.channels
    assert channels_config.channels["whatsapp"].max_length == 150
    print("✓ channels_config loaded correctly.")

    print("\nChecking chat_completion...")
    try:
        response = await parser.chat_completion([
            {"role": "user", "content": "Hello, say 'Test OK'"}
        ])
        print(f"LLM Response: {response}")
        if "Test OK" in response:
            print("✓ chat_completion works.")
        else:
            print("✗ chat_completion produced unexpected output.")
    except Exception as e:
        print(f"✗ chat_completion failed: {e}")

    print("\nChecking manual.md...")
    if os.path.exists("src/assets/manual.md"):
        print("✓ src/assets/manual.md exists.")
    else:
        print("✗ src/assets/manual.md missing.")

if __name__ == "__main__":
    asyncio.run(verify())
