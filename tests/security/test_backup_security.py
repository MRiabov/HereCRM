import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
import os
from src.main import app
from src.api.v1.pwa.backup import get_data_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_backup_endpoint_security():
    # Mock the service
    mock_service = MagicMock()
    mock_service.backup_db = AsyncMock(return_value="https://s3.example.com/backup.sqlite")

    # Override dependency
    app.dependency_overrides[get_data_service] = lambda: mock_service

    try:
        # Use patch.dict to safely modify os.environ for this block
        with patch.dict(os.environ, {"CRON_SECRET": "secure_secret_value"}):
            # Test with correct secret
            response = client.post(
                "/api/v1/pwa/backup/trigger",
                headers={"X-Cron-Secret": "secure_secret_value"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            assert response.json()["status"] == "success"

            # Test with incorrect secret
            response = client.post(
                "/api/v1/pwa/backup/trigger",
                headers={"X-Cron-Secret": "wrong_value"}
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid cron secret"

            # Test with missing secret header
            response = client.post(
                "/api/v1/pwa/backup/trigger",
                headers={}
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid cron secret"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides = {}
