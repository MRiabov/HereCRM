import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings

@pytest.mark.asyncio
async def test_history_endpoint_security():
    """
    Verifies that the history endpoint is now secured.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Attempt without key -> 401
        response = await client.get("/history/+15551234567")
        assert response.status_code == 401

        # 2. Attempt with correct key -> 200
        headers = {"X-Admin-Key": settings.secret_key}
        response = await client.get("/history/+15551234567", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
