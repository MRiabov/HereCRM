
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, Job, Quote, QuoteStatus
from src.services.quote_service import QuoteService
from src.services.crm_service import CRMService
from src.events import event_bus, QUOTE_SENT, JOB_PAID
from src.services.scheduler import scheduler_service
# Import handlers to ensure subscription
import src.handlers.automation_handlers

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as s:
        yield s
    await engine.dispose()

@pytest.mark.asyncio
async def test_automation_triggers(session):
    # Manually register handlers because conftest resets event_bus
    from src.handlers.automation_handlers import AutomationEventHandler
    event_bus.subscribe(QUOTE_SENT, AutomationEventHandler.handle_quote_sent)
    event_bus.subscribe(JOB_PAID, AutomationEventHandler.handle_job_paid)

    # Mock Scheduler
    with patch.object(scheduler_service, 'add_delayed_job') as mock_add_delayed:

        # Setup Data
        business = Business(name="Test Biz", id=1)
        customer = Customer(name="John Doe", business_id=1, id=100)
        session.add(business)
        session.add(customer)
        await session.commit()

        # 1. Test Quote Sent Automation
        quote_service = QuoteService(session)
        quote = await quote_service.create_quote(customer.id, business.id, [{"description": "Test", "unit_price": 100, "quantity": 1}])

        # Subscribe to QUOTE_SENT to verify emit (spy)
        quote_sent_handler = AsyncMock()
        event_bus.subscribe(QUOTE_SENT, quote_sent_handler)

        # Action: Send Quote
        await quote_service.send_quote(quote.id)

        # Verification 1: Event Emitted
        if not quote_sent_handler.called:
            print("FAIL: QUOTE_SENT event was not emitted")
        else:
            print("PASS: QUOTE_SENT event emitted")

        # Verification 2: Scheduler called (by the handler in src/handlers/automation_handlers.py)
        # We need to wait a bit because event bus is async gather
        await asyncio.sleep(0.1)

        # Verify add_delayed_job was called
        # The handler calls it with check_quote_followup, delay=48h, etc.
        if mock_add_delayed.call_count == 0:
             print("FAIL: Scheduler add_delayed_job was not called for QUOTE_SENT")
        else:
             # Check arguments
             call_args = mock_add_delayed.call_args_list[0]
             # check_quote_followup is the first arg
             func_name = call_args[0][0].__name__
             if func_name == "check_quote_followup":
                 print("PASS: Scheduler called for check_quote_followup")
             else:
                 print(f"FAIL: Scheduler called with wrong function: {func_name}")

        mock_add_delayed.reset_mock()

        # 2. Test Job Paid Automation
        crm_service = CRMService(session, business.id)
        job = await crm_service.create_job(customer.id, description="Test Job", value=500)

        # Subscribe to JOB_PAID
        job_paid_handler = AsyncMock()
        event_bus.subscribe(JOB_PAID, job_paid_handler)

        # Action: Mark Job as Paid using new method
        if not hasattr(crm_service, 'mark_job_paid'):
            print("FAIL: CRMService.mark_job_paid method does not exist")
        else:
            await crm_service.mark_job_paid(job.id)

            # Verification 1: Event Emitted
            if not job_paid_handler.called:
                print("FAIL: JOB_PAID event was not emitted")
            else:
                print("PASS: JOB_PAID event emitted")

            # Verification 2: Scheduler called
            await asyncio.sleep(0.1)

            if mock_add_delayed.call_count == 0:
                print("FAIL: Scheduler add_delayed_job was not called for JOB_PAID")
            else:
                 call_args = mock_add_delayed.call_args_list[0]
                 func_name = call_args[0][0].__name__
                 if func_name == "send_review_request":
                     print("PASS: Scheduler called for send_review_request")
                 else:
                     print(f"FAIL: Scheduler called with wrong function: {func_name}")

if __name__ == "__main__":
    asyncio.run(test_automation_triggers(None))
