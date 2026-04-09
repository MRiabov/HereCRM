import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import User, UserRole, Business
from src.tool_executor import ToolExecutor
from src.uimodels import AddServiceTool, HelpTool
from src.services.chat.handlers.idle import IdleHandler
from src.llm_client import LLMParser

@pytest.mark.asyncio
async def test_tool_executor_denial_message_format():
    """Verify that ToolExecutor returns the EXACT denial message required by FR-005."""
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)
    business = Business(id=1, active_addons=[])

    session = AsyncMock()
    session.get.side_effect = lambda model, id: business if model == Business else None

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    executor = ToolExecutor(session, 1, 1, "123", MagicMock())
    executor.user_repo = user_repo

    # AddServiceTool is restricted to OWNER (EMPLOYEE should fail)
    tool = AddServiceTool(name="Test Service", price=10.0)

    # Execute
    result, _ = await executor.execute(tool)

    # Expected: "It seems you are trying to add services. Sorry, you don't have permission for that."
    # Current implementation prepends "Error: "
    expected_message = "It seems you are trying to add services. Sorry, you don't have permission for that."

    # Check for exact match or containment without "Error: " prefix
    # The spec says: "The system MUST return a message to the LLM in the format: ..."
    # So "Error: It seems..." is technically failing the format if strict.
    assert result == expected_message, f"Expected '{expected_message}', but got '{result}'"

@pytest.mark.asyncio
async def test_idle_handler_disclaimer_conditional():
    """Verify that IdleHandler appends disclaimer ONLY for restricted topics."""
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)
    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    # Mock HelpService
    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
        help_instance = MockHelpService.return_value
        help_instance.generate_help_response = AsyncMock(return_value="Here is some help.")

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

        disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."

        with patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:
            MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])

            # Case 1: Safe topic (e.g., adding a job)
            response_safe = await handler.handle(user, state_record, "How do I add a job?")
            assert disclaimer not in response_safe, "Disclaimer should NOT be present for safe topics"

            # Case 2: Restricted topic (e.g., revenue)
            response_restricted = await handler.handle(user, state_record, "How do I view revenue?")
            assert disclaimer in response_restricted, "Disclaimer SHOULD be present for restricted topics"
