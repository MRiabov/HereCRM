import asyncio
import logging
import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from src.database import engine, Base
from src.models import Service, LineItem, Job

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    logger.info("Starting manual migration for 004-line-items-and-service-catalog...")
    
    async with engine.begin() as conn:
        # Check if tables exist
        logger.info("Checking/Creating tables: services, line_items")
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Migration completed successfully.")
    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_migration())
