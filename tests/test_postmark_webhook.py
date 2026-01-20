"""
Integration tests for Postmark webhook endpoint (WP03)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import app
from src.api.routes import get_services

class TestPostmarkWebhook:
    """Test suite for Postmark inbound webhook endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_postmark_webhook_missing_from(self, client):
        """Test webhook rejects requests without From field"""
        payload = {
            "Subject": "Test",
            "TextBody": "Test body"
        }
        
        response = client.post("/webhooks/postmark/inbound", json=payload)
        
        assert response.status_code == 400
        assert "Missing required fields" in response.json()["detail"]
    
    def test_postmark_webhook_missing_body(self, client):
        """Test webhook rejects requests without TextBody field"""
        payload = {
            "From": "test@example.com",
            "Subject": "Test"
        }
        
        response = client.post("/webhooks/postmark/inbound", json=payload)
        
        assert response.status_code == 400
        assert "Missing required fields" in response.json()["detail"]
    
    @patch('src.api.routes.check_rate_limit')
    def test_postmark_webhook_rate_limited(self, mock_rate_limit, client):
        """Test webhook handles rate limiting"""
        mock_rate_limit.return_value = True
        
        payload = {
            "From": "test@example.com",
            "Subject": "Test",
            "TextBody": "Test message"
        }
        
        response = client.post("/webhooks/postmark/inbound", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "rate_limited"

    @patch('src.services.postmark_service.PostmarkService.send_email', new_callable=AsyncMock)
    @patch('src.api.routes.check_rate_limit')
    def test_postmark_webhook_success(self, mock_rate_limit, mock_send_email, client):
        """Test happy path for Postmark webhook using dependency overrides"""
        mock_rate_limit.return_value = False
        
        # Mock Services
        mock_auth_service = AsyncMock()
        mock_whatsapp_service = AsyncMock()
        
        # Setup Auth User return
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.email = "user@example.com"
        mock_user.phone_number = "user@example.com" # Identity
        mock_auth_service.get_or_create_user_by_identity.return_value = (mock_user, False)
        
        # Setup Whatsapp Service return
        mock_whatsapp_service.handle_message.return_value = "Hello from Assistant"

        # Mock DB Session
        mock_auth_service.session.commit = AsyncMock()
        
        # Mock Session Verify (execute query)
        mock_result = MagicMock()
        mock_message = MagicMock()
        mock_message.log_metadata = {}
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_auth_service.session.execute.return_value = mock_result
        
        # Override Dependency
        async def override_get_services():
            return mock_auth_service, mock_whatsapp_service
            
        app.dependency_overrides[get_services] = override_get_services
        
        try:
            payload = {
                "From": "user@example.com",
                "Subject": "Hello",
                "TextBody": "Hi there",
                "MessageID": "msg-123",
                "Headers": [
                    {"Name": "In-Reply-To", "Value": "msg-old-1"}
                ]
            }
            
            # Since we mock services, we don't need real DB connection
            # But get_db might still be called by verify_signature or others? 
            # verify_signature doesn't use DB.
            # postmark_inbound_webhook uses get_db as default dependency for get_services,
            # but we overrode get_services.
            # BUT postmark_inbound_webhook ALSO asks for `db: AsyncSession = Depends(get_db)` directly!
            # We need to override get_db as well to avoid DB connection attempt.
            
            from src.database import get_db
            async def override_get_db():
                yield AsyncMock() # Fake session
            
            app.dependency_overrides[get_db] = override_get_db

            response = client.post("/webhooks/postmark/inbound", json=payload)
            
            # Verify response
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "success"
            
            # Verify interactions
            mock_auth_service.get_or_create_user_by_identity.assert_called_with("user@example.com")
            
            mock_whatsapp_service.handle_message.assert_called_once()
            call_args = mock_whatsapp_service.handle_message.call_args
            assert call_args.kwargs['user_phone'] == "user@example.com"
            assert call_args.kwargs['message_text'] == "Hi there"
            assert call_args.kwargs['channel'] == "email"

            mock_send_email.assert_called_once()
            email_args = mock_send_email.call_args
            assert email_args.kwargs['to_email'] == "user@example.com"
            assert email_args.kwargs['subject'] == "Re: Hello"
            assert email_args.kwargs['body'] == "Hello from Assistant"
            assert email_args.kwargs['in_reply_to'] == "msg-123"

        finally:
            app.dependency_overrides = {}
