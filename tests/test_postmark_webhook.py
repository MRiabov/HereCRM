"""
Integration tests for Postmark webhook endpoint (WP03)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app


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
