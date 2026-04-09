import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import User, UserRole, ConversationState, ConversationStatus
from src.tool_executor import ToolExecutor
from src.uimodels import GetBillingStatusTool, HelpTool
from src.services.rbac_service import RBACService
from src.services.chat.handlers.idle import IdleHandler
from src.llm_client import LLMParser

@pytest.mark.asyncio
async def test_rbac_permission_denied_message_format():
    """
    Verify that the permission denied message follows the strict format:
    "It seems you are trying to [friendly name]. Sorry, you don't have permission for that."
    and does NOT contain "Error: " prefix.
    """
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)

    # Mock repositories
    session = AsyncMock()
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    # ToolExecutor
    executor = ToolExecutor(session, 1, 1, "123", MagicMock())
    executor.user_repo = user_repo

    # Execute GetBillingStatusTool (requires OWNER, user is EMPLOYEE)
    tool = GetBillingStatusTool()

    result, _ = await executor.execute(tool)

    # Assertions
    expected_msg = "It seems you are trying to check billing. Sorry, you don't have permission for that."

    # Check that it matches the expected message EXACTLY (or at least contains it without Error prefix)
    assert expected_msg in result
    assert not result.startswith("Error: ")
    assert result == expected_msg

@pytest.mark.asyncio
async def test_help_tool_disclaimer_overzealous():
    """
    Verify if the disclaimer is appended even for allowed topics.
    If I ask about 'Add Lead' (allowed for EMPLOYEE), I shouldn't see the disclaimer.
    """
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)

    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    # Mock HelpService
    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
        help_instance = MockHelpService.return_value
        # Help service answers a question about an allowed feature
        help_instance.generate_help_response = AsyncMock(return_value="To add a lead, type 'Add lead John Doe'.")

        # IdleHandler
        handler = IdleHandler(
            session=session,
            parser=parser,
            template_service=MagicMock(),
            summary_generator=MagicMock(),
            undo_handler=MagicMock(),
            geocoding_service=MagicMock(),
            invitation_service=MagicMock(),
            auto_confirm_service=MagicMock()
        )

        state_record = MagicMock()
        state_record.active_channel = "WHATSAPP"

        # Mock ServiceRepository
        with patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:
            MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])

            response = await handler.handle(user, state_record, "How do I add a lead?")

            # The disclaimer checks if user is not OWNER.
            # If implementation is naive, it will append it.
            disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."

            # We expect the disclaimer NOT to be present for allowed features.
            assert disclaimer not in response, "Disclaimer should not be present for allowed features"
