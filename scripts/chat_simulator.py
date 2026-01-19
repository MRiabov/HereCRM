import asyncio
import hashlib
import hmac
import json
import os
import sys

import httpx
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add src to path if needed (though we'll use HTTP to talk to the server)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try to load settings to get the secret, otherwise use a placeholder
try:
    from src.config import settings

    SECRET = settings.whatsapp_app_secret
except Exception:
    SECRET = os.getenv("WHATSAPP_APP_SECRET", "dummy_secret")

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_PHONE = "1234567890"


async def send_message(phone: str, body: str, client: httpx.AsyncClient):
    payload = {"from_number": phone, "body": body}
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Calculate signature
    signature = hmac.new(
        SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Hub-Signature-256": f"sha256={signature}",
        "Content-Type": "application/json",
    }

    try:
        response = await client.post(
            f"{BASE_URL}/webhook", content=payload_bytes, headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("reply", "No response.")
        else:
            return f"Error {response.status_code}: {response.text}"
    except httpx.ReadTimeout:
        return "Request failed: Timeout (Server took too long to respond)"
    except Exception as e:
        return f"Request failed: {type(e).__name__}: {e}"


async def main():
    print("=== HereCRM - Text-based CRM CLI ===")
    print(f"Targeting: {BASE_URL}")
    print(f"Auth: {'Enabled' if SECRET else 'Disabled'}")
    print("Type 'exit' to quit, 'switch' to change phone number.\n")

    current_phone = DEFAULT_PHONE

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                user_input = input(f"[{current_phone}] > ").strip()
            except EOFError:
                break

            if user_input.lower() == "exit":
                break

            if user_input.lower() == "switch":
                new_phone = input("Enter new phone number: ").strip()
                if new_phone:
                    current_phone = "".join(c for c in new_phone if c.isdigit() or c == "+")
                continue

            if not user_input:
                continue

            reply = await send_message(current_phone, user_input, client)
            print(f"Reply: {reply}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")

