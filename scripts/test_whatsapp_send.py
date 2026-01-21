import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

async def send_test_message():
    # Use WHATSAPP_SYSTEM_USER_KEY if WHATSAPP_ACCESS_TOKEN is placeholder
    token = os.getenv("WHATSAPP_SYSTEM_USER_KEY")
    if not token or token.startswith("your_"):
        token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    recipient = "+353899485670"
    
    print(f"Using Token: {token[:10]}...")
    print(f"Using Phone Number ID: {phone_number_id}")
    
    if not phone_number_id or phone_number_id == "your_phone_number_id":
        print("Error: WHATSAPP_PHONE_NUMBER_ID is not configured in .env")
        return

    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {
            "body": "Hello from Antigravity! This is a test message for HereCRM."
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_message())
