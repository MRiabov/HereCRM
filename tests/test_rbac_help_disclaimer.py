import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.chat.handlers.idle import IdleHandler
from src.services.help_service import HelpService
from src.models import User, UserRole, ConversationState, ConversationStatus, Message, MessageRole, MessageType
from src.uimodels import HelpTool

@pytest.mark.asyncio
async def test_idle_handler_delegates_disclaimer_to_help_service():
    # Setup mocks
    session = AsyncMock()
    parser = AsyncMock()
    template_service = MagicMock()
    summary_generator = MagicMock()
    undo_handler = MagicMock()
    geocoding_service = MagicMock()
    invitation_service = MagicMock()
    auto_confirm_service = MagicMock()

    handler = IdleHandler(
        session, parser, template_service, summary_generator,
        undo_handler, geocoding_service, invitation_service, auto_confirm_service
    )

    # Mock user as EMPLOYEE
    user = User(id=1, business_id=1, role=UserRole.EMPLOYEE, name="John Doe")
    state = ConversationState(user_id=1, state=ConversationStatus.IDLE)

    # Mock parser to return HelpTool
    parser.parse.return_value = HelpTool()

    # Mock ServiceRepository to return empty list
    with patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:
        mock_repo = MockServiceRepo.return_value
        mock_repo.get_all_for_business = AsyncMock(return_value=[])

        # Mock HelpService
        with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
            mock_help_service = MockHelpService.return_value
            # The mock returns a clean response.
            # If IdleHandler logic is fixed, it won't append anything.
            mock_help_service.generate_help_response = AsyncMock(return_value="Here is how you add a job.")

            response = await handler.handle(user, state, "How do I add a job?")

            # Verify generate_help_response was called with user_role
            mock_help_service.generate_help_response.assert_called_with(
                user_query="How do I add a job?",
                business_id=user.business_id,
                user_id=user.id,
                channel="WHATSAPP",
                user_role=UserRole.EMPLOYEE
            )

            # Check if disclaimer is NOT appended by IdleHandler
            expected_disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."

            assert expected_disclaimer not in response
            assert response == "Here is how you add a job."

@pytest.mark.asyncio
async def test_help_service_constructs_rbac_prompt():
    # Setup
    session = AsyncMock()
    # Mock session execute for get_chat_history
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    llm_client = AsyncMock()
    help_service = HelpService(session, llm_client)

    # Mock RBACService inside HelpService
    with patch.object(help_service.rbac_service, '_config', new={
        "tools": {
            "RestrictedTool": {"friendly_name": "do restricted things", "role": "manager"},
            "PublicTool": {"friendly_name": "do public things", "role": "employee"}
        }
    }):
        # Mock load_manual
        with patch.object(help_service, '_load_manual', return_value="Manual Content"):
            await help_service.generate_help_response(
                user_query="How do I do restricted things?",
                business_id=1,
                user_id=1,
                channel=MessageType.WHATSAPP,
                user_role=UserRole.EMPLOYEE
            )

            # Verify LLM call
            args, kwargs = llm_client.chat_completion.call_args
            prompt_messages = args[0]

            system_msg = prompt_messages[0]["content"]

            # Verify RBAC Context is present
            assert "**RBAC CONTEXT**" in system_msg
            assert "User Role: EMPLOYEE" in system_msg
            assert "- do restricted things (RestrictedTool): Minimum Role MANAGER" in system_msg
            assert "The user does not have role-based access to this feature because he doesn't have a status." in system_msg
