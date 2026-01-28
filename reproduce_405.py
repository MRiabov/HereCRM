import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.api.dependencies.clerk_auth import get_current_user, verify_token
from src.models import User

async def mock_auth():
    return User(id=1, clerk_id="test_clerk", business_id=1)

async def reproduce():
    # Override auth
    app.dependency_overrides[get_current_user] = mock_auth
    app.dependency_overrides[verify_token] = mock_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test Onboarding
        print("Testing /api/v1/pwa/onboarding/choice...")
        resp = await client.post("/api/v1/pwa/onboarding/choice", json={"choice": "create"})
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text}")

        # Test Onboarding with trailing slash
        print("\nTesting /api/v1/pwa/onboarding/choice/...")
        resp = await client.post("/api/v1/pwa/onboarding/choice/", json={"choice": "create"})
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text}")

        # Test Analytics Proxy
        print("\nTesting /api/v1/pwa/analytics/proxy/e/...")
        resp = await client.post("/api/v1/pwa/analytics/proxy/e/", json={"test": "data"})
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text}")

        # Test Analytics Proxy without trailing slash
        print("\nTesting /api/v1/pwa/analytics/proxy/e...")
        resp = await client.post("/api/v1/pwa/analytics/proxy/e", json={"test": "data"})
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text}")

if __name__ == "__main__":
    asyncio.run(reproduce())
