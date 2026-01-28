import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock
from src.services.whatsapp_service import WhatsappService, ConversationStatus
from src.models import User, ConversationState
from src.uimodels import GetBillingStatusTool

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
    
    # Mock ToolExecutor execution. Note: ToolExecutor is imported in src.services.chat.handlers.idle
    with unittest.mock.patch("src.services.chat.handlers.idle.ToolExecutor") as MockExecutor:
        mock_exec_instance = AsyncMock()
        MockExecutor.return_value = mock_exec_instance
        mock_exec_instance.execute.return_value = ("Billing Status: Free", None)
        
        # Call idle_handler directly
        response = await whatsapp_service.idle_handler.handle(user, state, "billing")
        
        assert state.state == ConversationStatus.BILLING
        assert "Billing Status: Free" in response

@pytest.mark.asyncio
async def test_billing_status_check(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    # Mock ToolExecutor in billing handler
    with unittest.mock.patch("src.services.chat.handlers.billing.ToolExecutor") as MockExecutor:
        mock_exec_instance = AsyncMock()
        MockExecutor.return_value = mock_exec_instance
        mock_exec_instance.execute.return_value = ("Status: Active", None)
        
        response = await whatsapp_service.billing_handler.handle(user, state, "status")
        
        assert "Status: Active" in response
        # Verify GetBillingStatusTool was called
        args, _ = mock_exec_instance.execute.call_args
        assert isinstance(args[0], GetBillingStatusTool)

@pytest.mark.asyncio
async def test_billing_upgrade_request_seat(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    # Mock summary generator since it's called
    whatsapp_service.billing_handler.summary_generator.generate_summary = AsyncMock(return_value="Summary")

    response = await whatsapp_service.billing_handler.handle(user, state, "buy 5 seats")
    
    assert state.state == ConversationStatus.WAITING_CONFIRM
    assert state.draft_data["tool_name"] == "RequestUpgradeTool"
    assert state.draft_data["arguments"]["item_type"] == "seat"
    assert state.draft_data["arguments"]["quantity"] == 5

@pytest.mark.asyncio
async def test_billing_upgrade_request_addon(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)

    # Mock summary generator since it's called
    whatsapp_service.billing_handler.summary_generator.generate_summary = AsyncMock(return_value="Summary")
    
    response = await whatsapp_service.billing_handler.handle(user, state, "I want the campaign addon")
    
    assert state.state == ConversationStatus.WAITING_CONFIRM
    assert state.draft_data["tool_name"] == "RequestUpgradeTool"
    assert state.draft_data["arguments"]["item_type"] == "addon"
    assert state.draft_data["arguments"]["item_id"] == "campaign_manager"

@pytest.mark.asyncio
async def test_billing_exit(whatsapp_service):
    user = User(id=1, business_id=1, phone_number="123")
    state = ConversationState(user_id=1, state=ConversationStatus.BILLING)
    
    await whatsapp_service.billing_handler.handle(user, state, "exit")
    assert state.state == ConversationStatus.IDLE
