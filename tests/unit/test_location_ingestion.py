import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.whatsapp_service import WhatsappService
from src.models import User, Message

@pytest.mark.asyncio
async def test_location_ingestion_whatsapp(async_session):
    # Mock dependencies
    parser_mock = MagicMock()
    template_mock = MagicMock()
    template_mock.render.return_value = "Template response"
    
    service = WhatsappService(async_session, parser_mock, template_mock)
    
    # Mock User
    user = User(id=1, phone_number="1234567890", business_id=1)
    
    # Mock LocationService.update_location and parse_location_from_text
    with patch("src.services.whatsapp_service.LocationService") as LocationServiceMock:
        LocationServiceMock.parse_location_from_text.return_value = (53.3, -6.2)
        LocationServiceMock.update_location = AsyncMock()
        
        
        # Test Case 1: Explicit Location Message
        print("DEBUG: Calling handle_message with location")
        resp = await service.handle_message(
            user_phone="1234567890",
            message_text="",
            user_id=1,
            media_type="location"
        )
        print(f"DEBUG: Response 1: {resp}")
        
        # Verify call count
        print(f"DEBUG: Mock calls: {LocationServiceMock.parse_location_from_text.call_args_list}")
        
        assert resp == "Thanks, your location has been updated and tracking is active."
        LocationServiceMock.update_location.assert_awaited_with(service.session, 1, 53.3, -6.2)
        
        # Test Case 2: SMS Text with Link
        LocationServiceMock.update_location.reset_mock()
        resp = await service.handle_message(
            user_phone="1234567890",
            message_text="Here is my location: maps.google.com/?q=53.3,-6.2",
            user_id=1,
            channel="sms"
        )
        print(f"DEBUG: Response 2: {resp}")
        assert resp == "Thanks, your location has been updated and tracking is active."
        LocationServiceMock.update_location.assert_awaited_with(service.session, 1, 53.3, -6.2)
