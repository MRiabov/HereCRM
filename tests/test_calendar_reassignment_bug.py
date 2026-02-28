import pytest
from datetime import datetime, timezone
from src.models import Business, User, Job, UserRole, JobStatus
from src.services.assignment_service import AssignmentService
from src.events import event_bus, JOB_ASSIGNED, JOB_UNASSIGNED
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio

async def test_reassignment_calendar_sync_bug(async_session):
    biz = Business(name="Test Biz")
    async_session.add(biz)
    await async_session.flush()

    user1 = User(
        business_id=biz.id,
        name="User One",
        email="one@example.com",
        phone_number="1111111111",
        role=UserRole.EMPLOYEE,
    )
    user2 = User(
        business_id=biz.id,
        name="User Two",
        email="two@example.com",
        phone_number="2222222222",
        role=UserRole.EMPLOYEE,
    )
    async_session.add_all([user1, user2])
    await async_session.commit()

    from src.models import Customer
    cust = Customer(name="Cust", business_id=biz.id)
    async_session.add(cust)
    await async_session.flush()

    job = Job(
        business_id=biz.id,
        customer_id=cust.id,
        description="Fix sink",
        status=JobStatus.PENDING,
        employee_id=user1.id,
        gcal_event_id="gcal-event-123"
    )
    async_session.add(job)
    await async_session.commit()

    # We will mock event_bus.emit to intercept it
    emitted_events = []

    async def mock_emit(event_name, data=None):
        emitted_events.append((event_name, data))

        if event_name == JOB_UNASSIGNED:
            # Simulate what CalendarSyncHandler does
            job.gcal_event_id = None
            async_session.add(job)
            await async_session.commit()

        if event_name == JOB_ASSIGNED:
            # The bug is that gcal_event_id was still "gcal-event-123" when JOB_ASSIGNED was emitted
            # because AssignmentService didn't refresh the job after JOB_UNASSIGNED.
            # We assert here what the state of job.gcal_event_id is
            assert job.gcal_event_id is None, "gcal_event_id should be cleared before JOB_ASSIGNED is emitted"


    with patch.object(event_bus, "emit", side_effect=mock_emit):
        service = AssignmentService(async_session, biz.id)

        # Test reassignment
        # The memory states: AssignmentService.assign_job orchestrates reassignment by explicitly emitting JOB_UNASSIGNED for the old employee ID and setting job.gcal_event_id = None before emitting JOB_ASSIGNED for the new one, ensuring external syncs clean up correctly.
        # Wait, if AssignmentService explicitly emits JOB_UNASSIGNED and sets job.gcal_event_id = None, then we need to write that logic in AssignmentService.
        await service.assign_job(job.id, user2.id)

        # Verify events emitted
        assert any(e[0] == JOB_UNASSIGNED for e in emitted_events)
        assert any(e[0] == JOB_ASSIGNED for e in emitted_events)
