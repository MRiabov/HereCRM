
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.whatsapp_service import WhatsappService
from src.models import User, ConversationState, ConversationStatus
from src.uimodels import AddLeadTool

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
async def test_geocoding_during_summary(mock_parser, mock_template_service):
    # Setup
    session = AsyncMock()
    session.add = MagicMock()
    
    with patch("src.services.whatsapp_service.BillingService") as MockBilling:
        mock_billing = MockBilling.return_value
        mock_billing.track_message_sent = AsyncMock()
        service = WhatsappService(session, mock_parser, mock_template_service, billing_service=mock_billing)
    
    # User with no defaults, but +353 phone number
    user = User(id=1, business_id=1, phone_number="+3538956701451", preferences={})
    state = ConversationState(user_id=1, state=ConversationStatus.IDLE, active_channel="whatsapp")
    
    service.user_repo.get_by_phone = AsyncMock(return_value=user)
    service.state_repo.get_by_user_id = AsyncMock(return_value=state)
    
    # Mock GeocodingService.geocode
    # It should be called with default_country="Ireland" inferred from phone
    service.geocoding_service.geocode = AsyncMock(return_value=(
        53.3441, -6.2738, "John's Lane West", "Dublin", "Ireland", "D08", "John's Lane West, Dublin, Ireland"
    ))
    
    # Tool call with ambiguous address
    tool = AddLeadTool(name="Margaret", location="3 John's Ln W", phone="+3538956701451")
    mock_parser.parse.return_value = tool
    
    with patch("src.services.whatsapp_service.get_channel_config_loader") as mock_loader_cls:
        loader = MagicMock()
        loader.get_channel_config.return_value = {"auto_confirm": False}
        mock_loader_cls.return_value = loader
        
        # Act
        await service.handle_message("add lead Margaret at 3 John's Ln W", user_phone="+3538956701451")
        
        # Assertions
        # 1. Geocode should have been called with country hint
        service.geocoding_service.geocode.assert_called_once()
        args, kwargs = service.geocoding_service.geocode.call_args
        assert kwargs["default_country"] == "Ireland"
        
        # 2. Tool in draft_data should have updated location
        assert state.draft_data["arguments"]["location"] == "John's Lane West, Dublin, Ireland"
        assert state.draft_data["arguments"]["city"] == "Dublin"
        assert state.draft_data["arguments"]["country"] == "Ireland"

if __name__ == "__main__":
    pytest.main([__file__])
