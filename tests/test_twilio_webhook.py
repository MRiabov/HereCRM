"""
Integration tests for Twilio webhook endpoint (WP02)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import app
from src.api.routes import get_services, verify_twilio_signature
from fastapi import Response

class TestTwilioWebhook:
    """Test suite for Twilio webhook endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        # Clear overrides before each test
        app.dependency_overrides = {}
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_twilio_webhook_success(self, client):
        """Test successful Twilio webhook processing"""
        # Mock Services
        mock_auth_service = AsyncMock()
        mock_whatsapp_service = AsyncMock()
        
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.phone_number = "+1234567890"
        mock_auth_service.get_or_create_user.return_value = (mock_user, False)
        
        # Override Dependencies
        async def override_get_services():
            return mock_auth_service, mock_whatsapp_service
            
        async def override_verify_signature():
            return # skip validation
            
        app.dependency_overrides[get_services] = override_get_services
        app.dependency_overrides[verify_twilio_signature] = override_verify_signature
        
        params = {
            "From": "+1234567890",
            "Body": "Hello world"
        }
        
        response = client.post("/webhooks/twilio", data=params)
        
        # Assertions
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "<Response></Response>" in response.text
        
        # Verify interactions
        mock_auth_service.get_or_create_user.assert_called_with("+1234567890")
        mock_whatsapp_service.handle_message.assert_called_once()
        call_args = mock_whatsapp_service.handle_message.call_args
        assert call_args.kwargs['user_phone'] == "+1234567890"
        assert call_args.kwargs['channel'] == "sms"

    async def test_twilio_webhook_missing_signature(self, client):
        """Test webhook rejects requests without signature (triggering real dependency)"""
        # Note: We DON'T override verify_twilio_signature here to test the real one
        with patch('src.api.routes.settings') as mock_settings:
            mock_settings.twilio_auth_token = "test_token"
            
            params = {"From": "+1234567890", "Body": "Test"}
            response = client.post("/webhooks/twilio", data=params)
            
            # Should fail with 403 (Missing Twilio Signature)
            assert response.status_code == 403
            assert "Missing Twilio Signature" in response.json()["detail"]

    @patch('src.api.routes.RequestValidator')
    async def test_twilio_webhook_invalid_signature(self, mock_validator_class, client):
        """Test webhook rejects requests with invalid signature"""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = False
        mock_validator_class.return_value = mock_validator
        
        with patch('src.api.routes.settings') as mock_settings:
            mock_settings.twilio_auth_token = "test_token"
            
            params = {"From": "+1234567890", "Body": "Test"}
            response = client.post(
                "/webhooks/twilio", 
                data=params,
                headers={"X-Twilio-Signature": "wrong"}
            )
            
            assert response.status_code == 403
            assert "Invalid Twilio Signature" in response.json()["detail"]

    @patch('src.api.routes.check_rate_limit')
    async def test_twilio_webhook_rate_limited(self, mock_rate_limit, client):
        """Test webhook handles rate limiting"""
        mock_rate_limit.return_value = True
        
        async def override_verify_signature(): return
        app.dependency_overrides[verify_twilio_signature] = override_verify_signature

        params = {"From": "+1234567890", "Body": "Test"}
        response = client.post("/webhooks/twilio", data=params)
        
        assert response.status_code == 200
        assert "<Response></Response>" in response.text
        # Ensure it didn't call services
        # (We could check if get_services was called, but if we don't override it and it's not reached, that's fine)
