import pytest
import asyncio

from src.services.event_bus import event_bus
from src.services.messaging_service import MessagingService
from src.events import JobBookedEvent, JobScheduledEvent, OnMyWayEvent
from src.models import MessageLog, MessageStatus


@pytest.mark.asyncio
async def test_event_bus_integration_job_booked():
    """
    Integration test: Emit JobBookedEvent and verify MessagingService picks it up.
    """
    # Create a new MessagingService instance for this test
    service = MessagingService()
    
    # Register handlers
    service.register_handlers()
    
    # Start the service
    await service.start()
    
    # Emit a JobBookedEvent
    event = JobBookedEvent(
        job_id=123,
        customer_id=456,
        business_id=789,
        description="Test integration job",
    )
    
    await event_bus.emit(event)
    
    # Wait for async processing
    await asyncio.sleep(0.5)
    
    # Verify message was enqueued and processed
    # The queue should be empty after processing
    assert service._queue.qsize() == 0
    
    # Stop the service
    await service.stop()
    
    # Query database to verify MessageLog was created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        result = await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(MessageLog).where(
                MessageLog.trigger_source == "job_booked"
            )
        )
        message_logs = result.scalars().all()
        
        # Should have at least one message log
        assert len(message_logs) > 0
        
        # Verify the message content
        latest_log = message_logs[-1]
        assert "123" in latest_log.content or "job" in latest_log.content.lower()
        assert latest_log.status == MessageStatus.SENT
        break


@pytest.mark.asyncio
async def test_event_bus_integration_job_scheduled():
    """
    Integration test: Emit JobScheduledEvent and verify MessagingService picks it up.
    """
    from datetime import datetime, timezone
    
    service = MessagingService()
    service.register_handlers()
    await service.start()
    
    # Emit a JobScheduledEvent
    event = JobScheduledEvent(
        job_id=123,
        customer_id=456,
        business_id=789,
        scheduled_at=datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc),
    )
    
    await event_bus.emit(event)
    
    # Wait for async processing
    await asyncio.sleep(0.5)
    
    # Verify queue is empty (message was processed)
    assert service._queue.qsize() == 0
    
    await service.stop()
    
    # Query database to verify MessageLog was created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        result = await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(MessageLog).where(
                MessageLog.trigger_source == "job_scheduled"
            )
        )
        message_logs = result.scalars().all()
        
        assert len(message_logs) > 0
        latest_log = message_logs[-1]
        assert "scheduled" in latest_log.content.lower()
        assert latest_log.status == MessageStatus.SENT
        break


@pytest.mark.asyncio
async def test_event_bus_integration_on_my_way():
    """
    Integration test: Emit OnMyWayEvent and verify MessagingService picks it up.
    """
    service = MessagingService()
    service.register_handlers()
    await service.start()
    
    # Emit an OnMyWayEvent
    event = OnMyWayEvent(
        customer_id=456,
        business_id=789,
        eta_minutes=20,
    )
    
    await event_bus.emit(event)
    
    # Wait for async processing
    await asyncio.sleep(0.5)
    
    # Verify queue is empty (message was processed)
    assert service._queue.qsize() == 0
    
    await service.stop()
    
    # Query database to verify MessageLog was created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        result = await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(MessageLog).where(
                MessageLog.trigger_source == "on_my_way"
            )
        )
        message_logs = result.scalars().all()
        
        assert len(message_logs) > 0
        latest_log = message_logs[-1]
        assert "way" in latest_log.content.lower()
        assert "20" in latest_log.content
        assert latest_log.status == MessageStatus.SENT
        break


@pytest.mark.asyncio
async def test_multiple_events_concurrent_processing():
    """
    Integration test: Emit multiple events and verify all are processed.
    """
    from datetime import datetime, timezone
    
    service = MessagingService()
    service.register_handlers()
    await service.start()
    
    # Emit multiple events concurrently
    events = [
        JobBookedEvent(job_id=1, customer_id=1, business_id=1),
        JobScheduledEvent(
            job_id=2,
            customer_id=2,
            business_id=1,
            scheduled_at=datetime.now(timezone.utc),
        ),
        OnMyWayEvent(customer_id=3, business_id=1, eta_minutes=10),
    ]
    
    # Emit all events
    for event in events:
        await event_bus.emit(event)
    
    # Wait for all messages to be processed
    await asyncio.sleep(1.0)
    
    # Verify queue is empty
    assert service._queue.qsize() == 0
    
    await service.stop()
    
    # Query database to verify all MessageLogs were created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        result = await db.execute(__import__("sqlalchemy", fromlist=["select"]).select(MessageLog))
        message_logs = result.scalars().all()
        
        # Should have at least 3 message logs
        assert len(message_logs) >= 3
        
        # Verify different trigger sources
        trigger_sources = {log.trigger_source for log in message_logs}
        assert "job_booked" in trigger_sources
        assert "job_scheduled" in trigger_sources
        assert "on_my_way" in trigger_sources
        break
