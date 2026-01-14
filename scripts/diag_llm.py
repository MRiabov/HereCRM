import asyncio
import os
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from src.config import settings
except ImportError:
    settings = None


async def diag():
    print("Diagnostics for OpenRouter")
    api_key = (
        settings.openrouter_api_key if settings else os.getenv("OPENROUTER_API_KEY")
    )
    model = (
        settings.openrouter_model
        if settings
        else os.getenv("OPENROUTER_MODEL", "openrouter/auto")
    )

    print(f"API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'NONE'}")
    print(f"Model: {model}")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    try:
        print("Sending test request...")
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
        )
        print(f"Response: {response.choices[0].message.content}")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(diag())
