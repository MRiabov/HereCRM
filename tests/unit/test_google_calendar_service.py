import pytest
import json
from unittest.mock import MagicMock, patch
from src.services.google_calendar_service import GoogleCalendarService
from src.models import User
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def service():
    with patch("src.services.google_calendar_service.settings") as mock_settings:
        mock_settings.google_client_id = "test_id"
        mock_settings.google_client_secret = "test_secret"
        mock_settings.google_redirect_uri = "http://test/callback"
        yield GoogleCalendarService()

@pytest.mark.asyncio
async def test_get_auth_url(service):
    with patch("src.services.google_calendar_service.Flow") as mock_flow_class:
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("http://auth_url", "test_state")
        mock_flow_class.from_client_config.return_value = mock_flow
        
        auth_url, state = service.get_auth_url(state="user_123")
        
        assert auth_url == "http://auth_url"
        mock_flow.authorization_url.assert_called_once_with(
            prompt='consent', 
            state="user_123", 
            access_type='offline',
            include_granted_scopes='true'
        )

@pytest.mark.asyncio
async def test_process_auth_callback(service):
    mock_db = MagicMock(spec=AsyncSession)
    mock_user = User(id=123)
    
    with patch("src.services.google_calendar_service.Flow") as mock_flow_class:
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = json.dumps({"token": "abc"})
        mock_flow.credentials = mock_creds
        mock_flow_class.from_client_config.return_value = mock_flow
        
        with patch("src.services.google_calendar_service.select") as mock_select:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            # We mock asyncio.to_thread to just call the function
            with patch("src.services.google_calendar_service.asyncio.to_thread", side_effect=lambda f, **kwargs: f(**kwargs)):
                success = await service.process_auth_callback("test_code", 123, mock_db)
                
                assert success is True
                assert mock_user.google_calendar_credentials == {"token": "abc"}
                assert mock_user.google_calendar_sync_enabled is True
                mock_flow.fetch_token.assert_called_once_with(code="test_code")
