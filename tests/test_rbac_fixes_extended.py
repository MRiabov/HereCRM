
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import User, UserRole
from src.tool_executor import ToolExecutor
from src.tools.invoice_tools import SendInvoiceTool
from src.services.rbac_service import RBACService
from src.services.template_service import TemplateService
from src.services.chat.handlers.idle import IdleHandler
from src.models import ConversationState
from src.uimodels import HelpTool
from src.llm_client import LLMParser

@pytest.mark.asyncio
async def test_tool_executor_rbac_message_format():
    """Verify that RBAC denial message does not start with 'Error: '."""
    # Setup
    session = AsyncMock()
    user_repo = AsyncMock()
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)
    user_repo.get_by_id.return_value = user

    # Mock RBACService to deny permission
    rbac_service = MagicMock(spec=RBACService)
    rbac_service.check_permission.return_value = False
    rbac_service.get_tool_config.return_value = {"friendly_name": "send invoices"}

    executor = ToolExecutor(session, 1, 1, "123", MagicMock(spec=TemplateService))
    executor.user_repo = user_repo
    executor.rbac_service = rbac_service

    # Execute tool that employee shouldn't have access to
    tool = SendInvoiceTool(query="test", force_regenerate=False)

    result, _ = await executor.execute(tool)

    expected = "It seems you are trying to send invoices. Sorry, you don't have permission for that."
    assert result == expected
    assert not result.startswith("Error: ")

@pytest.mark.asyncio
async def test_idle_handler_disclaimer_logic_benign():
    """Verify that disclaimer is NOT added for benign queries by non-owners."""
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1, phone_number="123")
    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService, \
         patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:

        MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])
        MockHelpService.return_value.generate_help_response = AsyncMock(return_value="Help content.")

        handler = IdleHandler(
            session=session, parser=parser, template_service=MagicMock(),
            summary_generator=MagicMock(), undo_handler=MagicMock(),
            geocoding_service=MagicMock(), invitation_service=MagicMock(),
            auto_confirm_service=MagicMock()
        )

        state_record = MagicMock(spec=ConversationState)
        state_record.active_channel = "WHATSAPP"

        # Benign query
        response = await handler.handle(user, state_record, "how to add job")

        assert "The user does not have role-based access" not in response

@pytest.mark.asyncio
async def test_idle_handler_disclaimer_logic_restricted():
    """Verify that disclaimer IS added for restricted queries by non-owners."""
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1, phone_number="123")
    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService, \
         patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:

        MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])
        MockHelpService.return_value.generate_help_response = AsyncMock(return_value="Help content.")

        handler = IdleHandler(
            session=session, parser=parser, template_service=MagicMock(),
            summary_generator=MagicMock(), undo_handler=MagicMock(),
            geocoding_service=MagicMock(), invitation_service=MagicMock(),
            auto_confirm_service=MagicMock()
        )

        state_record = MagicMock(spec=ConversationState)
        state_record.active_channel = "WHATSAPP"

        # Restricted query
        response = await handler.handle(user, state_record, "how to export data")

        assert "The user does not have role-based access" in response
