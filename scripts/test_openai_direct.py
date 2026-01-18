import asyncio
import os
from openai import AsyncOpenAI
from src.config import settings

async def test_direct():
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )
    
    print(f"Using key: {settings.openrouter_api_key[:10]}...")
    
    try:
        response = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[{"role": "user", "content": "Say hello"}],
        )
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error without headers: {e}")

    client_with_headers = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        default_headers={
            "HTTP-Referer": "https://herecrm.io",
            "X-Title": "HereCRM",
        }
    )
    
    async_client_empty = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="",
    )
    try:
        print("\nTesting with empty key...")
        await async_client_empty.chat.completions.create(
            model=settings.openrouter_model,
            messages=[{"role": "user", "content": "Say hello"}],
        )
    except Exception as e:
        print(f"Error with empty key: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct())
