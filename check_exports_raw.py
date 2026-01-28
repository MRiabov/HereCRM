import asyncio
from sqlalchemy import text
from src.database import engine

async def check_failed_exports_raw():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, status, query, format, created_at FROM export_requests ORDER BY created_at DESC LIMIT 10"))
        exports = result.all()
        
        print(f"{'ID':<5} | {'Status':<12} | {'Query':<20} | {'Format':<8} | {'Created At'}")
        print("-" * 70)
        for e in exports:
            print(f"{e[0]:<5} | {e[1]:<12} | {str(e[2])[:20]:<20} | {e[3]:<8} | {e[4]}")

if __name__ == "__main__":
    asyncio.run(check_failed_exports_raw())
