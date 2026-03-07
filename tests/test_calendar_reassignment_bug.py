import pytest
from unittest.mock import AsyncMock, patch, ANY

from src.models import Job, User
from src.services.assignment_service import AssignmentService
from src.events import event_bus, JOB_ASSIGNED, JOB_UNASSIGNED

@pytest.mark.asyncio
async def test_assign_job_emits_unassigned_when_reassigning():
    mock_session = AsyncMock()
    service = AssignmentService(mock_session, business_id=1)

    # Setup mock job repo
    mock_job = Job(id=1, business_id=1, employee_id=10, scheduled_at="2024-01-01", gcal_event_id="test_gcal_id")
    service.job_repo.get_by_id = AsyncMock(return_value=mock_job)

    # Setup mock user repo
    mock_employee = User(id=20, business_id=1)
    service.user_repo.get_by_id = AsyncMock(return_value=mock_employee)

    mock_session.execute = AsyncMock(return_value=AsyncMock(scalars=lambda: AsyncMock(all=lambda: [])))

    emitted_events = []

    async def track_emit(event_name, data=None):
        emitted_events.append((event_name, data))

    with patch('src.services.assignment_service.event_bus.emit', side_effect=track_emit):
        await service.assign_job(1, 20)

    # Check emitted events
    assert emitted_events == [
        (JOB_UNASSIGNED, {"job_id": 1, "employee_id": 10, "business_id": 1}),
        (JOB_ASSIGNED, {"job_id": 1, "employee_id": 20, "business_id": 1})
    ]

    # Check that the job gcal_event_id was cleared
    assert mock_job.gcal_event_id is None

    # Check that employee_id is correct
    assert mock_job.employee_id == 20
