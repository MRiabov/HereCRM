import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_google_login_verbose_error(client):
    # Patch the GoogleCalendarService used in src.api.routes

    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        # Raise an exception with internal details
        mock_instance.get_auth_url.side_effect = Exception("Internal DB Error: Table 'users' not found")

        response = client.get("/auth/google/login?user_id=1")

        assert response.status_code == 500
        # Check that the internal error message is NOT leaked
        assert "Internal DB Error: Table 'users' not found" not in response.text
        # Check that we get a generic error message
        assert "Internal Server Error" in response.text
