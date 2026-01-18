import asyncio
import os
from openai import AsyncOpenAI
from src.config import settings

async def test_openrouter():
    print(f"Testing OpenRouter with key: {settings.openrouter_api_key[:10]}...")
    print(f"Base URL: https://openrouter.ai/api/v1")
    print(f"Model: {settings.openrouter_model}")
    
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )
    
    try:
        response = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            extra_body={
                "provider": {
                    "sort": "throughput",
                }
            },
        )
        print("Response received successfully!")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openrouter())
