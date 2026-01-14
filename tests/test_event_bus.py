import pytest
from src.services.event_bus import EventBus
from src.events import JobBookedEvent

@pytest.mark.asyncio
async def test_event_bus_subscribe_and_emit():
    bus = EventBus()
    received_events = []

    async def mock_handler(event):
        received_events.append(event)

    bus.subscribe(JobBookedEvent, mock_handler)
    
    event = JobBookedEvent(job_id=1, customer_id=1, business_id=1)
    await bus.emit(event)

    assert len(received_events) == 1
    assert received_events[0] == event

@pytest.mark.asyncio
async def test_event_bus_multiple_handlers():
    bus = EventBus()
    counter = {"val": 0}

    async def handler1(event):
        counter["val"] += 1

    async def handler2(event):
        counter["val"] += 1

    bus.subscribe(JobBookedEvent, handler1)
    bus.subscribe(JobBookedEvent, handler2)
    
    event = JobBookedEvent(job_id=1, customer_id=1, business_id=1)
    await bus.emit(event)

    assert counter["val"] == 2

@pytest.mark.asyncio
async def test_event_bus_sync_handler():
    bus = EventBus()
    received = []

    def sync_handler(event):
        received.append(event)

    bus.subscribe(JobBookedEvent, sync_handler)
    
    event = JobBookedEvent(job_id=1, customer_id=1, business_id=1)
    await bus.emit(event)

    assert len(received) == 1
    assert received[0] == event

@pytest.mark.asyncio
async def test_event_bus_no_handlers():
    bus = EventBus()
    # Should not raise exception
    await bus.emit(JobBookedEvent(job_id=1, customer_id=1, business_id=1))
