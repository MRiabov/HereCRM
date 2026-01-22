import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from src.models import User, ConversationState, ConversationStatus
from src.services.whatsapp_service import WhatsappService
from src.uimodels import AddJobTool
from src.config.loader import ChannelConfig

# Mock config loader
@pytest.fixture
def mock_config_loader():
    with patch("src.services.whatsapp_service.get_channel_config_loader") as mock:
        loader = MagicMock()
        loader.get_channel_config.return_value = {
            "auto_confirm": True,
            "auto_confirm_timeout": 45,
            "max_length": 160
        }
        mock.return_value = loader
        yield loader

@pytest.fixture
def mock_parser():
    parser = MagicMock()
    parser.parse = AsyncMock()
    return parser

@pytest.fixture
def mock_template_service():
    service = MagicMock()
    service.render.side_effect = lambda key, **kwargs: f"Rendered {key} {kwargs}"
    return service

@pytest.mark.asyncio
async def test_config_loader():
    # Test loading actual config
    config = ChannelConfig()
    sms_config = config.get_channel_config("sms")
    assert sms_config["provider"] == "twilio"
    assert sms_config["auto_confirm"] is True
    assert sms_config["max_length"] == 160

@pytest.mark.asyncio
async def test_auto_confirm_initiation(mock_config_loader, mock_parser, mock_template_service):
    # Setup
    session = AsyncMock()
    # Configure session.add to be MagicMock (sync)
    session.add = MagicMock()
    
    service = WhatsappService(session, mock_parser, mock_template_service)
    
    # Mock repositories
    user = User(id=1, business_id=1, phone_number="+1234567890", preferred_channel="sms")
    state = ConversationState(
        user_id=1, 
        state=ConversationStatus.IDLE, 
        active_channel="sms"
    )
    
    service.user_repo.get_by_phone = AsyncMock(return_value=user)
    service.state_repo.get_by_user_id = AsyncMock(return_value=state)
    service.state_repo.add = MagicMock()
    service._generate_summary = MagicMock(return_value="Add Job Summary")
    
    # Mock ServiceRepository instantiated inside _handle_idle
    with patch("src.services.whatsapp_service.ServiceRepository") as MockServiceRepo:
        mock_repo_instance = MockServiceRepo.return_value
        mock_repo_instance.get_all_for_business = AsyncMock(return_value=[])
    
        # Mock parser to return a tool
        tool = AddJobTool(description="Fix sink", price=100.0, customer_name="Alice")
        mock_parser.parse.return_value = tool
        
        # Mock background task (we don't want to actually sleep/spawn)
        with patch("asyncio.create_task") as mock_create_task:
            reply = await service.handle_message("Add job", user_phone="+1234567890", channel="sms")
            
            # Verify
            assert "Auto-confirming in 45s" in reply
            assert state.state == ConversationStatus.PENDING_AUTO_CONFIRM
            assert state.pending_action_timestamp is not None
            mock_create_task.assert_called_once()
            
@pytest.mark.asyncio
async def test_auto_confirm_cancellation(mock_config_loader, mock_parser, mock_template_service):
    session = AsyncMock()
    session.add = MagicMock() # Sync
    service = WhatsappService(session, mock_parser, mock_template_service)
    
    user = User(id=1, business_id=1, phone_number="+1234567890")
    state = ConversationState(
        user_id=1, 
        state=ConversationStatus.PENDING_AUTO_CONFIRM, 
        active_channel="sms",
        pending_action_timestamp=datetime.now(timezone.utc) + timedelta(seconds=30)
    )
    
    service.user_repo.get_by_phone = AsyncMock(return_value=user)
    service.state_repo.get_by_user_id = AsyncMock(return_value=state)
    
    # User says "No"
    reply = await service.handle_message("No", user_phone="+1234567890", channel="sms")
    
    assert "Rendered action_cancelled" in reply
    assert state.state == ConversationStatus.IDLE
    assert state.pending_action_timestamp is None

@pytest.mark.asyncio
async def test_auto_confirm_interruption_creates_new_command(mock_config_loader, mock_parser, mock_template_service):
    session = AsyncMock()
    session.add = MagicMock() # Sync
    service = WhatsappService(session, mock_parser, mock_template_service)
    
    user = User(id=1, business_id=1, phone_number="+1234567890")
    state = ConversationState(
        user_id=1, 
        state=ConversationStatus.PENDING_AUTO_CONFIRM, 
        active_channel="sms"
    )
    
    service.user_repo.get_by_phone = AsyncMock(return_value=user)
    service.state_repo.get_by_user_id = AsyncMock(return_value=state)
    service._handle_idle = AsyncMock(return_value="New Command Processed")
    
    # User says "Actually add lead" (not yes/no)
    reply = await service.handle_message("Actually add lead", user_phone="+1234567890")
    
    assert "Auto-confirm cancelled" in reply
    assert "New Command Processed" in reply
    assert state.state == ConversationStatus.IDLE 

@pytest.mark.asyncio
async def test_auto_confirm_task_execution(mock_template_service):
    # This test mocks the inside of _auto_confirm_task
    # We need to mock AsyncSessionLocal
    
    with patch("src.services.whatsapp_service.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.add = MagicMock() # Sync method
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Setup data inside the mocked session
        user = User(id=1, business_id=1, phone_number="+1234567890")
        state = ConversationState(
            user_id=1, 
            state=ConversationStatus.PENDING_AUTO_CONFIRM,
            active_channel="sms",
            pending_action_timestamp=datetime.now(timezone.utc) - timedelta(seconds=1), # Expired
            draft_data={"tool_name": "AddJobTool", "arguments": {
                "description": "Fix sink", "price": 100.0, "customer_name": "Alice"
            }}
        )
        
        # Mock repos returning this data
        mock_state_repo = MagicMock()
        mock_state_repo.get_by_user_id = AsyncMock(return_value=state)
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        
        with patch("src.services.whatsapp_service.ConversationStateRepository", return_value=mock_state_repo):
            with patch("src.services.whatsapp_service.UserRepository", return_value=mock_user_repo):
                 # Mock WhatsappService inside the task
                 with patch("src.services.whatsapp_service.WhatsappService") as MockServiceCls:
                     mock_service_instance = MockServiceCls.return_value
                     mock_service_instance._execute_draft = AsyncMock(return_value="Draft Executed")
                     
                     # Instantiate real service
                     real_service = WhatsappService(AsyncMock(), MagicMock(), MagicMock())
                     
                     # Mock TwilioService - it's imported locally in the method, so patching the source module is safest/correct
                     # Assuming the code imports: from src.services.twilio_service import TwilioService
                     with patch("src.services.twilio_service.TwilioService") as MockTwilio:
                         mock_twilio = MockTwilio.return_value
                         mock_twilio.send_sms = AsyncMock()
                         
                         # Run the task
                         await real_service._auto_confirm_task(user_id=1, timeout=0)
                         
                         # Verify execution
                         mock_service_instance._execute_draft.assert_called_once()
                         mock_twilio.send_sms.assert_called_with("+1234567890", "Draft Executed")
                         
                         # Verify system log message added
                         assert mock_session.add.call_count >= 1
                         mock_session.commit.assert_called_once()
