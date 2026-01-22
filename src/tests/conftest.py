import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.database import Base
import src.database

import os
# Use a temporary file for tests to ensure visibility across multiple sessions
TEST_DB_FILE = "./test_crm.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def patch_db(monkeypatch):
    # Patch the app's database engine and session maker
    monkeypatch.setattr(src.database, "engine", test_engine)
    monkeypatch.setattr(src.database, "AsyncSessionLocal", TestAsyncSessionLocal)
    
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # No drop_all needed, we remove the file
    await test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest_asyncio.fixture(scope="function")
async def session():
    async with TestAsyncSessionLocal() as s:
        yield s

