
import asyncio
from src.database import AsyncSessionLocal
from src.services.whatsapp_service import WhatsappService
from src.services.auth_service import AuthService
from src.llm_client import parser
from src.services.template_service import TemplateService

async def test_fix():
    print("Testing persistence fix...")
    async with AsyncSessionLocal() as session:
        auth_service = AuthService(session)
        whatsapp_service = WhatsappService(session, parser, TemplateService())

        # 1. Simulate "New User" or "Hi" from a NEW number
        phone = "999888777" # Distinct valid-looking number
        print(f"Simulating message from {phone}...")
        
        # Ensure user exists or is created (logic from routes.py)
        user, is_new = await auth_service.get_or_create_user(phone)
        
        # Send "hi"
        response = await whatsapp_service.handle_message(
            user_phone=phone,
            message_text="hi",
            is_new_user=is_new
        )
        
        # Commit manually as routes.py does
        await session.commit()
        print(f"Service returned: {response[:50]}...")

    # 2. Verify it is in DB
    async with AsyncSessionLocal() as session:
        from src.models import Message
        from sqlalchemy import select
        
        stmt = select(Message).where(Message.to_number == phone)
        # Just select by phone
        stmt = select(Message).where(Message.to_number == phone)
        result = await session.execute(stmt)
        msgs = result.scalars().all()
        
        print(f"Found {len(msgs)} assistant messages for {phone}.")
        if len(msgs) > 0:
            print("SUCCESS: Reply was persisted!")
            for m in msgs:
                print(f"- {m.body[:50]}...")
        else:
            print("FAILURE: No reply found in DB.")

if __name__ == "__main__":
    asyncio.run(test_fix())
