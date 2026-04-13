from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import List, Optional, Any
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool
import logging
import os
import asyncio
import json
from datetime import date, datetime
from typing import Dict, Optional, Any
from contextvars import ContextVar

# Using relative path for SQLite database as default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/crm.db")

# ContextVar to track current test database name for background workers
current_db_name: ContextVar[Optional[str]] = ContextVar("current_db_name", default=None)

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

# Detect if we are using in-memory SQLite (usually during tests)
is_memory = "sqlite" in DATABASE_URL and ":memory:" in DATABASE_URL

engine_args = {}
if is_memory:
    engine_args["poolclass"] = StaticPool
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(DATABASE_URL, echo=False, **engine_args)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# Detector and registry for dynamic engines (test isolation)
class EngineRegistry:
    def __init__(self):
        self._engines: Dict[str, async_sessionmaker] = {}
        self._lock = asyncio.Lock()

    async def get_session_maker(self, db_name: str) -> async_sessionmaker:
        if db_name in self._engines:
            return self._engines[db_name]

        async with self._lock:
            if db_name in self._engines:
                return self._engines[db_name]

            # Create new engine for the specific test database
            # Ensure it's in a safe directory (e.g., ./data/tests/)
            os.makedirs("./data/tests", exist_ok=True)
            db_url = f"sqlite+aiosqlite:///./data/tests/{db_name}.db"

            new_engine = create_async_engine(
                db_url,
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )

            # Initialize schema
            async with new_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            new_session_maker = async_sessionmaker(
                bind=new_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            self._engines[db_name] = new_session_maker
            logging.info(f"Initialized dynamic test database: {db_name}")
            return new_session_maker

    async def dispose_all(self):
        for maker in self._engines.values():
            await maker.kw["bind"].dispose()


engine_registry = EngineRegistry()


def _sqlite_literal(value: Any) -> Optional[str]:
    """Render a Python value as a SQLite literal for ADD COLUMN defaults."""
    if hasattr(value, "value"):
        value = value.value

    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return f"'{json.dumps(value)}'"
    if isinstance(value, datetime):
        return f"'{value.isoformat(sep=' ')}'"
    if isinstance(value, date):
        return f"'{value.isoformat()}'"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"

    return None


def _sqlite_add_column_clause(column, dialect) -> str:
    """Build a conservative SQLite ADD COLUMN clause for an ORM column."""
    column_name = dialect.identifier_preparer.quote(column.name)
    column_type = column.type.compile(dialect=dialect)
    clause = f"{column_name} {column_type}"

    default_value = None
    if column.default is not None and not getattr(column.default, "is_callable", False):
        default_value = _sqlite_literal(column.default.arg)
    elif column.server_default is not None:
        server_default = getattr(column.server_default, "arg", None)
        default_value = _sqlite_literal(server_default)

    if default_value is not None:
        clause += f" DEFAULT {default_value}"

    return clause


async def repair_sqlite_schema(target_engine=None) -> List[tuple[str, str]]:
    """
    Repair missing columns in existing SQLite tables without dropping data.

    This is intentionally conservative: it only adds missing columns that exist
    in the SQLAlchemy model metadata. Missing tables are still handled by
    Base.metadata.create_all().
    """

    if target_engine is None:
        target_engine = engine

    if getattr(target_engine.dialect, "name", "") != "sqlite":
        return []

    if getattr(target_engine.url, "database", None) == ":memory:":
        return []

    # Import models lazily so the declarative metadata is populated before we inspect it.
    import src.models  # noqa: F401

    repaired: List[tuple[str, str]] = []

    async with target_engine.begin() as conn:
        def plan_repair(sync_conn):
            inspector = inspect(sync_conn)
            existing_tables = set(inspector.get_table_names())
            planned: list[tuple[str, str, str]] = []

            for table in Base.metadata.sorted_tables:
                if table.name not in existing_tables:
                    continue

                existing_columns = {
                    column_info["name"] for column_info in inspector.get_columns(table.name)
                }

                for column in table.columns:
                    if column.name in existing_columns:
                        continue

                    planned.append(
                        (
                            table.name,
                            column.name,
                            _sqlite_add_column_clause(column, sync_conn.dialect),
                        )
                    )

            return planned

        planned_changes = await conn.run_sync(plan_repair)

        for table_name, column_name, clause in planned_changes:
            logging.getLogger("src.database").info(
                "Repairing SQLite schema: adding %s.%s", table_name, column_name
            )
            await conn.exec_driver_sql(f'ALTER TABLE "{table_name}" ADD COLUMN {clause}')
            repaired.append((table_name, column_name))

    return repaired


async def get_session_maker() -> async_sessionmaker:
    """Utility to get the correct session maker based on current ContextVar."""
    db_name = current_db_name.get()
    if db_name:
        return await engine_registry.get_session_maker(db_name)
    return AsyncSessionLocal


async def get_db(request: Optional[Any] = None):
    # Try to get database name from header for test isolation
    db_name = None
    if request:
        db_name = request.headers.get("X-Test-Database")

    token = current_db_name.set(db_name)
    try:
        if db_name:
            session_maker = await engine_registry.get_session_maker(db_name)
        else:
            session_maker = AsyncSessionLocal

        async with session_maker() as session:
            yield session
    finally:
        current_db_name.reset(token)


# Credentials database setup (SQLCipher-encrypted)
CREDENTIALS_DB_KEY = os.getenv("CREDENTIALS_DB_KEY")
if CREDENTIALS_DB_KEY:
    try:
        # Import pysqlcipher3 dynamically to handle potential import issues
        import pysqlcipher3.dbapi2 as sqlite

        credentials_engine = create_engine(
            f"sqlite+pysqlcipher://:{CREDENTIALS_DB_KEY}@/credentials.db?cipher=aes-256-cfb&kdf_iter=64000",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        CredentialsSessionLocal = sessionmaker(
            bind=credentials_engine,
            expire_on_commit=False,
        )

        logging.info("Credentials database engine configured successfully")

    except ImportError as e:
        logging.warning(f"pysqlcipher3 not available: {e}")
        logging.warning(
            "QuickBooks credentials encryption disabled - install sqlcipher system libraries and pysqlcipher3 Python package"
        )
        logging.warning("Ubuntu/Debian: sudo apt-get install sqlcipher")
        logging.warning("Then: uv sync or pip install pysqlcipher3")
        credentials_engine = None
        CredentialsSessionLocal = None
    except Exception as e:
        logging.error(f"Failed to configure credentials database: {e}")
        credentials_engine = None
        CredentialsSessionLocal = None
else:
    logging.info(
        "CREDENTIALS_DB_KEY environment variable not set - QuickBooks integration disabled"
    )
    credentials_engine = None
    CredentialsSessionLocal = None


def get_credentials_db():
    """Get a synchronous session for the credentials database."""
    if not CredentialsSessionLocal:
        raise RuntimeError("Credentials database not configured")
    return CredentialsSessionLocal()
