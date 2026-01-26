import asyncio
import httpx
from datetime import date

async def verify_routing_api():
    base_url = "http://localhost:8000/api/v1/pwa"
    # We'd need a token, but let's see if we can at least check if the endpoint is registered (401 is better than 404)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/routing/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("Response:", response.json())
            elif response.status_code == 401:
                print("Endpoint registered (Auth required as expected)")
            else:
                print(f"Unexpected status: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_routing_api())
