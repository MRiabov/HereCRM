import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.models import User
from src.api.dependencies.clerk_auth import verify_token, get_current_user

client = TestClient(app)

# Helper to mock current user
async def mock_get_current_user():
    return User(id=1, email="test@example.com", business_id=1)

async def mock_verify_token_func(request, db):
    return User(id=1, email="test@example.com", business_id=1)

def test_google_login_verbose_error():
    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_auth_url.side_effect = Exception("DATABASE_URL=postgres://user:pass@localhost Connection failed")

        response = client.get("/auth/google/login?user_id=1")

        assert response.status_code == 500
        # AFTER FIX: Should NOT contain sensitive info
        assert "DATABASE_URL=postgres://user:pass@localhost" not in response.json()["detail"]
        assert "Login failed. Please contact support." == response.json()["detail"]

def test_quickbooks_callback_verbose_error():
    with patch("src.services.accounting.quickbooks_auth.QuickBooksAuthService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.handle_callback.side_effect = Exception("API_KEY=12345 leaked")

        response = client.get("/webhooks/quickbooks/callback?code=123&state=456&realmId=789")

        assert response.status_code == 500
        assert "API_KEY=12345 leaked" not in response.json()["detail"]
        assert "Connection failed. Please contact support." == response.json()["detail"]

def test_google_callback_verbose_error():
    with patch("src.api.routes.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.process_auth_callback.side_effect = Exception("GOOGLE_SECRET=secret leaked")

        response = client.get("/auth/google/callback?code=123&state=456")

        assert response.status_code == 500
        assert "GOOGLE_SECRET=secret leaked" not in response.json()["detail"]
        assert "Connection failed. Please contact support." == response.json()["detail"]
