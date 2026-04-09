import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_google_callback_open_redirect_fix():
    """
    Verifies the fix for Open Redirect in /auth/google/callback.
    We expect the endpoint to sanitze the URL and redirect to '/' instead of 'http://evil.com'.
    """
    success_url = "http://evil.com"

    with patch("src.api.routes.GoogleCalendarService") as MockService:
        instance = MockService.return_value
        instance.process_auth_callback = AsyncMock(side_effect=Exception("Simulated Auth Failure"))

        # 1. Standard Case
        response = client.get(
            f"/auth/google/callback?code=invalid&state=123&success_url={success_url}",
            follow_redirects=False
        )

        assert response.status_code == 307
        location = response.headers["location"]
        print(f"Redirect Location: {location}")

        # It should NOT go to evil.com
        assert "http://evil.com" not in location

        # It SHOULD go to root with error param
        assert location.startswith("/?error=google_auth_failed") or location.startswith("/?error=")

        # 2. Bypass Cases
        bypass_cases = ["javascript:alert(1)", "http:evil.com", "//evil.com", "data:text/html,bad"]
        for bad_url in bypass_cases:
             response = client.get(
                f"/auth/google/callback?code=invalid&state=123&success_url={bad_url}",
                follow_redirects=False
             )
             loc = response.headers.get("location", "")
             # We expect it to be sanitized to "/"
             assert bad_url not in loc, f"Security Bypass! URL '{bad_url}' was allowed redirect to '{loc}'"
             assert loc.startswith("/?error="), f"Expected sanitized redirect for '{bad_url}', got '{loc}'"
