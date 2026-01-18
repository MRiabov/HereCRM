import asyncio
import pandas as pd
import os
import io
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, ConversationState, ConversationStatus
from src.services.whatsapp_service import WhatsappService
from src.services.template_service import TemplateService
from src.llm_client import LLMParser
from unittest.mock import AsyncMock, MagicMock

# Configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///scripts/manual_test.db"

async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, SessionLocal

async def run_simulation():
    if os.path.exists("scripts/manual_test.db"):
        os.remove("scripts/manual_test.db")
    
    engine, SessionLocal = await setup_db()
    
    async with SessionLocal() as session:
        # 1. Create Business and User
        biz = Business(name="Verify Biz")
        session.add(biz)
        await session.flush()
        
        user = User(phone_number="123456789", business_id=biz.id)
        state = ConversationState(phone_number="123456789", state=ConversationStatus.IDLE)
        session.add_all([user, state])
        await session.commit()
        
        # 2. Setup WhatsappService
        # We need a real TemplateService but maybe mock parser to avoid LLM calls if needed, 
        # or use real one if OpenAI key is there.
        template_service = TemplateService()
        parser = LLMParser() # Real parser for NL tests
        
        service = WhatsappService(session, parser, template_service)
        
        print("\n--- Scenario 1: Transition to Data Management ---")
        response = await service._handle_idle(user, state, "manage data")
        print(f"Response: {response}")
        print(f"New state: {state.state}")
        
        print("\n--- Scenario 2: Smart CSV Import ---")
        csv_content = "Client Name,Client Phone,Address\nBob Builder,987654321,Under the Sea"
        csv_path = "scripts/test_import_manual.csv"
        with open(csv_path, "w") as f:
            f.write(csv_content)
        
        # In the real flow, media_url would be a URL. Here we pass the local path.
        # Ensure media_type is correct
        response = await service._handle_data_management(
            user, state, "", media_url=csv_path, media_type="text/csv"
        )
        print(f"Response: {response}")
        
        # Verify DB
        from sqlalchemy import select
        from src.models import Customer
        result = await session.execute(select(Customer).where(Customer.name == "Bob Builder"))
        customer = result.scalars().first()
        if customer:
            print(f"Import SUCCESS: Found customer {customer.name} with phone {customer.phone}")
        else:
            print("Import FAILED: Customer not found")
        
        print("\n--- Scenario 3: Natural Language Export ---")
        # This will call the LLM if using real parser. We might need to mock if no API key.
        if os.getenv("OPENAI_API_KEY"):
            response = await service._handle_data_management(user, state, "Export all customers in Dublin as JSON")
            print(f"Response: {response}")
        else:
            print("Skipping NL Export (No API Key)")

        print("\n--- Scenario 4: Exit Data Management ---")
        response = await service._handle_data_management(user, state, "exit")
        print(f"Response: {response}")
        print(f"Final state: {state.state}")

    await engine.dispose()
    if os.path.exists("scripts/test_import_manual.csv"):
        os.remove("scripts/test_import_manual.csv")
    if os.path.exists("scripts/manual_test.db"):
        os.remove("scripts/manual_test.db")

if __name__ == "__main__":
    asyncio.run(run_simulation())
