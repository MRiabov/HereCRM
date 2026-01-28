
import asyncio
from sqlalchemy import text
from src.database import engine

async def diagnose():
    async with engine.connect() as conn:
        print("\nChecking 'users' table info:")
        result = await conn.execute(text("PRAGMA table_info(users);"))
        for row in result:
            print(f" - {row[1]} ({row[2]})")

        print("\nChecking 'expenses' table info:")
        result = await conn.execute(text("PRAGMA table_info(expenses);"))
        for row in result:
            print(f" - {row[1]} ({row[2]})")
            
        print("\nChecking foreign keys for 'expenses':")
        result = await conn.execute(text("PRAGMA foreign_key_list(expenses);"))
        for row in result:
            print(f" - {row}")

if __name__ == "__main__":
    asyncio.run(diagnose())
