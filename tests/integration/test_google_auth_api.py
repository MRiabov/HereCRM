import pytest
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch, AsyncMock


@pytest.fixture
def client():
    return TestClient(app)


def test_google_login_redirect(client):
    with patch("src.api.routes.GoogleCalendarService") as mock_service_class:
        mock_service = mock_service_class.return_value
        # Ensure is_configured is True for the instance
        mock_service.is_configured = True
        mock_service.get_auth_url.return_value = ("https://google.com/auth", "state")

        response = client.get("/auth/google/login?user_id=123", follow_redirects=False)

        assert response.status_code in [302, 303, 307]
        assert response.headers["location"] == "https://google.com/auth"


def test_google_callback_success(client):
    with (
        patch("src.api.routes.GoogleCalendarService") as mock_service_class,
        patch(
            "src.services.messaging_service.MessagingService.send_message",
            new_callable=AsyncMock,
        ),
        patch(
            "src.services.calendar_sync_handler.calendar_sync_handler.sync_all_user_jobs",
            new_callable=AsyncMock,
        ),
    ):
        mock_service = mock_service_class.return_value
        mock_service.process_auth_callback = AsyncMock(return_value=True)

        response = client.get("/auth/google/callback?code=testcode&state=123")

        assert response.status_code == 200
        assert "Connected!" in response.text
        assert "Google Calendar has been successfully linked" in response.text
