import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock
from src.services.whatsapp_service import WhatsappService, ConversationStatus
from src.models import User, Business, ConversationState
from src.uimodels import GetBillingStatusTool, RequestUpgradeTool

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    session.refresh = AsyncMock()
    return session

@pytest.fixture
def mock_parser():
    return AsyncMock()

@pytest.fixture
def mock_template_service():
    ts = MagicMock()
    ts.render.return_value = "Mocked Template Response"
    return ts

@pytest.fixture
def whatsapp_service(mock_session, mock_parser, mock_template_service):
    # Mock BillingService
    mock_billing = AsyncMock()
    service = WhatsappService(mock_session, mock_parser, mock_template_service, billing_service=mock_billing)
    # Mock repositories internally
    service.user_repo = AsyncMock()
    service.state_repo = AsyncMock()
    service.business_repo = AsyncMock()
    
    return service

@pytest.mark.asyncio
async def test_billing_entry(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.IDLE)
    
    # Mock ToolExecutor execution
    with unittest.mock.patch("src.services.whatsapp_service.ToolExecutor") as MockExecutor:
        mock_exec_instance = AsyncMock()
        MockExecutor.return_value = mock_exec_instance
        mock_exec_instance.execute.return_value = ("Billing Status: Free", None)
        
        response = await whatsapp_service.handle_message("billing", user_id=1, user_phone="123")
        
        # Should transition to BILLING
        # Note: handle_message logic for "billing" keyword updates state
        # But wait, handle_message calls _handle_idle which checks keywords
        # Let's verify _handle_idle logic or the flow through handle_message
        
        # We need to ensure state_repo returns our state
        whatsapp_service.state_repo.get_by_user_id.return_value = state
        whatsapp_service.user_repo.get_by_id.return_value = user

        # Since we are mocking handle_message's internal calls, we actually need to test _handle_idle directly
        # or ensure handle_message calls it.
        # But handle_message does complex logic. 
        # For simplicity in this mock test, let's call _handle_idle directly for the keyword check part
        # OR better: run handle_message and trust the mock state repo.
        
        # Re-run logic for "billing" which is handled in _handle_idle (which is called by handle_message if state is IDLE)
        # However, handle_message logic:
        # 1. Get user -> ok
        # 2. Get state -> ok (IDLE)
        # 3. Call _handle_idle
        
        # Inside _handle_idle:
        # if "billing" in text -> state=BILLING, ToolExecutor.execute(GetBillingStatusTool)
        
        response = await whatsapp_service._handle_idle(user, state, "billing")
        
        assert state.state == ConversationStatus.BILLING
        assert "Billing Status: Free" in response

@pytest.mark.asyncio
async def test_billing_status_check(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    with unittest.mock.patch("src.services.whatsapp_service.ToolExecutor") as MockExecutor:
        mock_exec_instance = AsyncMock()
        MockExecutor.return_value = mock_exec_instance
        mock_exec_instance.execute.return_value = ("Status: Active", None)
        
        response = await whatsapp_service._handle_billing(user, state, "status")
        
        assert "Status: Active" in response
        # Verify GetBillingStatusTool was called
        args, _ = mock_exec_instance.execute.call_args
        assert isinstance(args[0], GetBillingStatusTool)

@pytest.mark.asyncio
async def test_billing_upgrade_request_seat(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    response = await whatsapp_service._handle_billing(user, state, "buy 5 seats")
    
    assert state.state == ConversationStatus.WAITING_CONFIRM
    assert state.draft_data["tool_name"] == "RequestUpgradeTool"
    assert state.draft_data["arguments"]["item_type"] == "seat"
    assert state.draft_data["arguments"]["quantity"] == 5

@pytest.mark.asyncio
async def test_billing_upgrade_request_addon(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    response = await whatsapp_service._handle_billing(user, state, "I want the campaign addon")
    
    assert state.state == ConversationStatus.WAITING_CONFIRM
    assert state.draft_data["tool_name"] == "RequestUpgradeTool"
    assert state.draft_data["arguments"]["item_type"] == "addon"
    assert state.draft_data["arguments"]["item_id"] == "campaign_manager"

@pytest.mark.asyncio
async def test_billing_exit(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    await whatsapp_service._handle_billing(user, state, "exit")
    assert state.state == ConversationStatus.IDLE
