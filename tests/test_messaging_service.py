import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from src.services.messaging_service import MessagingService
from src.models import MessageStatus, MessageType, Business, Customer, MessageLog
from src.database import AsyncSessionLocal
from src.events import event_bus


@pytest.mark.asyncio
async def test_send_message_creates_message_log():
    """Test that send_message creates a MessageLog entry in the database."""
    service = MessagingService()
    
    # Mock _send_whatsapp to avoid hitting API
    with patch.object(MessagingService, "_send_whatsapp", return_value=(True, "mock_id")):
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
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(MessageLog).where(MessageLog.id == message_log.id)
        result = await db.execute(stmt)
        msg = result.scalar_one()
        assert msg.status == MessageStatus.SENT
        assert msg.sent_at is not None
        assert msg.external_id == "mock_id"


@pytest.mark.asyncio
async def test_send_message_sms_channel():
    """Test that send_message works with SMS channel."""
    service = MessagingService()
    
    # Mock _send_sms to avoid hitting API
    with patch.object(MessagingService, "_send_sms", return_value=(True, "mock_sms_id")):
        # Send an SMS message
        message_log = await service.send_message(
            recipient_phone="+1234567890",
            content="Test SMS",
            channel="sms",
            trigger_source="test",
        )
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(MessageLog).where(MessageLog.id == message_log.id)
        result = await db.execute(stmt)
        msg = result.scalar_one()
        assert msg.message_type == MessageType.SMS
        assert msg.status == MessageStatus.SENT


@pytest.mark.asyncio
async def test_send_message_handles_errors():
    """Test that send_message handles errors gracefully."""
    service = MessagingService()
    
    # Mock _send_whatsapp to raise an exception
    with patch.object(MessagingService, "_send_whatsapp", side_effect=Exception("API Error")):
        message_log = await service.send_message(
            recipient_phone="+1234567890",
            content="Test message",
            channel="whatsapp",
            trigger_source="test",
        )
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(MessageLog).where(MessageLog.id == message_log.id)
        result = await db.execute(stmt)
        msg = result.scalar_one()
        assert msg.status == MessageStatus.FAILED
        assert msg.error_message == "API Error"
        assert msg.sent_at is None


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
async def test_handle_job_created_event():
    """Test that handle_job_created enqueues a message."""
    service = MessagingService()
    
    # Create necessary DB records
    async with AsyncSessionLocal() as db:
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
        
        # Create a payload for JOB_CREATED
        data = {
            "job_id": 1,
            "customer_id": customer.id,
            "business_id": business.id,
        }
        
        # Handle the event
        await service.handle_job_created(data)
    
    # Verify message was enqueued
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert "+1234567890" in message_data["recipient_phone"]
    assert "1" in message_data["content"]
    assert message_data["trigger_source"] == "job_booked"


@pytest.mark.asyncio
async def test_handle_job_scheduled_event():
    """Test that handle_job_scheduled enqueues a message."""
    service = MessagingService()
    
    # Create necessary DB records
    async with AsyncSessionLocal() as db:
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
        
        # Create a payload for JOB_SCHEDULED
        data = {
            "job_id": 1,
            "customer_id": customer.id,
            "business_id": business.id,
            "scheduled_at": "2026-01-15T10:00:00Z",
        }
        
        # Handle the event
        await service.handle_job_scheduled(data)
    
    # Verify message was enqueued
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert "+1234567890" in message_data["recipient_phone"]
    assert "scheduled" in message_data["content"].lower()
    assert "2026-01-15T10:00:00Z" in message_data["content"]
    assert message_data["trigger_source"] == "job_scheduled"


@pytest.mark.asyncio
async def test_handle_on_my_way_event():
    """Test that handle_on_my_way enqueues a message."""
    service = MessagingService()
    
    # Create necessary DB records
    async with AsyncSessionLocal() as db:
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
        
        # Create an ON_MY_WAY payload
        data = {
            "customer_id": customer.id,
            "business_id": business.id,
            "eta_minutes": 15,
        }
        
        # Handle the event
        await service.handle_on_my_way(data)
    
    # Verify message was enqueued
    assert service._queue.qsize() == 1
    
    # Get the message from queue
    message_data = await service._queue.get()
    assert "+1234567890" in message_data["recipient_phone"]
    assert "on our way" in message_data["content"].lower()
    assert "15" in message_data["content"]
    assert message_data["trigger_source"] == "on_my_way"


@pytest.mark.asyncio
async def test_register_handlers():
    """Test that register_handlers subscribes to events."""
    service = MessagingService()
    
    # Clear any existing subscribers for testing purposes
    # Note: in real scenarios we might want a clean event_bus
    event_bus._subscribers.clear()
    
    # Register handlers
    service.register_handlers()
    
    # Verify handlers were registered
    assert "JOB_CREATED" in event_bus._subscribers
    assert "JOB_SCHEDULED" in event_bus._subscribers
    assert "ON_MY_WAY" in event_bus._subscribers
    
    assert service.handle_job_created in event_bus._subscribers["JOB_CREATED"]
    assert service.handle_job_scheduled in event_bus._subscribers["JOB_SCHEDULED"]
    assert service.handle_on_my_way in event_bus._subscribers["ON_MY_WAY"]
