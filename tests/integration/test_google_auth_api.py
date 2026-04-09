import pytest
import json
import time
import jwt
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch, AsyncMock
from src.config import settings


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

        # Verify call args
        args, kwargs = mock_service.get_auth_url.call_args
        state = kwargs.get("state")
        assert state is not None

        # Verify JWT in state
        payload = jwt.decode(state, settings.secret_key, algorithms=["HS256"])
        assert payload["user_id"] == 123
        assert "exp" in payload
        assert payload["exp"] > time.time()


def test_google_callback_success(client):
    # Generate valid JWT state with expiration
    payload = {"user_id": 123, "exp": int(time.time()) + 600}
    signed_state = jwt.encode(payload, settings.secret_key, algorithm="HS256")

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

        response = client.get(f"/auth/google/callback?code=testcode&state={signed_state}")

        assert response.status_code == 200
        assert "Connected!" in response.text
        assert "Google Calendar has been successfully linked" in response.text


def test_google_callback_invalid_signature(client):
    # Generate state with invalid secret
    payload = {"user_id": 123, "exp": int(time.time()) + 600}
    signed_state = jwt.encode(payload, "wrong_secret", algorithm="HS256")

    with patch("src.api.routes.GoogleCalendarService") as mock_service_class:
        response = client.get(f"/auth/google/callback?code=testcode&state={signed_state}")

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid state token"


def test_google_callback_expired_state(client):
    # Generate state with expired timestamp
    payload = {"user_id": 123, "exp": int(time.time()) - 600}
    signed_state = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    with patch("src.api.routes.GoogleCalendarService") as mock_service_class:
        response = client.get(f"/auth/google/callback?code=testcode&state={signed_state}")

        assert response.status_code == 400
        assert response.json()["detail"] == "State expired"


def test_google_callback_unsigned_state(client):
    # State without signature (legacy/attack attempt)
    state = "123"

    with patch("src.api.routes.GoogleCalendarService") as mock_service_class:
        response = client.get(f"/auth/google/callback?code=testcode&state={state}")

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid state token"


def test_google_callback_malformed_token(client):
    # State with random junk
    state = "invalid.junk.token"

    with patch("src.api.routes.GoogleCalendarService") as mock_service_class:
        response = client.get(f"/auth/google/callback?code=testcode&state={state}")

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid state token"
