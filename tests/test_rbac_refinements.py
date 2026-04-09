import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import User, UserRole, Business
from src.tool_executor import ToolExecutor
from src.uimodels import ExportQueryTool, HelpTool
from src.services.chat.handlers.idle import IdleHandler
from src.llm_client import LLMParser

@pytest.mark.asyncio
async def test_tool_denial_message_format():
    """
    Verify that RBAC denial messages do not contain the 'Error: ' prefix.
    FR-005: "It seems you are trying to [friendly tool name]. Sorry, you don't have permission for that."
    """
    # Setup
    user = User(id=2, role=UserRole.EMPLOYEE, business_id=1)
    business = Business(id=1, active_addons=[])

    # Mock repositories
    session = AsyncMock()
    # Mock session.get for Business
    session.get.side_effect = lambda model, id: business if model == Business else None

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    # ToolExecutor
    # Mock TemplateService
    template_service = MagicMock()

    executor = ToolExecutor(session, 1, 2, "123", template_service)
    executor.user_repo = user_repo

    # Execute ExportQueryTool (Restricted to OWNER)
    tool = ExportQueryTool(query="Select * from users")

    result, _ = await executor.execute(tool)

    # Assertions
    expected_message = "It seems you are trying to export data. Sorry, you don't have permission for that."

    # Check that the result is EXACTLY the expected message (or at least starts with it and NO Error prefix)
    # The current bug produces "Error: It seems you are trying to export data. Sorry, you don't have permission for that."

    # We want to assert it DOES NOT start with "Error: "
    assert not result.startswith("Error: "), f"Message should not start with 'Error: '. Got: {result}"
    assert result == expected_message

@pytest.mark.asyncio
async def test_help_tool_conditional_disclaimer():
    """
    Verify that HelpTool disclaimer is only added for restricted topics when user is not OWNER.
    """
    # Setup
    user = User(id=2, role=UserRole.EMPLOYEE, business_id=1)

    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)

    # We need to mock parser.parse to return HelpTool()
    parser.parse.return_value = HelpTool()

    # Mock dependencies for IdleHandler
    template_service = MagicMock()
    summary_generator = MagicMock()
    undo_handler = MagicMock()
    geocoding_service = MagicMock()
    invitation_service = MagicMock()
    auto_confirm_service = MagicMock()

    # Instantiate handler
    # We need to patch HelpService and ServiceRepository inside IdleHandler
    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService, \
         patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:

        # Setup MockHelpService
        help_instance = MockHelpService.return_value
        help_instance.generate_help_response = AsyncMock(return_value="Here is some help info.")

        # Setup MockServiceRepo
        MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])

        handler = IdleHandler(
            session=session,
            parser=parser,
            template_service=template_service,
            summary_generator=summary_generator,
            undo_handler=undo_handler,
            geocoding_service=geocoding_service,
            invitation_service=invitation_service,
            auto_confirm_service=auto_confirm_service
        )

        state_record = MagicMock()
        state_record.active_channel = "WHATSAPP"

        # Case 1: Safe Query (Should NOT have disclaimer)
        safe_query = "How do I add a job?"
        response_safe = await handler.handle(user, state_record, safe_query)

        disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."
        assert disclaimer not in response_safe, f"Disclaimer should NOT be present for safe query: '{safe_query}'"

        # Case 2: Restricted Query (Should HAVE disclaimer)
        restricted_query = "How do I export data?"

        # Reset mock for second call? No need, return value is constant string
        # But handle method calls parser.parse again.
        # parser.parse is mocked to return HelpTool() always.

        response_restricted = await handler.handle(user, state_record, restricted_query)
        assert disclaimer in response_restricted, f"Disclaimer SHOULD be present for restricted query: '{restricted_query}'"
