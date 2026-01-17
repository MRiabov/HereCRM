from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import logging

import os

# Using relative path for SQLite database as default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crm.db")

# Helper to ensure database directory exists if using SQLite
if "sqlite" in DATABASE_URL:
    try:
        # Extract path from URL (remove scheme)
        # Handle "sqlite+aiosqlite:///" (absolute) vs "sqlite+aiosqlite:///" (relative) logic roughly
        # This is a basic check for typical usage
        db_path = DATABASE_URL.split("///")[-1]
        
        # If it's a file path (not :memory:), make sure directory exists
        if db_path != ":memory:":
             # Handle absolute paths that might be passed incorrectly in some connection strings
             # But generally, os.path.dirname works if it looks like a path
             directory = os.path.dirname(db_path)
             if directory and not os.path.exists(directory):
                 os.makedirs(directory, exist_ok=True)
                 logging.info(f"Created database directory: {directory}")
    except Exception as e:
        logging.warning(f"Could not check/create database directory: {e}")

# Configure logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
