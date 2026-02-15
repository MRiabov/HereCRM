import pytest
from unittest.mock import AsyncMock, patch
from src.services.assignment_service import AssignmentService
from src.services.calendar_sync_handler import CalendarSyncHandler
from src.models import Job, User, Business, JobStatus, Customer
from src.database import AsyncSessionLocal
from src.events import event_bus
from datetime import datetime

@pytest.mark.asyncio
async def test_calendar_reassignment_bug():
    # Setup - mock GoogleCalendarService
    with patch("src.services.calendar_sync_handler.GoogleCalendarService") as MockGCalService:
        mock_gcal = MockGCalService.return_value
        mock_gcal.create_event = AsyncMock(return_value="new_event_id")
        mock_gcal.update_event = AsyncMock(return_value=True)
        mock_gcal.delete_event = AsyncMock(return_value=True)

        # Initialize handler and register events
        # Note: calendar_sync_handler global instance might already be registered in main app,
        # but in tests we often need to manually ensure it.
        # However, conftest.py resets event_bus.
        handler = CalendarSyncHandler()
        handler.register()

        async with AsyncSessionLocal() as session:
            # Create Business
            business = Business(name="Test Biz")
            session.add(business)
            await session.flush()

            # Create Users
            user1 = User(
                business_id=business.id,
                email="user1@example.com",
                google_calendar_sync_enabled=True,
                google_calendar_credentials={"token": "abc", "scopes": []}
            )
            user2 = User(
                business_id=business.id,
                email="user2@example.com",
                google_calendar_sync_enabled=True,
                google_calendar_credentials={"token": "def", "scopes": []}
            )
            session.add_all([user1, user2])
            await session.flush()

            user1_id = user1.id
            user2_id = user2.id
            business_id = business.id

            # Create Customer
            customer = Customer(
                business_id=business_id,
                name="Test Customer",
                phone="1234567890"
            )
            session.add(customer)
            await session.flush()

            # Create Job assigned to User 1
            job = Job(
                business_id=business.id,
                customer_id=customer.id,
                employee_id=user1.id,
                scheduled_at=datetime.now(),
                gcal_event_id="old_event_id", # Simulate existing event
                status=JobStatus.SCHEDULED
            )
            session.add(job)
            await session.commit()

            job_id = job.id

        # Now, use AssignmentService to reassign to User 2
        async with AsyncSessionLocal() as session:
            service = AssignmentService(session, business_id)

            # Action: Reassign
            result = await service.assign_job(job_id, user2_id)
            assert result.success


        # Verify Mocks
        delete_calls = mock_gcal.delete_event.call_args_list
        update_calls = mock_gcal.update_event.call_args_list
        create_calls = mock_gcal.create_event.call_args_list

        print(f"Delete calls: {delete_calls}")
        print(f"Update calls: {update_calls}")
        print(f"Create calls: {create_calls}")

        # Check if we tried to update the old event for the new user
        has_updated_incorrectly = False
        for call in update_calls:
            args, _ = call
            job_arg = args[0]
            user_arg = args[1]
            # If update called with old event ID but user is user2
            if job_arg.gcal_event_id == "old_event_id" and user_arg.id == user2_id:
                has_updated_incorrectly = True

        # Check if we deleted the old event for the old user
        has_deleted_old = False
        for call in delete_calls:
            args, _ = call
            event_id_arg = args[0]
            user_arg = args[1]
            if event_id_arg == "old_event_id" and user_arg.id == user1_id:
                 has_deleted_old = True

        if has_updated_incorrectly:
             pytest.fail("Bug reproduced: Tried to update old event ID for new user!")

        if not has_deleted_old:
             pytest.fail("Bug reproduced: Did not delete old event!")
