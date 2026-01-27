import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_google_login_error_handling():
    """
    Verify that google_login does not leak sensitive exception details.
    """
    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        # Mock get_auth_url to raise an exception with sensitive info
        mock_instance.get_auth_url.side_effect = ValueError("SENSITIVE_DB_PASSWORD_LEAK")

        response = client.get("/auth/google/login?user_id=123")

        # Verify failure logic
        assert response.status_code == 500
        # The generic message we expect after fix
        # For now, we assert what we WANT (secure behavior)
        assert "SENSITIVE_DB_PASSWORD_LEAK" not in response.text
        assert "Internal Error" in response.text or "Connection failed" in response.text

@pytest.mark.asyncio
async def test_google_callback_error_handling():
    """
    Verify that google_callback does not leak sensitive exception details.
    """
    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.process_auth_callback = AsyncMock(side_effect=ValueError("SENSITIVE_TOKEN_LEAK"))

        response = client.get("/auth/google/callback?code=abc&state=123")

        assert response.status_code == 500
        assert "SENSITIVE_TOKEN_LEAK" not in response.text
        assert "Connection failed" in response.text or "Internal Error" in response.text

@pytest.mark.asyncio
async def test_quickbooks_callback_error_handling():
    """
    Verify that quickbooks_callback does not leak sensitive exception details.
    """
    # Patch where it is imported. Since it is imported inside the function,
    # we need to mock sys.modules or patch the class where it is defined
    # and hope the local import picks it up, OR since we are using TestClient
    # which runs in the same process, patching 'src.services.accounting.quickbooks_auth.QuickBooksAuthService' works.
    with patch("src.services.accounting.quickbooks_auth.QuickBooksAuthService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.handle_callback = AsyncMock(side_effect=ValueError("SENSITIVE_QB_SECRET_LEAK"))

        response = client.get("/webhooks/quickbooks/callback?code=abc&state=xyz&realmId=123")

        assert response.status_code == 500
        assert "SENSITIVE_QB_SECRET_LEAK" not in response.text
        assert "Connection failed" in response.text or "Internal Error" in response.text
