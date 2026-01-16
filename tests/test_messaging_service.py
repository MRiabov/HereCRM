import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from src.services.messaging_service import MessagingService
from src.models import MessageStatus, MessageType, Business, Customer
from src.events import JobBookedEvent, JobScheduledEvent, OnMyWayEvent
from src.database import get_db


@pytest.mark.asyncio
async def test_send_message_creates_message_log():
    """Test that send_message creates a MessageLog entry in the database."""
    service = MessagingService()
    
    # Send a message
    message_log = await service.send_message(
        recipient_phone="+1234567890",
        content="Test message",
        channel="whatsapp",
        trigger_source="test",
    )
    
    # Verify MessageLog was created
    assert message_log is not None
    assert message_log.id is not None
    assert message_log.recipient_phone == "+1234567890"
    assert message_log.content == "Test message"
    assert message_log.message_type == MessageType.WHATSAPP
    assert message_log.trigger_source == "test"
    
    # Verify status was updated to SENT (mock implementation)
    assert message_log.status == MessageStatus.SENT
    assert message_log.sent_at is not None
    assert message_log.external_id is not None


@pytest.mark.asyncio
async def test_send_message_sms_channel():
    """Test that send_message works with SMS channel."""
    service = MessagingService()
    
    # Send an SMS message
    message_log = await service.send_message(
        recipient_phone="+1234567890",
        content="Test SMS",
        channel="sms",
        trigger_source="test",
    )
    
    # Verify MessageLog was created with SMS type
    assert message_log.message_type == MessageType.SMS
    assert message_log.status == MessageStatus.SENT


@pytest.mark.asyncio
async def test_send_message_handles_errors():
    """Test that send_message handles errors gracefully."""
    service = MessagingService()
    
    # Mock the asyncio.sleep to raise an exception
    with patch("asyncio.sleep", side_effect=Exception("API Error")):
        message_log = await service.send_message(
            recipient_phone="+1234567890",
            content="Test message",
            channel="whatsapp",
            trigger_source="test",
        )
    
    # Verify MessageLog was created but marked as FAILED
    assert message_log.status == MessageStatus.FAILED
    assert message_log.error_message == "API Error"
    assert message_log.sent_at is None


@pytest.mark.asyncio
async def test_enqueue_message():
    """Test that enqueue_message adds messages to the queue."""
    service = MessagingService()
    
    # Enqueue a message
    await service.enqueue_message(
        recipient_phone="+1234567890",
        content="Queued message",
        channel="whatsapp",
        trigger_source="test",
    )
    
    # Verify message was added to queue
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert message_data["recipient_phone"] == "+1234567890"
    assert message_data["content"] == "Queued message"
    assert message_data["channel"] == "whatsapp"
    assert message_data["trigger_source"] == "test"


@pytest.mark.asyncio
async def test_process_queue():
    """Test that process_queue processes messages from the queue."""
    service = MessagingService()
    
    # Enqueue a message
    await service.enqueue_message(
        recipient_phone="+1234567890",
        content="Queued message",
        channel="whatsapp",
        trigger_source="test",
    )
    
    # Start the service
    await service.start()
    
    # Wait for the message to be processed
    await asyncio.sleep(0.5)
    
    # Stop the service
    await service.stop()
    
    # Verify queue is empty
    assert service._queue.qsize() == 0


@pytest.mark.asyncio
async def test_handle_job_booked_event():
    """Test that handle_job_booked enqueues a message."""
    service = MessagingService()
    
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
        
        # Create a JobBookedEvent
        event = JobBookedEvent(
            job_id=1,
            customer_id=customer.id,
            business_id=business.id,
            description="Test job",
        )
        
        # Handle the event
        await service.handle_job_booked(event)
        break
    
    # Verify message was enqueued
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert "+1234567890" in message_data["recipient_phone"]
    assert "job_id" in message_data["content"].lower() or "1" in message_data["content"]
    assert message_data["trigger_source"] == "job_booked"


@pytest.mark.asyncio
async def test_handle_job_scheduled_event():
    """Test that handle_job_scheduled enqueues a message."""
    service = MessagingService()
    
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
        
        # Create a JobScheduledEvent
        event = JobScheduledEvent(
            job_id=1,
            customer_id=customer.id,
            business_id=business.id,
            scheduled_at=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        
        # Handle the event
        await service.handle_job_scheduled(event)
        break
    
    # Verify message was enqueued
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert "+1234567890" in message_data["recipient_phone"]
    assert "scheduled" in message_data["content"].lower()
    assert message_data["trigger_source"] == "job_scheduled"


@pytest.mark.asyncio
async def test_handle_on_my_way_event():
    """Test that handle_on_my_way enqueues a message."""
    service = MessagingService()
    
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
        
        # Create an OnMyWayEvent
        event = OnMyWayEvent(
            customer_id=customer.id,
            business_id=business.id,
            eta_minutes=15,
        )
        
        # Handle the event
        await service.handle_on_my_way(event)
        break
    
    # Verify message was enqueued
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert "+1234567890" in message_data["recipient_phone"]
    assert "on our way" in message_data["content"].lower() or "way" in message_data["content"].lower()
    assert "15" in message_data["content"]
    assert message_data["trigger_source"] == "on_my_way"


@pytest.mark.asyncio
async def test_register_handlers():
    """Test that register_handlers subscribes to events."""
    from src.services.event_bus import event_bus
    
    service = MessagingService()
    
    # Clear any existing handlers
    event_bus._handlers.clear()
    
    # Register handlers
    service.register_handlers()
    
    # Verify handlers were registered
    assert JobBookedEvent in event_bus._handlers
    assert JobScheduledEvent in event_bus._handlers
    assert OnMyWayEvent in event_bus._handlers
    
    assert service.handle_job_booked in event_bus._handlers[JobBookedEvent]
    assert service.handle_job_scheduled in event_bus._handlers[JobScheduledEvent]
    assert service.handle_on_my_way in event_bus._handlers[OnMyWayEvent]
