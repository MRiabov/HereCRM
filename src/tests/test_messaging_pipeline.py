import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Customer, PipelineStage, Business, MessageType, MessageTriggerSource
from src.services.messaging_service import MessagingService
from src.events import event_bus, CONTACT_EVENT
from src.services.pipeline_handlers import handle_contact_event

@pytest.fixture(autouse=True)
def setup_event_subscriptions():
    event_bus._subscribers = {}
    event_bus.subscribe(CONTACT_EVENT, handle_contact_event)
    yield
    event_bus._subscribers = {}

@pytest.mark.asyncio
async def test_send_message_triggers_pipeline_update(session: AsyncSession):
    business_id = 1
    # Create Business first to satisfy FK
    business = Business(id=business_id, name="Test Biz")
    session.add(business)
    await session.flush()

    customer = Customer(
        name="Test Contact",
        phone="+15551234567",
        business_id=business_id,
        pipeline_stage=PipelineStage.NOT_CONTACTED
    )
    session.add(customer)
    await session.commit()

    assert customer.pipeline_stage == PipelineStage.NOT_CONTACTED

    # Initialize Service
    # We pass the session object's factory-like callable or just rely on session reuse if possible?
    # MessagingService uses session_factory().
    # In tests, `session` fixture is an AsyncSession instance.
    # We need to mock session_factory to return a context manager that yields this session.

    # However, MessagingService creates NEW sessions using session_factory.
    # If we want it to reuse the test session (rolled back at end), we need to be careful.
    # But for this integration test, maybe we can mock _get_session_maker to return a factory that returns our session?

    # Or cleaner: Since MessagingService creates its own session, we should let it do so,
    # but the test `session` fixture usually runs in a transaction that is rolled back.
    # If MessagingService creates a new connection, it won't see uncommitted data from test setup
    # unless we commit it (which we did `await session.commit()`).
    # But usually tests use a shared transaction or truncated tables.

    # Let's try to pass a factory that yields the current session.
    class MockSessionFactory:
        def __call__(self):
            return self
        async def __aenter__(self):
            return session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    ms = MessagingService(session_factory=MockSessionFactory())

    # Mock sending methods
    ms._send_whatsapp = MagicMock(return_value=(True, "msg_id"))
    ms._send_whatsapp.side_effect = None

    # We need to await the result if the original method was async?
    # _send_whatsapp is async.
    async def mock_send(*args, **kwargs):
        return True, "msg_id"

    with patch.object(ms, '_send_whatsapp', side_effect=mock_send):
        await ms.send_message(
            recipient_phone=customer.phone,
            content="Hello",
            channel=MessageType.WHATSAPP,
            business_id=business_id,
            trigger_source=MessageTriggerSource.MANUAL
        )

    # MessagingService emits event. EventBus runs handler. Handler updates customer.
    # Handler uses src.database.get_session_maker().
    # We need to patch that too if we want it to use our session, otherwise it opens a new one.
    # Since we are using sqlite memory in some environments or local pg, we want it to see the change.

    # But wait, `handle_contact_event` imports `src.database`.
    # We can patch `src.services.pipeline_handlers.src.database.get_session_maker`.

    # However, in `test_pipeline_logic.py`, `handle_contact_event` works.
    # Why? `test_pipeline_logic.py` emits event manually.
    # `handle_contact_event` is called. It opens session.
    # If the test environment is configured correctly, it works.

    # Let's just try running it. The main issue is usually transaction isolation.
    # If `handle_contact_event` opens a new session, and we are using `pytest-asyncio` with `session` fixture,
    # usually `session` is in a transaction.
    # If `handle_contact_event` uses a separate connection, it might block or not see uncommitted data.
    # But we did `await session.commit()` above. So data is committed.
    # So `handle_contact_event` should see it.

    # Refresh customer
    await session.refresh(customer)
    assert customer.pipeline_stage == PipelineStage.CONTACTED
