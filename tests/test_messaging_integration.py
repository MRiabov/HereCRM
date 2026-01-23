import pytest
import asyncio

from src.events import event_bus
from src.services.messaging_service import MessagingService
from src.models import MessageLog, MessageStatus, Business, Customer
from src.database import get_db
from datetime import datetime, timezone
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_messaging_api():
    with patch.object(MessagingService, "_send_whatsapp", return_value=(True, "mock_id")), \
         patch.object(MessagingService, "_send_sms", return_value=(True, "mock_sms_id")):
        yield


@pytest.mark.asyncio
async def test_event_bus_integration_job_created():
    """
    Integration test: Emit JOB_CREATED and verify MessagingService picks it up.
    """
    # Create a new MessagingService instance for this test
    service = MessagingService()
    
    # Register handlers
    service.register_handlers()
    
    # Start the service
    await service.start()
    
    # Create necessary DB records
    async for db in get_db():
        business = Business(name="Test Business")
        db.add(business)
        await db.commit()
        await db.refresh(business)
        
        customer = Customer(
            business_id=business.id,
            name="Test Customer",
            phone="+1234567890"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        
        event_data = {
            "job_id": 123,
            "customer_id": customer.id,
            "business_id": business.id,
        }
        break
    
    # Emit a JOB_CREATED event
    await event_bus.emit("JOB_CREATED", event_data)
    
    # Wait for async processing
    await service._queue.join()
    
    # Verify message was enqueued and processed
    # The queue should be empty after processing
    assert service._queue.qsize() == 0
    
    # Stop the service
    await service.stop()
    
    # Query database to verify MessageLog was created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        from sqlalchemy import select
        result = await db.execute(
            select(MessageLog).where(
                MessageLog.trigger_source == "job_booked"
            )
        )
        message_logs = result.scalars().all()
        
        # Should have at least one message log
        assert len(message_logs) > 0
        
        # Verify the message content
        latest_log = message_logs[-1]
        assert "123" in latest_log.content
        assert latest_log.status == MessageStatus.SENT
        break


@pytest.mark.asyncio
async def test_event_bus_integration_job_scheduled():
    """
    Integration test: Emit JOB_SCHEDULED and verify MessagingService picks it up.
    """
    service = MessagingService()
    service.register_handlers()
    await service.start()
    
    # Create necessary DB records
    async for db in get_db():
        business = Business(name="Test Business")
        db.add(business)
        await db.commit()
        await db.refresh(business)
        
        customer = Customer(
            business_id=business.id,
            name="Test Customer",
            phone="+1234567890"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        
        event_data = {
            "job_id": 123,
            "customer_id": customer.id,
            "business_id": business.id,
            "scheduled_at": datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc).isoformat(),
        }
        break
    
    # Emit a JOB_SCHEDULED event
    await event_bus.emit("JOB_SCHEDULED", event_data)
    
    # Wait for async processing
    await service._queue.join()
    
    # Verify queue is empty (message was processed)
    assert service._queue.qsize() == 0
    
    await service.stop()
    
    # Query database to verify MessageLog was created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        from sqlalchemy import select
        result = await db.execute(
            select(MessageLog).where(
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
    Integration test: Emit ON_MY_WAY and verify MessagingService picks it up.
    """
    service = MessagingService()
    service.register_handlers()
    await service.start()
    
    # Create necessary DB records
    async for db in get_db():
        business = Business(name="Test Business")
        db.add(business)
        await db.commit()
        await db.refresh(business)
        
        customer = Customer(
            business_id=business.id,
            name="Test Customer",
            phone="+1234567890"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        
        event_data = {
            "customer_id": customer.id,
            "business_id": business.id,
            "eta_minutes": 20,
        }
        break
    
    # Emit an ON_MY_WAY event
    await event_bus.emit("ON_MY_WAY", event_data)
    
    # Wait for async processing
    await service._queue.join()
    
    # Verify queue is empty (message was processed)
    assert service._queue.qsize() == 0
    
    await service.stop()
    
    # Query database to verify MessageLog was created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        from sqlalchemy import select
        result = await db.execute(
            select(MessageLog).where(
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
    service = MessagingService()
    service.register_handlers()
    await service.start()
    
    # Create necessary DB records
    async for db in get_db():
        business = Business(name="Test Business")
        db.add(business)
        await db.commit()
        await db.refresh(business)
        
        customers = []
        for i in range(3):
            c = Customer(
                business_id=business.id,
                name=f"Customer {i}",
                phone=f"+123456789{i}"
            )
            db.add(c)
            customers.append(c)
        await db.commit()
        for c in customers:
            await db.refresh(c)
            
        # Prepare events data
        event1 = ("JOB_CREATED", {"job_id": 1, "customer_id": customers[0].id, "business_id": business.id})
        event2 = ("JOB_SCHEDULED", {
                "job_id": 2,
                "customer_id": customers[1].id,
                "business_id": business.id,
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
            })
        event3 = ("ON_MY_WAY", {"customer_id": customers[2].id, "business_id": business.id, "eta_minutes": 10})
        break
    
    # Emit multiple events
    await event_bus.emit(*event1)
    await event_bus.emit(*event2)
    await event_bus.emit(*event3)
    
    # Wait for all messages to be processed
    await service._queue.join()
    
    # Verify queue is empty
    assert service._queue.qsize() == 0
    
    await service.stop()
    
    # Query database to verify all MessageLogs were created
    async for db in __import__("src.database", fromlist=["get_db"]).get_db():
        from sqlalchemy import select
        result = await db.execute(select(MessageLog))
        message_logs = result.scalars().all()
        
        # Should have at least 3 message logs
        assert len(message_logs) >= 3
        
        # Verify different trigger sources
        trigger_sources = {log.trigger_source for log in message_logs}
        assert "job_booked" in trigger_sources
        assert "job_scheduled" in trigger_sources
        assert "on_my_way" in trigger_sources
        break
