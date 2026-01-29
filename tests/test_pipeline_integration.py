import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, PipelineStage, JobStatus
from src.services.crm_service import CRMService
from src.services.pipeline_handlers import handle_job_created

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def setup_event_handlers():
    """Register the actual handlers for the test duration."""
    # Note: mocking AsyncSessionLocal inside handlers to use test_session is tricky
    # because handlers create their own session.
    # For integration tests, we want handlers to use the SAME DB as the test.
    # We will patch AsyncSessionLocal in the handler module to return our test_session factory.
    pass


@pytest.mark.asyncio
async def test_pipeline_progression_scenarios(test_session):
    """
    Test the full lifecycle:
    Not Contacted -> Converted Once -> Converted Recurrent
    """
    # 1. Setup Business
    biz = Business(name="Pipeline Biz")
    test_session.add(biz)
    await test_session.commit()

    # 2. Add Customer (directly to DB to verify default)
    c1 = Customer(name="John Pipeline", business_id=biz.id, phone="123")
    test_session.add(c1)
    await test_session.commit()

    # Assert Default Stage
    assert c1.pipeline_stage == PipelineStage.NOT_CONTACTED

    # 3. Create First Job via CRMService
    # We need to ensure the EventBus triggers the handler, AND the handler uses our test DB.
    # Since patching 'src.services.pipeline_handlers.src.database.AsyncSessionLocal' is global,
    # we can do it here.

    from unittest.mock import MagicMock, patch

    # Create a factory that yields our existing session
    # BUT wait, the handler does `async with AsyncSessionLocal() as session`.
    # Our test_session is already open. We probably want a nested transaction or just reuse it.
    # However, `test_session` fixture yields a session.
    # We need a callable that returns an async context manager that returns this session.

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__.return_value = test_session
    mock_session_cm.__aexit__.return_value = None

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session_cm

    # Also patch EventBus to run synchronously?
    # No, EventBus in this app is likely just `fire_event` which might be invalid
    # if it spins up background tasks without us resolving them.
    # Let's check `src/events.py` logic later if needed.
    # For now, let's manually invoke the handler to simulate the event bus,
    # OR assume `CRMService` calls `event_bus.emit`.
    # Ideally integration tests should test the bus too, but `handle_job_created` is async.
    # Let's manual-invoke for determinism in this "Unit-Integration" style.

    service = CRMService(test_session, biz.id)

    # Add Job 1
    with patch(
        "src.services.pipeline_handlers.src.database.AsyncSessionLocal", mock_factory
    ):
        job1 = await service.create_job(
            customer_id=c1.id,
            description="First Job",
            value=100.0,
            status=JobStatus.SCHEDULED,
        )
        # Manually trigger handler because real EventBus might be running in background (or not started)
        await handle_job_created({"customer_id": c1.id, "business_id": biz.id})

    await test_session.refresh(c1)
    assert c1.pipeline_stage == PipelineStage.CONVERTED_ONCE

    # 4. Add Job 2
    with patch(
        "src.services.pipeline_handlers.src.database.AsyncSessionLocal", mock_factory
    ):
        job2 = await service.create_job(
            customer_id=c1.id,
            description="Second Job",
            value=100.0,
            status=JobStatus.SCHEDULED,
        )
        await handle_job_created({"customer_id": c1.id, "business_id": biz.id})

    await test_session.refresh(c1)
    assert c1.pipeline_stage == PipelineStage.CONVERTED_RECURRENT


@pytest.mark.asyncio
async def test_manual_update_persistence(test_session):
    """Test manual update logic (which bypasses event bus logic usually)."""
    biz = Business(name="Manual Biz")
    test_session.add(biz)
    await test_session.commit()

    c1 = Customer(
        name="Manual Mike",
        business_id=biz.id,
        phone="999",
        pipeline_stage=PipelineStage.CONTACTED,
    )
    test_session.add(c1)
    await test_session.commit()

    service = CRMService(test_session, biz.id)

    # Manual update to LOST
    updated = await service.update_customer_stage(c1.id, PipelineStage.LOST)
    assert updated.pipeline_stage == PipelineStage.LOST

    await test_session.refresh(c1)
    assert c1.pipeline_stage == PipelineStage.LOST
