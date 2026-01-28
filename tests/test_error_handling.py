import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from src.main import app

client = TestClient(app)

# Helper to bypass auth for other tests if needed, but here we explicitly want to test auth failure
def bypass_auth():
    return MagicMock()

@pytest.mark.asyncio
async def test_clerk_auth_error_leak():
    """
    Verify that an exception during token validation leaks sensitive info in the 401 response.
    """
    with patch("src.api.dependencies.clerk_auth.jwt.decode", side_effect=Exception("SENSITIVE_INTERNAL_INFO_LEAK")):
        # We need a valid-looking header to trigger the decode logic
        headers = {"Authorization": "Bearer some.fake.token"}

        # We need an endpoint that uses verify_token.
        # src/api/v1/pwa/user.py /user/integrations uses it.
        response = client.get("/api/v1/pwa/user/integrations", headers=headers)

        # EXPECTED BEHAVIOR (SECURE): status 401 and detail IS GENERIC
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "SENSITIVE_INTERNAL_INFO_LEAK" not in response.json()["detail"]
        assert response.json()["detail"] == "Token validation failed"


@pytest.mark.asyncio
async def test_google_callback_error_leak():
    """
    Verify that an exception during Google callback leaks sensitive info in the 500 response.
    """
    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.process_auth_callback.side_effect = Exception("DB_CONNECTION_STRING_LEAK")

        response = client.get("/auth/google/callback?code=123&state=456")

        # EXPECTED BEHAVIOR (SECURE): status 500 and detail IS GENERIC
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "DB_CONNECTION_STRING_LEAK" not in response.json()["detail"]
        assert response.json()["detail"] == "Connection failed"
