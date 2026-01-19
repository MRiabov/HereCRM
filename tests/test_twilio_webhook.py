"""
Integration tests for Twilio webhook endpoint (WP02)
"""
import pytest
import hmac
import hashlib
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from src.main import app


class TestTwilioWebhook:
    """Test suite for Twilio webhook endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def generate_twilio_signature(self, url: str, params: dict, auth_token: str) -> str:
        """Generate a valid Twilio signature for testing"""
        # Concatenate URL and sorted params
        data = url
        for key in sorted(params.keys()):
            data += f"{key}{params[key]}"
        
        # Create HMAC SHA256 signature
        signature = hmac.new(
            auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        # Return base64-encoded signature
        return base64.b64encode(signature).decode()
    
    @patch('src.api.routes.settings')
    @patch('src.services.twilio_service.TwilioService.send_sms')
    @patch('src.api.routes.AuthService')
    @patch('src.api.routes.WhatsappService')
    def test_twilio_webhook_success(
        self, 
        mock_whatsapp_service, 
        mock_auth_service,
        mock_send_sms,
        mock_settings,
        client
    ):
        """Test successful Twilio webhook processing"""
        # Setup mocks
        mock_settings.twilio_auth_token = "test_token"
        
        # Mock user creation
        mock_user = Mock()
        mock_user.phone_number = "+1234567890"
        mock_user.id = 1
        mock_user.business_id = 1
        
        mock_auth_instance = Mock()
        mock_auth_instance.get_or_create_user = AsyncMock(return_value=(mock_user, False))
        mock_auth_service.return_value = mock_auth_instance
        
        # Mock message handling
        mock_whatsapp_instance = Mock()
        mock_whatsapp_instance.handle_message = AsyncMock(return_value="Test response")
        mock_whatsapp_service.return_value = mock_whatsapp_instance
        
        # Mock SMS sending
        mock_send_sms.return_value = AsyncMock(return_value=True)
        
        # Prepare webhook data
        url = "http://testserver/webhooks/twilio"
        params = {
            "From": "+1234567890",
            "Body": "Hello, this is a test message"
        }
        
        signature = self.generate_twilio_signature(url, params, "test_token")
        
        # Make request
        with patch('src.api.routes.check_rate_limit', return_value=False):
            response = client.post(
                "/webhooks/twilio",
                data=params,
                headers={"X-Twilio-Signature": signature}
            )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    @patch('src.api.routes.settings')
    def test_twilio_webhook_missing_signature(self, mock_settings, client):
        """Test webhook rejects requests without signature"""
        mock_settings.twilio_auth_token = "test_token"
        
        params = {
            "From": "+1234567890",
            "Body": "Test message"
        }
        
        response = client.post("/webhooks/twilio", data=params)
        
        assert response.status_code == 401
        assert "Missing Twilio Signature" in response.json()["detail"]
    
    @patch('src.api.routes.settings')
    def test_twilio_webhook_invalid_signature(self, mock_settings, client):
        """Test webhook rejects requests with invalid signature"""
        mock_settings.twilio_auth_token = "test_token"
        
        params = {
            "From": "+1234567890",
            "Body": "Test message"
        }
        
        response = client.post(
            "/webhooks/twilio",
            data=params,
            headers={"X-Twilio-Signature": "invalid_signature"}
        )
        
        assert response.status_code == 403
        assert "Invalid Signature" in response.json()["detail"]
    
    @patch('src.api.routes.settings')
    def test_twilio_webhook_missing_fields(self, mock_settings, client):
        """Test webhook rejects requests with missing required fields"""
        mock_settings.twilio_auth_token = "test_token"
        
        url = "http://testserver/webhooks/twilio"
        params = {
            "From": "+1234567890"
            # Missing Body field
        }
        
        signature = self.generate_twilio_signature(url, params, "test_token")
        
        response = client.post(
            "/webhooks/twilio",
            data=params,
            headers={"X-Twilio-Signature": signature}
        )
        
        assert response.status_code == 400
        assert "Missing required fields" in response.json()["detail"]
    
    @patch('src.api.routes.settings')
    @patch('src.api.routes.check_rate_limit')
    def test_twilio_webhook_rate_limited(self, mock_rate_limit, mock_settings, client):
        """Test webhook handles rate limiting"""
        mock_settings.twilio_auth_token = "test_token"
        mock_rate_limit.return_value = True
        
        url = "http://testserver/webhooks/twilio"
        params = {
            "From": "+1234567890",
            "Body": "Test message"
        }
        
        signature = self.generate_twilio_signature(url, params, "test_token")
        
        response = client.post(
            "/webhooks/twilio",
            data=params,
            headers={"X-Twilio-Signature": signature}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "rate_limited"
