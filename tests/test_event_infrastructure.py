import pytest
from src.models import PipelineStage, Customer
from src.events import EventBus, event_bus


def test_pipeline_stage_enum():
    assert PipelineStage.NOT_CONTACTED == "NOT_CONTACTED"
    assert PipelineStage.CONTACTED == "CONTACTED"
    assert PipelineStage.CONVERTED_ONCE == "CONVERTED_ONCE"
    assert len(PipelineStage) == 8


def test_customer_model_has_pipeline_stage():
    customer = Customer(name="Test Customer")

    # Check assignment works
    customer.pipeline_stage = PipelineStage.CONTACTED
    assert customer.pipeline_stage == PipelineStage.CONTACTED

    # Verify default value configuration via introspection
    from sqlalchemy import inspect

    mapper = inspect(Customer)
    col = mapper.columns["pipeline_stage"]
    assert col.default.arg == PipelineStage.NOT_CONTACTED


@pytest.mark.asyncio
async def test_event_bus():
    received_data = []

    async def async_handler(data):
        received_data.append(f"async:{data}")

    def sync_handler(data):
        received_data.append(f"sync:{data}")

    bus = EventBus()
    bus.subscribe("test_event", async_handler)
    bus.subscribe("test_event", sync_handler)

    await bus.emit("test_event", "hello")

    assert "async:hello" in received_data
    assert "sync:hello" in received_data
    assert len(received_data) == 2


@pytest.mark.asyncio
async def test_global_event_bus():
    # Verify the global instance is accessible and usable
    assert isinstance(event_bus, EventBus)

    received = []

    def handler(data):
        received.append(data)

    event_bus.subscribe("global_test", handler)
    await event_bus.emit("global_test", 123)

    assert received == [123]
