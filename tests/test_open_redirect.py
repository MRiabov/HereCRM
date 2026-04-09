
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app

@pytest.mark.asyncio
async def test_open_redirect_fix():
    # We need to mock several things to reach the redirect logic

    with patch("src.api.routes.GoogleCalendarService") as MockServiceClass, \
         patch("src.repositories.UserRepository") as MockUserRepoClass, \
         patch("src.services.messaging_service.messaging_service.send_message", new_callable=AsyncMock), \
         patch("src.services.calendar_sync_handler.calendar_sync_handler.sync_all_user_jobs", new_callable=AsyncMock):

        mock_service = MockServiceClass.return_value
        mock_service.process_auth_callback = AsyncMock(return_value=True)

        mock_repo = MockUserRepoClass.return_value
        mock_user = AsyncMock()
        mock_user.id = 1
        mock_user.phone_number = "+1234567890"
        mock_user.preferred_channel = "WHATSAPP"
        mock_repo.get_by_id = AsyncMock(return_value=mock_user)

        async def mock_get_db():
            yield AsyncMock()

        app.dependency_overrides["get_db"] = mock_get_db

        client = TestClient(app)

        # Test 1: Malicious URL should be sanitized to "/"
        malicious_url = "http://evil.com"
        response = client.get(
            "/auth/google/callback",
            params={
                "code": "fake_code",
                "state": "1",
                "success_url": malicious_url
            },
            follow_redirects=False
        )
        assert response.status_code == 307
        assert response.headers["location"] == "/"

        # Test 2: Valid relative URL should be preserved
        valid_url = "/dashboard"
        response = client.get(
            "/auth/google/callback",
            params={
                "code": "fake_code",
                "state": "1",
                "success_url": valid_url
            },
            follow_redirects=False
        )
        assert response.status_code == 307
        assert response.headers["location"] == valid_url

        # Test 3: Localhost URL should be preserved (for dev)
        localhost_url = "http://localhost:3000/dashboard"
        response = client.get(
            "/auth/google/callback",
            params={
                "code": "fake_code",
                "state": "1",
                "success_url": localhost_url
            },
            follow_redirects=False
        )
        assert response.status_code == 307
        assert response.headers["location"] == localhost_url
