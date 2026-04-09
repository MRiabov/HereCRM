import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.database import get_db

client = TestClient(app)

@pytest.fixture
def override_get_db():
    async def _get_db():
        yield AsyncMock()
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()

def test_open_redirect_mitigated(override_get_db):
    """
    Verify that the Google callback endpoint is protected against Open Redirect.
    When an exception occurs (e.g., invalid code), it should redirect to a safe URL (/)
    instead of the malicious success_url.
    """
    malicious_url = "http://evil.com"

    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        # Make process_auth_callback raise an exception
        mock_instance.process_auth_callback.side_effect = Exception("Auth failed")

        response = client.get(
            "/auth/google/callback",
            params={
                "code": "invalid_code",
                "state": "1",
                "success_url": malicious_url
            },
            follow_redirects=False
        )

        # Assert that we are NOT redirected to the malicious URL
        assert response.status_code in [302, 307]
        location = response.headers["location"]
        assert not location.startswith(malicious_url)

        # Assert fallback to safe URL (relative)
        assert location.startswith("/")
        assert "error=google_auth_failed" in location
