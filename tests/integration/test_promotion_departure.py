import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.models import Business, User, UserRole
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService
from src.tools.employee_management import (
    PromoteUserTool,
    DismissUserTool,
    LeaveBusinessTool,
)


@pytest.mark.asyncio
async def test_owner_can_promote_employee(async_session: Session):
    # Setup
    business = Business(name="Test Biz Match")
    async_session.add(business)
    await async_session.flush()

    owner = User(
        name="Owner", phone_number="+100", business_id=business.id, role=UserRole.OWNER
    )
    employee = User(
        name="John Doe",
        phone_number="+101",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    async_session.add_all([owner, employee])
    await async_session.commit()

    # Execute
    executor = ToolExecutor(
        async_session, business.id, owner.id, owner.phone_number, TemplateService()
    )
    tool = PromoteUserTool(employee_query="John")
    result, metadata = await executor.execute(tool)

    # Verify
    assert "Promoted John Doe to Manager" in result

    await async_session.refresh(employee)
    assert employee.role == UserRole.MANAGER


@pytest.mark.asyncio
async def test_owner_can_dismiss_employee(async_session: Session):
    # Setup
    business = Business(name="Test Biz Dismiss")
    async_session.add(business)
    await async_session.flush()

    owner = User(
        name="Owner", phone_number="+200", business_id=business.id, role=UserRole.OWNER
    )
    employee = User(
        name="Fired Guy",
        phone_number="+201",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    async_session.add_all([owner, employee])
    await async_session.commit()

    # Execute
    executor = ToolExecutor(
        async_session, business.id, owner.id, owner.phone_number, TemplateService()
    )
    tool = DismissUserTool(employee_query="Fired")
    result, metadata = await executor.execute(tool)

    # Verify
    assert "Dismissed Fired Guy" in result

    # Verify deletion
    stmt = select(User).where(User.id == employee.id)
    res = await async_session.execute(stmt)
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_employee_can_leave_business(async_session: Session):
    # Setup
    business = Business(name="Test Biz Leave")
    async_session.add(business)
    await async_session.flush()

    employee = User(
        name="Quitting Guy",
        phone_number="+301",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    async_session.add(employee)
    await async_session.commit()

    # Execute
    executor = ToolExecutor(
        async_session,
        business.id,
        employee.id,
        employee.phone_number,
        TemplateService(),
    )
    tool = LeaveBusinessTool()
    result, metadata = await executor.execute(tool)

    # Verify
    assert "You have left the business" in result

    stmt = select(User).where(User.id == employee.id)
    res = await async_session.execute(stmt)
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_employee_cannot_promote(async_session: Session):
    # Setup
    business = Business(name="Test Biz Fail")
    async_session.add(business)
    await async_session.flush()

    pawn = User(
        name="Pawn",
        phone_number="+401",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    other = User(
        name="Other",
        phone_number="+402",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    async_session.add_all([pawn, other])
    await async_session.commit()

    # Execute
    executor = ToolExecutor(
        async_session, business.id, pawn.id, pawn.phone_number, TemplateService()
    )
    tool = PromoteUserTool(employee_query="Other")
    result, _ = await executor.execute(tool)

    # Verify Permission Denied
    assert "don't have permission" in result
