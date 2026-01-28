import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Mock necessary imports before importing our services
import sys
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()

from src.services.google_calendar_service import GoogleCalendarService
from src.services.calendar_sync_handler import CalendarSyncHandler
from src.models import Job, User, Customer

async def test_sync_logic():
    print("Testing Google Calendar Sync Logic...")
    
    # 1. Setup Mock User and Job
    user = User(
        id=1,
        google_calendar_sync_enabled=True,
        google_calendar_credentials={"access_token": "abc", "refresh_token": "def"}
    )
    
    customer = Customer(name="John Doe", phone="+123456789")
    job = Job(
        id=101,
        business_id=1,
        employee_id=1,
        customer=customer,
        scheduled_at=datetime.now(),
        description="Fix the leak"
    )
    
    # 2. Mock DB and Service
    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = user
    mock_db.execute.return_value.scalar_one.return_value = job
    
    service = GoogleCalendarService()
    
    # 3. Test _build_event_body
    print("Checking event body construction...")
    event_body = await service._build_event_body(job, mock_db)
    print(f"Summary: {event_body['summary']}")
    print(f"Description: {event_body['description']}")
    
    assert "John Doe" in event_body['summary']
    assert "John Doe" in event_body['description']
    assert "+123456789" in event_body['description']
    print("✅ Event body looks good!")

    # 4. Test unscheduling logic
    print("Checking unscheduling logic...")
    job.gcal_event_id = "gcal_123"
    job.scheduled_at = None
    
    handler = CalendarSyncHandler()
    with patch.object(GoogleCalendarService, 'delete_event', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True
        
        # We need to mock the DB session used inside _sync_job
        with patch('src.services.calendar_sync_handler.AsyncSessionLocal', return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_db))):
            # Also need to mock UserRepository
            with patch('src.services.calendar_sync_handler.UserRepository', return_value=MagicMock(get_by_id=AsyncMock(return_value=user))):
                await handler._sync_job(101, 1)
                
        mock_delete.assert_called_once()
    print("✅ Unscheduling logic triggers delete_event!")

    print("\nAll local sync logic tests passed!")

if __name__ == "__main__":
    asyncio.run(test_sync_logic())
