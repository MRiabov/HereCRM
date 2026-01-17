import asyncio
from sqlalchemy import select
from src.database import AsyncSessionLocal, engine, Base
from src.models import Message

async def check_messages():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Message))
        messages = result.scalars().all()
        print(f"Total messages in DB: {len(messages)}")
        for msg in messages:
            print(f"[{msg.created_at}] {msg.role}: {msg.body}")
            if msg.log_metadata:
                print(f"    Metadata: {msg.log_metadata}")

async def check_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/history/1234567890")
        if response.status_code == 200:
            history = response.json()
            print(f"API History count: {len(history)}")
        else:
            print(f"API Error: {response.status_code}")

if __name__ == "__main__":
    import httpx
    asyncio.run(check_messages())
    asyncio.run(check_api())
