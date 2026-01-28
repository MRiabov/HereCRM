import logging
from typing import List, Any
from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from src.database import Base, DATABASE_URL

logger = logging.getLogger(__name__)

def validate_db_schema() -> List[Any]:
    """
    Compares the current SQLAlchemy metadata with the actual database schema.
    Returns a list of detected differences.
    """
    # Convert async sqlite URL to sync for Alembic comparison
    # Alembic/SQLAlchemy comparison tools work best with sync engines
    sync_url = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
    
    # Using a sync engine for schema inspection
    engine = create_engine(sync_url)
    
    try:
        with engine.connect() as connection:
            mc = MigrationContext.configure(connection)
            diff = compare_metadata(mc, Base.metadata)
            
            if diff:
                logger.error("Database schema mismatch detected!")
                for change in diff:
                    logger.error(f"  - {change}")
                return diff
            else:
                logger.info("Database schema is in sync with models.")
                return []
    except Exception as e:
        logger.error(f"Error during schema validation: {e}")
        # If we can't even validate, we should probably treat it as a failure
        return [("error", str(e))]
    finally:
        engine.dispose()
