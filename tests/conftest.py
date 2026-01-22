import os
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models import Base
from src.database import engine

# Inject dummy keys BEFORE standard imports can fail
os.environ["GOOGLE_API_KEY"] = "dummy_test_key"
os.environ["WHATSAPP_APP_SECRET"] = "dummy_secret"
os.environ["WA_TOKEN"] = "dummy_token"
os.environ["WA_PHONE_ID"] = "dummy_phone_id"
os.environ["ALLOW_LOCAL_IMPORT"] = "true"
os.environ["QB_CLIENT_ID"] = "dummy_qb_client_id"
os.environ["QB_CLIENT_SECRET"] = "dummy_qb_client_secret"
os.environ["QB_REDIRECT_URI"] = "http://localhost:8000/callback"
os.environ["CREDENTIALS_DB_KEY"] = "dummy_key_for_testing_only_12345"


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    # This fixture ensures these remain set, though the top-level
    # execution is what really saves us from import errors.
    os.environ["WA_PHONE_ID"] = "dummy_phone_id"
    yield

@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Create database tables before each test."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def async_session():
    # Create an in-memory SQLite database for specific session testing if needed
    # but usually we can just use the global engine if it's also in-memory
    # For now, keeping the HEAD version of async_session
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
