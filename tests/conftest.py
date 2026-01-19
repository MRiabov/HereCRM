import os
import pytest

# Inject dummy keys BEFORE standard imports can fail
os.environ["GOOGLE_API_KEY"] = "dummy_test_key"
os.environ["WHATSAPP_APP_SECRET"] = "dummy_secret"
os.environ["WA_TOKEN"] = "dummy_token"
os.environ["WA_PHONE_ID"] = "dummy_phone_id"
os.environ["ALLOW_LOCAL_IMPORT"] = "true"


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    # This fixture ensures these remain set, though the top-level
    # execution is what really saves us from import errors.
    os.environ["WA_PHONE_ID"] = "dummy_phone_id"
    yield

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models import Base

@pytest.fixture(scope="function")
async def async_session():
    # Create an in-memory SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    # Dispose engine
    await engine.dispose()
