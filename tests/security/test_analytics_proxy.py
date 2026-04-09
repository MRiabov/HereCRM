import pytest
from unittest.mock import patch, AsyncMock
from fastapi import Request
from src.api.v1.pwa.analytics_proxy import proxy_posthog
from src.config import settings

@pytest.mark.asyncio
async def test_proxy_posthog_path_traversal():
    """
    Test that path traversal attempts are blocked with 400 Bad Request.
    """
    scope = {
        "type": "http",
        "headers": [],
        "query_string": b"",
        "path": "/api/v1/pwa/analytics_proxy/../internal",
    }
    async def receive():
        return {"type": "http.request", "body": b""}

    request = Request(scope, receive)

    # Mock return object
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b"ok"
            self.headers = {}

    async def mock_request_fn(*args, **kwargs):
        return MockResponse()

    with patch("src.api.v1.pwa.analytics_proxy._client.request", new_callable=AsyncMock) as mock_request:
        # Ensure posthog_host is set to verify traversal logic, not config check
        with patch.object(settings, "posthog_host", "https://mock.host"):
            mock_request.side_effect = mock_request_fn

            path = "../internal"
            response = await proxy_posthog(request, path=path)

            # We expect security check to block this (return 400)
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
