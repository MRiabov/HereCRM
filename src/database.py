from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
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


# Credentials database setup (SQLCipher-encrypted)
CREDENTIALS_DB_KEY = os.getenv("CREDENTIALS_DB_KEY")
if CREDENTIALS_DB_KEY:
    try:
        # Import pysqlcipher3 dynamically to handle potential import issues
        import pysqlcipher3.dbapi2 as sqlite
        
        credentials_engine = create_engine(
            f"sqlite+pysqlcipher://:{CREDENTIALS_DB_KEY}@/credentials.db?cipher=aes-256-cfb&kdf_iter=64000",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        CredentialsSessionLocal = sessionmaker(
            bind=credentials_engine,
            expire_on_commit=False,
        )
        
        logging.info("Credentials database engine configured successfully")
        
    except ImportError as e:
        logging.warning(f"pysqlcipher3 not available: {e}")
        logging.warning("QuickBooks credentials encryption disabled - install sqlcipher system libraries and pysqlcipher3 Python package")
        logging.warning("Ubuntu/Debian: sudo apt-get install sqlcipher")
        logging.warning("Then: uv sync or pip install pysqlcipher3")
        credentials_engine = None
        CredentialsSessionLocal = None
    except Exception as e:
        logging.error(f"Failed to configure credentials database: {e}")
        credentials_engine = None
        CredentialsSessionLocal = None
else:
    logging.info("CREDENTIALS_DB_KEY environment variable not set - QuickBooks integration disabled")
    credentials_engine = None
    CredentialsSessionLocal = None


def get_credentials_db():
    """Get a synchronous session for the credentials database."""
    if not CredentialsSessionLocal:
        raise RuntimeError("Credentials database not configured")
    return CredentialsSessionLocal()
