import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.tool_executor import ToolExecutor
from src.models import User, Business, UserRole
from src.services.template_service import TemplateService
from src.uimodels import CheckETATool, LocateEmployeeTool
from src.tools.invoice_tools import SendInvoiceTool


@pytest.mark.asyncio
async def test_employee_can_use_check_eta(async_session: AsyncSession):
    """
    Scenario 1: Employee tries to use CheckETATool (Allowed).
    Verify tool runs successfully.
    """
    # Setup: Create business and employee user
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    employee = User(
        name="Test Employee",
        phone_number="+1234567890",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(employee)
    await async_session.flush()
    
    # Create ToolExecutor
    template_service = TemplateService()
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=employee.id,
        user_phone=employee.phone_number,
        template_service=template_service
    )
    
    # Create tool call
    tool = CheckETATool(customer_query="Test Customer")
    
    # Execute - should not be denied
    result, metadata = await executor.execute(tool)
    
    # Verify it's not a permission denial
    assert "Sorry, you don't have permission" not in result


@pytest.mark.asyncio
async def test_employee_cannot_use_send_invoice(async_session: AsyncSession):
    """
    Scenario 2: Employee tries to use SendInvoiceTool (Denied).
    Verify returned string matches the denial format.
    """
    # Setup: Create business and employee user
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    employee = User(
        name="Test Employee",
        phone_number="+1234567890",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(employee)
    await async_session.flush()
    
    # Create ToolExecutor
    template_service = TemplateService()
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=employee.id,
        user_phone=employee.phone_number,
        template_service=template_service
    )
    
    # Create tool call
    tool = SendInvoiceTool(query="Test Customer")
    
    # Execute - should be denied
    result, metadata = await executor.execute(tool)
    
    # Verify permission denial message
    assert "It seems you are trying to send invoices" in result
    assert "Sorry, you don't have permission for that" in result


@pytest.mark.asyncio
async def test_manager_can_use_locate_employee(async_session: AsyncSession):
    """
    Scenario 3: Manager tries to use LocateEmployeeTool (Allowed).
    Verify tool runs successfully.
    """
    # Setup: Create business and manager user
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    manager = User(
        name="Test Manager",
        phone_number="+1234567891",
        business_id=business.id,
        role=UserRole.MANAGER
    )
    async_session.add(manager)
    await async_session.flush()
    
    # Create ToolExecutor
    template_service = TemplateService()
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=manager.id,
        user_phone=manager.phone_number,
        template_service=template_service
    )
    
    # Create tool call
    tool = LocateEmployeeTool(employee_query="Test Employee")
    
    # Execute - should not be denied
    result, metadata = await executor.execute(tool)
    
    # Verify it's not a permission denial
    assert "Sorry, you don't have permission" not in result


@pytest.mark.asyncio
async def test_manager_can_use_send_invoice(async_session: AsyncSession):
    """
    Scenario 4: Manager tries to use SendInvoiceTool (Allowed).
    Verify tool runs successfully (or fails with non-permission error).
    """
    # Setup: Create business and manager user
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    manager = User(
        name="Test Manager",
        phone_number="+1234567891",
        business_id=business.id,
        role=UserRole.MANAGER
    )
    async_session.add(manager)
    await async_session.flush()
    
    # Create ToolExecutor
    template_service = TemplateService()
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=manager.id,
        user_phone=manager.phone_number,
        template_service=template_service
    )
    
    # Create tool call
    tool = SendInvoiceTool(query="Test Customer")
    
    # Execute - should NOT be denied
    result, metadata = await executor.execute(tool)
    
    # Verify permission is NOT denied
    assert "Sorry, you don't have permission" not in result


@pytest.mark.asyncio
async def test_owner_can_use_send_invoice(async_session: AsyncSession):
    """
    Scenario 5: Owner tries SendInvoiceTool (Allowed).
    Verify tool runs successfully.
    """
    # Setup: Create business and owner user
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    owner = User(
        name="Test Owner",
        phone_number="+1234567892",
        business_id=business.id,
        role=UserRole.OWNER
    )
    async_session.add(owner)
    await async_session.flush()
    
    # Create ToolExecutor
    template_service = TemplateService()
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=owner.id,
        user_phone=owner.phone_number,
        template_service=template_service
    )
    
    # Create tool call
    tool = SendInvoiceTool(query="Test Customer")
    
    # Execute - should not be denied (though it may fail for other reasons like customer not found)
    result, metadata = await executor.execute(tool)
    
    # Verify it's not a permission denial
    assert "Sorry, you don't have permission" not in result
