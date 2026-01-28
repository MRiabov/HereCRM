import asyncio
import os
import time
from httpx import AsyncClient, ASGITransport

# Mock envs
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["POSTHOG_API_KEY"] = "dummy_key"
os.environ["POSTHOG_HOST"] = "https://dummy.host"
os.environ["CLERK_JWKS_URL"] = "https://dummy.clerk.accounts.dev/.well-known/jwks.json"
os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_dummy"
os.environ["OPENROUTER_API_KEY"] = "dummy"
os.environ["WHATSAPP_APP_SECRET"] = "dummy"

# Mock PostHog
import sys
from unittest.mock import MagicMock
# Use the same mocking strategy as conftest
try:
    import posthog
    posthog.Posthog = MagicMock()
except ImportError:
    if "posthog" not in sys.modules:
        sys.modules["posthog"] = MagicMock()

# Import App
print("Importing app...")
t0 = time.time()
from src.main import app
from src.api.dependencies.clerk_auth import verify_token, get_current_user
from src.models import User, UserRole, Business, Base
from src.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

print(f"App imported in {time.time()-t0:.2f}s")

async def mock_user():
    return User(
        id=1,
        clerk_id="user_test",
        name="Test User",
        email="test@example.com",
        business_id=1,
        role=UserRole.OWNER
    )

app.dependency_overrides[verify_token] = mock_user
app.dependency_overrides[get_current_user] = mock_user

async def main():
    print("Setting up DB...")
    t0 = time.time()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add dummy business and user
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        biz = Business(id=1, name="Test Business")
        session.add(biz)
        await session.flush()
        user = User(
            id=1,
            clerk_id="user_test",
            name="Test User",
            email="test@example.com",
            business_id=1,
            role=UserRole.OWNER
        )
        session.add(user)
        await session.commit()
    print(f"DB setup in {time.time()-t0:.2f}s")

    print("Sending request...")
    t0 = time.time()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/pwa/dashboard/stats")

    print(f"Request finished in {time.time()-t0:.2f}s")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(main())
