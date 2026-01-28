import asyncio
from sqlalchemy import select, text
from src.database import AsyncSessionLocal
from src.models import Business

async def diagnose():
    async with AsyncSessionLocal() as session:
        # 1. Check which database file we are connected to
        result = await session.execute(text("PRAGMA database_list;"))
        rows = result.fetchall()
        print("\nDatabase list:")
        for row in rows:
            print(f" - {row}")
            
        # 2. Check columns in businesses table
        result = await session.execute(text("PRAGMA table_info(businesses);"))
        columns = result.fetchall()
        print("\nColumns in 'businesses':")
        for col in columns:
            print(f" - {col[1]} ({col[2]})")
            
        # 3. Try the problematic query
        try:
            print("\nAttempting to query Business model...")
            stmt = select(Business).limit(1)
            result = await session.execute(stmt)
            biz = result.scalar_one_or_none()
            if biz:
                print(f"Successfully retrieved business: {biz.name}")
                print(f"Default City: {biz.default_city}")
            else:
                print("No business found.")
        except Exception as e:
            print(f"\nQUERY FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
