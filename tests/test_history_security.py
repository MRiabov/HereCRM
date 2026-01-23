import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings

@pytest.mark.asyncio
async def test_history_endpoint_requires_auth():
    """
    Test that the /history endpoint requires authentication.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        phone = "15551234567"

        # Request history for a phone number without any auth headers
        response = await ac.get(f"/history/{phone}")

        # It should return 422 (Validation Error for missing header) or 403 (Forbidden)
        assert response.status_code in [422, 403]

@pytest.mark.asyncio
async def test_history_endpoint_rejects_invalid_key():
    """
    Test that the /history endpoint rejects invalid API keys.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        phone = "15551234567"

        response = await ac.get(
            f"/history/{phone}",
            headers={"X-Admin-Key": "wrong-key"}
        )

        assert response.status_code == 403

@pytest.mark.asyncio
async def test_history_endpoint_success():
    """
    Test that the /history endpoint works with a valid API key.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        phone = "15551234567"

        response = await ac.get(
            f"/history/{phone}",
            headers={"X-Admin-Key": settings.secret_key}
        )

        assert response.status_code == 200
        # Assert structure of response
        assert isinstance(response.json(), list)
