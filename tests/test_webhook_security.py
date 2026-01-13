import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db
from unittest.mock import AsyncMock, patch
import hmac
import hashlib
import json
import os

# Dummy secret for tests
SECRET = "dummy_secret"


def sign_payload(payload: dict, secret: str) -> str:
    body_bytes = json.dumps(payload).encode("utf-8")
    secret_bytes = secret.encode("utf-8")
    signature = hmac.new(secret_bytes, body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


@pytest.mark.asyncio
async def test_webhook_internal_error_returns_500():
    """
    Test that an unexpected exception results in a 500 status code.
    This specifically tests the fix for 'return HTTPException' vs 'raise HTTPException'.
    """

    # Mocking AuthService.get_or_create_user to raise an exception
    with patch(
        "src.api.routes.AuthService.get_or_create_user",
        side_effect=Exception("Database crash!"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            phone = "111222333"
            payload = {"from_number": phone, "body": "test error"}

            # Use manual serialization for byte-perfect match
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(
                SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
            ).hexdigest()
            sig_header = f"sha256={signature}"

            response = await ac.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": sig_header,
                    "Content-Type": "application/json",
                },
            )

            # Assert that the status code is 500, not 200
            assert response.status_code == 500
            assert response.json() == {"detail": "Internal Server Error"}
