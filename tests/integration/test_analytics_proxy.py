import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.config import settings

client = TestClient(app)

@pytest.mark.asyncio
async def test_analytics_proxy_forwarding():
    """
    Test that the analytics proxy forwards calls to the configured PostHog host.
    """
    # Define a test path and query
    test_path = "decide"
    test_query = "v=3&ver=1.335.2"
    proxy_url = f"/api/v1/pwa/analytics/proxy/{test_path}?{test_query}"
    
    # Mock payload
    payload = {"token": "test_token", "distinct_id": "user_123"}
    
    # We need to patch httpx.AsyncClient.request to capture the outgoing request
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        # Configure the mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "ok"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_request.return_value = mock_response
        
        # Make the request to our proxy
        response = client.post(proxy_url, json=payload)
        
        # Verify our proxy returned the mock response
        assert response.status_code == 200
        assert response.content == b'{"status": "ok"}'
        
        # Verify the mock was called with the correct URL
        expected_target_url = f"{settings.posthog_host}/{test_path}?{test_query}"
        
        import json
        
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args.kwargs["method"] == "POST"
        assert call_args.kwargs["url"] == expected_target_url
        
        # Compare parsed JSON to avoid whitespace issues
        assert json.loads(call_args.kwargs["content"]) == payload

@pytest.mark.asyncio
async def test_analytics_proxy_error_handling():
    """
    Test that the proxy handles upstream errors gracefully (suppressing them).
    """
    with patch("httpx.AsyncClient.request", side_effect=Exception("Connection failed")):
        response = client.post("/api/v1/pwa/analytics/proxy/capture")
        
        # Should return 204 No Content to silence errors in the browser
        assert response.status_code == 204
