import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db, AsyncSessionLocal as SessionLocal
from src.models import User, Business, UserRole
from sqlalchemy.ext.asyncio import AsyncSession
import json

async def debug_422():
    async with SessionLocal() as session:
        # Setup a test user and business
        biz = Business(name="Debug Biz")
        session.add(biz)
        await session.flush()
        
        user = User(
            clerk_id="debug_user",
            name="Debug User",
            email="debug@example.com",
            business_id=biz.id,
            role=UserRole.OWNER
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        async def mock_auth(*args, **kwargs):
            return user

        from src.api.dependencies.clerk_auth import get_current_user, verify_token
        app.dependency_overrides[get_current_user] = mock_auth
        app.dependency_overrides[verify_token] = mock_auth
        app.dependency_overrides[get_db] = lambda: session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test onboarding
            payload = {"choice": "create"}
            res = await client.post("/api/v1/pwa/onboarding/choice", json=payload)
            print(f"Onboarding Choice (create) status: {res.status_code}")
            if res.status_code == 422:
                print(f"422 Detail: {json.dumps(res.json(), indent=2)}")

            # Test customers list
            res = await client.get("/api/v1/pwa/customers/")
            print(f"Customers List status: {res.status_code}")
            if res.status_code == 422:
                print(f"422 Detail: {json.dumps(res.json(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(debug_422())
