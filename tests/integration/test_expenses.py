import pytest
from datetime import datetime, timezone
from src.services.expenses import ExpenseService
from src.models import User, Job, Business, UserRole, Customer, Expense
from src.uimodels import AddExpenseTool
from src.tools.expenses import execute_add_expense

@pytest.mark.asyncio
async def test_expense_service_crud(async_session):
    # Setup data
    business = Business(name="Expense Biz", created_at=datetime.now(timezone.utc))
    async_session.add(business)
    await async_session.flush()

    user = User(
        name="Expense Employee",
        phone_number="+16666666666",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(user)
    await async_session.flush()

    service = ExpenseService(async_session)

    # 1. Create expense
    expense = await service.create_expense(
        business_id=business.id,
        employee_id=user.id,
        amount=50.5,
        category="Fuel",
        description="Fuel for truck"
    )
    assert expense.id is not None
    assert expense.amount == 50.5
    assert expense.category == "Fuel"

    # 2. Get expenses
    expenses = await service.get_expenses(business.id)
    assert len(expenses) == 1
    assert expenses[0].id == expense.id

@pytest.mark.asyncio
async def test_add_expense_tool_integration(async_session):
    # Setup data
    business = Business(name="Tool Biz", created_at=datetime.now(timezone.utc))
    async_session.add(business)
    await async_session.flush()

    user = User(
        name="Tool Employee",
        phone_number="+17777777777",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(user)
    await async_session.flush()
    
    customer = Customer(name="Tool Customer", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()

    job = Job(business_id=business.id, customer_id=customer.id, description="Expense Job")
    async_session.add(job)
    await async_session.flush()

    service = ExpenseService(async_session)

    # 1. Test Tool without job
    tool_no_job = AddExpenseTool(amount=10.0, description="Parking", category="Parking")
    msg, metadata = await execute_add_expense(tool_no_job, service, business.id, user.id)
    
    assert "Recorded expense" in msg
    assert "Parking" in msg
    assert metadata["amount"] == 10.0
    assert metadata["job_id"] is None

    # 2. Test Tool with job
    tool_with_job = AddExpenseTool(amount=25.0, description="Supplies", category="Supplies", job_id=job.id)
    msg_job, metadata_job = await execute_add_expense(tool_with_job, service, business.id, user.id)
    
    assert f"Linked to Job #{job.id}" in msg_job
    assert metadata_job["job_id"] == job.id

    # 3. Verify in DB
    expenses = await service.get_expenses(business.id, job_id=job.id)
    assert len(expenses) == 1
    assert expenses[0].amount == 25.0
