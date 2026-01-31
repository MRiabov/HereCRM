import pytest
from src.models import Business, User, UserRole
from src.tool_executor import ToolExecutor
from src.tools.invoice_tools import SendInvoiceTool
from src.uimodels import GoogleCalendarStatusTool
from src.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def template_service():
    return TemplateService()

@pytest.mark.asyncio
async def test_rbac_denial_message_format(
    async_session: AsyncSession, template_service: TemplateService
):
    """
    Test that RBAC denial message follows the exact format from spec.
    User Story 1/FR-005.
    """
    test_session = async_session
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    # Create Employee (cannot send invoices)
    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.EMPLOYEE)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )

    # SendInvoiceTool is Manager level
    tool = SendInvoiceTool(query="Bob")

    result, metadata = await executor.execute(tool)

    # FR-005: "It seems you are trying to [friendly tool name]. Sorry, you don't have permission for that."
    expected_message = "It seems you are trying to send invoices. Sorry, you don't have permission for that."

    assert result == expected_message

@pytest.mark.asyncio
async def test_missing_tool_in_rbac_fixed(
    async_session: AsyncSession, template_service: TemplateService
):
    """
    Test that a previously missing tool (GoogleCalendarStatusTool) is now accessible to OWNER.
    """
    test_session = async_session
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    # Create OWNER (should have access to everything)
    user = User(phone_number="987654321", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )

    tool = GoogleCalendarStatusTool()

    result, metadata = await executor.execute(tool)

    # Should not be denied
    assert "Sorry, you don't have permission for that" not in result
    # Should return actual tool output
    assert "Google Calendar Status" in result
