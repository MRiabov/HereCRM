import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.services.whatsapp_service import WhatsappService
from src.uimodels import HelpTool
from src.models import User, MessageRole, ConversationState, ConversationStatus

async def verify_integration_flow():
    # 1. Setup Mocks
    mock_session = AsyncMock()
    mock_parser = AsyncMock() # parse is async
    mock_template = MagicMock()
    
    service = WhatsappService(mock_session, mock_parser, mock_template)
    
    # Mock repositories
    service.user_repo = AsyncMock()
    service.user_repo.get_by_phone.return_value = User(phone_number="+123456", business_id=1)
    
    service.state_repo = AsyncMock()
    service.state_repo.get_by_phone.return_value = ConversationState(phone_number="+123456", state=ConversationStatus.IDLE)
    
    # Mock ServiceRepository
    with patch('src.services.whatsapp_service.ServiceRepository') as MockRepo:
        MockRepo.return_value.get_all_for_business = AsyncMock(return_value=[])
        
        # Mock Parser.parse to return HelpTool
        mock_parser.parse.return_value = HelpTool()
        
        # Mock HelpService.generate_help_response
        with patch('src.services.help_service.HelpService.generate_help_response', new_callable=AsyncMock) as mock_help_gen:
            mock_help_gen.return_value = "This is a RAG help response"
            
            print("Running handle_message with 'help'...")
            response = await service.handle_message("+123456", "help")
            
            print(f"Response: {response}")
            assert response == "This is a RAG help response"
            mock_help_gen.assert_called_once()
            print("✓ HelpService was correctly called during integration.")

if __name__ == "__main__":
    asyncio.run(verify_integration_flow())
