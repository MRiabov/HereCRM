import asyncio
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import ExportRequest

async def check_failed_exports():
    async with AsyncSessionLocal() as session:
        stmt = select(ExportRequest).order_by(ExportRequest.created_at.desc()).limit(10)
        result = await session.execute(stmt)
        exports = result.scalars().all()
        
        print(f"{'ID':<5} | {'Status':<12} | {'Query':<20} | {'Format':<8} | {'Created At'}")
        print("-" * 70)
        for e in exports:
            print(f"{e.id:<5} | {e.status:<12} | {e.query[:20]:<20} | {e.format:<8} | {e.created_at}")

if __name__ == "__main__":
    asyncio.run(check_failed_exports())
