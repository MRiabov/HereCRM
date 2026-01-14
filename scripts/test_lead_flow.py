import hmac
import hashlib
import json
import httpx
import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import settings


async def test_webhook():
    SECRET = settings.whatsapp_app_secret
    BASE_URL = "http://localhost:8000"

    payload = {
        "from_number": "1234567890",
        "body": "add lead: John Doe, 123 High Street",
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    signature = hmac.new(
        SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Hub-Signature-256": f"sha256={signature}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        print(f"Sending 'add lead: John Doe, 123 High Street' to {BASE_URL}/webhook...")
        resp = await client.post(
            f"{BASE_URL}/webhook", content=payload_bytes, headers=headers
        )
        print(f"Response: {resp.status_code}")
        print(f"Body: {resp.text}")

        if resp.status_code == 200:
            print("\nConfirming with 'Yes'...")
            payload = {"from_number": "1234567890", "body": "Yes"}
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(
                SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-Hub-Signature-256"] = f"sha256={signature}"
            resp = await client.post(
                f"{BASE_URL}/webhook", content=payload_bytes, headers=headers
            )
            print(f"Response: {resp.status_code}")
            print(f"Body: {resp.text}")

        print("\nTesting 'edit last'...")
        payload = {"from_number": "1234567890", "body": "edit last"}
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={signature}"
        resp = await client.post(
            f"{BASE_URL}/webhook", content=payload_bytes, headers=headers
        )
        print(f"Response: {resp.status_code}")
        print(f"Body: {resp.text}")


if __name__ == "__main__":
    asyncio.run(test_webhook())
