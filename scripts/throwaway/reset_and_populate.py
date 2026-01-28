import asyncio
from src.database import AsyncSessionLocal
from src.api.v1.pwa.dev import populate_demo_data
from src.models import Base
from src.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        await populate_demo_data(db)
        print("Database reset and populated with E2E test data.")

if __name__ == "__main__":
    asyncio.run(main())
