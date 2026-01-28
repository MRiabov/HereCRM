import os

# Inject dummy keys and FORCE in-memory database BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["GOOGLE_API_KEY"] = "dummy_test_key"
os.environ["WHATSAPP_APP_SECRET"] = "dummy_secret"
os.environ["WA_TOKEN"] = "dummy_token"
os.environ["WA_PHONE_ID"] = "dummy_phone_id"
os.environ["ALLOW_LOCAL_IMPORT"] = "true"
os.environ["QB_CLIENT_ID"] = "dummy_qb_client_id"
os.environ["QB_CLIENT_SECRET"] = "dummy_qb_client_secret"
os.environ["QB_REDIRECT_URI"] = "http://localhost:8000/callback"
os.environ["CREDENTIALS_DB_KEY"] = "dummy_key_for_testing_only_12345"

# Clerk Settings for tests
os.environ["CLERK_SECRET_KEY"] = "sk_test_dummy"
os.environ["CLERK_PUBLISHABLE_KEY"] = "pk_test_dummy"
os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
os.environ["CLERK_JWKS_URL"] = "https://dummy.clerk.accounts.dev/.well-known/jwks.json"
os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_dummy"

# PostHog Settings for tests
os.environ["POSTHOG_API_KEY"] = "dummy_key"
os.environ["POSTHOG_HOST"] = "https://dummy.host"

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models import Base
from src.database import engine
from src.events import event_bus

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    # This fixture ensures these remain set, though the top-level
    # execution is what really saves us from import errors.
    os.environ["WA_PHONE_ID"] = "dummy_phone_id"
    yield

@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset EventBus subscribers before each test."""
    event_bus._subscribers = {}
    yield

@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Create database tables before each test."""
    # Create all tables using the global engine which is now in-memory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables after test to ensure isolation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def async_session():
    # Create an in-memory SQLite database for specific session testing if needed
    # but usually we can just use the global engine if it's also in-memory
    engine_sqlite = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine_sqlite.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_maker = sessionmaker(
        engine_sqlite, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    # Dispose engine
    await engine_sqlite.dispose()

# Global engine disposal after each test
@pytest.fixture(scope="function", autouse=True)
async def dispose_engine():
    yield
    await engine.dispose()
