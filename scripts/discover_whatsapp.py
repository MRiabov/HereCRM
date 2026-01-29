import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


async def discover():
    token = os.getenv("WHATSAPP_SYSTEM_USER_KEY")
    if not token or token.startswith("your_"):
        token = os.getenv("WHATSAPP_ACCESS_TOKEN")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        print("--- Accounts ---")
        resp = await client.get(
            "https://graph.facebook.com/v18.0/me/accounts", headers=headers
        )
        print(resp.text)

        print("\n--- Assigned Users? ---")
        # For System Users, sometimes we need to check the business it belongs to.
        # Let's try to get more fields about 'me'
        resp = await client.get(
            "https://graph.facebook.com/v18.0/me?fields=id,name,business",
            headers=headers,
        )
        print(resp.text)


if __name__ == "__main__":
    asyncio.run(discover())
