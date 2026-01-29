import httpx
import asyncio


async def test_webhook():
    url = "http://localhost:8000/webhooks/generic"

    # Test 1: New User via Email
    payload = {
        "identity": "test_zapier@example.com",
        "message": "Hello from Zapier, I want to add a job for John Doe",
        "source": "Zapier",
    }

    print(f"Sending payload: {payload}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error connecting to server: {e}")
            print(
                "Is the server running? Start it with 'uvicorn src.main:app --reload'"
            )


if __name__ == "__main__":
    asyncio.run(test_webhook())
