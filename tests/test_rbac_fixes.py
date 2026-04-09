import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import User, UserRole, Business
from src.tool_executor import ToolExecutor
from src.uimodels import ListServicesTool, HelpTool, UpdateSettingsTool
from src.services.chat.handlers.idle import IdleHandler
from src.llm_client import LLMParser

@pytest.mark.asyncio
async def test_tool_executor_permission_denied_message_format():
    """
    Verify that ToolExecutor does NOT prefix 'Error: ' to the permission denied message.
    Spec FR-005 requires exactly: "It seems you are trying to [friendly tool name]. Sorry, you don't have permission for that."
    """
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)
    business = Business(id=1)

    session = AsyncMock()
    session.get.side_effect = lambda model, id: business if model == Business else None

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    executor = ToolExecutor(session, 1, 1, "123", MagicMock())
    executor.user_repo = user_repo

    # Use UpdateSettingsTool which is OWNER only
    tool = UpdateSettingsTool(setting_key="default_city", setting_value="Dublin")

    result, _ = await executor.execute(tool)

    expected_message = "It seems you are trying to modify settings. Sorry, you don't have permission for that."
    assert result == expected_message, f"Expected '{expected_message}', but got '{result}'"


@pytest.mark.asyncio
async def test_idle_handler_disclaimer_on_allowed_topics():
    """
    Verify that IdleHandler appends disclaimer for non-owners ONLY when discussing restricted features/data.
    """
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)

    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
        help_instance = MockHelpService.return_value
        # Simulate a help response for an allowed feature (e.g. adding a job)
        help_instance.generate_help_response = AsyncMock(return_value="To add a job, type 'Add job for [Customer]'.")

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

        with patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:
            MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])

            # User asks about an allowed feature
            response = await handler.handle(user, state_record, "How do I add a job?")

            # The disclaimer should NOT be present because 'adding a job' is allowed for Employees.
            disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."
            assert disclaimer not in response


@pytest.mark.asyncio
async def test_list_services_tool_success():
    """Verify that ListServicesTool is now executable by employees and returns the list."""
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)
    business = Business(id=1, active_addons=["manage_employees"])

    # Mock repositories
    session = AsyncMock()
    session.get.side_effect = lambda model, id: business if model == Business else None

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    # ToolExecutor
    executor = ToolExecutor(session, 1, 1, "123", MagicMock())
    executor.user_repo = user_repo

    # Mock service repo
    executor.service_repo = AsyncMock()
    # Return some dummy services
    s1 = MagicMock(name="Service 1", default_price=10.0)
    s1.name = "Service 1"
    s1.default_price = 10.0
    s2 = MagicMock(name="Service 2", default_price=20.0)
    s2.name = "Service 2"
    s2.default_price = 20.0
    executor.service_repo.get_all_for_business.return_value = [s1, s2]

    # Execute ListServicesTool
    tool = ListServicesTool()

    result, _ = await executor.execute(tool)

    # Assertions
    assert "Sorry, you don't have permission for that" not in result
    assert "Available Services" in result
    assert "Service 1: €10.00" in result
    assert "Service 2: €20.00" in result


@pytest.mark.asyncio
async def test_help_tool_disclaimer_for_employee():
    """Verify that HelpTool responses for non-owners include the mandatory disclaimer (FR-007)."""
    # Setup
    user = User(id=1, role=UserRole.EMPLOYEE, business_id=1)

    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    # Mock HelpService
    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
        help_instance = MockHelpService.return_value
        help_instance.generate_help_response = AsyncMock(return_value="Here is how you export data.")

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

        # Mock ServiceRepository called in IdleHandler
        with patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:
            MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])

            response = await handler.handle(user, state_record, "How do I export data?")

            # FR-007: "The user does not have role-based access to this feature because he doesn't have a status."
            disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."
            assert disclaimer in response

@pytest.mark.asyncio
async def test_help_tool_no_disclaimer_for_owner():
    """Verify that HelpTool responses for owners DO NOT include the disclaimer."""
    # Setup
    user = User(id=1, role=UserRole.OWNER, business_id=1)

    session = AsyncMock()
    parser = MagicMock(spec=LLMParser)
    parser.parse.return_value = HelpTool()

    with patch("src.services.chat.handlers.idle.HelpService") as MockHelpService:
        help_instance = MockHelpService.return_value
        help_instance.generate_help_response = AsyncMock(return_value="Here is how you export data.")

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

        with patch("src.services.chat.handlers.idle.ServiceRepository") as MockServiceRepo:
            MockServiceRepo.return_value.get_all_for_business = AsyncMock(return_value=[])

            response = await handler.handle(user, state_record, "How do I export data?")

            disclaimer = "The user does not have role-based access to this feature because he doesn't have a status."
            assert disclaimer not in response
