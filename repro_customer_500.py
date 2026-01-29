
import asyncio
import os
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import Base, engine
# from sqlalchemy.ext.asyncio import create_async_engine

# Set env vars
os.environ["MOCK_AUTH_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

async def repro():
    # Initialize DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        print("Sending POST /api/v1/pwa/customers")
        response = await ac.post("/api/v1/pwa/customers/", json={
            "first_name": "Test",
            "last_name": "Repro",
            "email": "repro@example.com",
            "phone": "5550100",
            "street": "123 Integration St",
            "city": "Test City",
            "pipeline_stage": "NEW_LEAD"
        }, headers={"Authorization": "Bearer mock_token"})
        
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
        
        # Fetch errors
        print("Fetching backend errors...")
        err_resp = await ac.get("/api/v1/pwa/dev/errors", headers={"Authorization": "Bearer mock_token"})
        print(f"Errors Status: {err_resp.status_code}")
        print(f"Errors Body: {err_resp.text}")

if __name__ == "__main__":
    asyncio.run(repro())
