import pytest
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.services.data_management import DataManagementService
from src.models import (
    Business,
    Customer,
    Job,
    ImportJob,
    EntityType,
    ImportStatus,
    Quote,
    Request,
    Expense,
    User,
    UserRole,
    ExpenseCategory,
)


@pytest.mark.asyncio
async def test_import_quotes(async_session: AsyncSession):
    business = Business(name="Quote Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    user = User(business_id=business.id, email="q@test.com", role=UserRole.OWNER)
    async_session.add(user)
    await async_session.commit()

    service = DataManagementService(async_session)

    filename = "test_quotes.csv"
    with open(filename, "w") as f:
        f.write("Name,Quote Description,Amount\n")
        f.write("Quoty McQuote,New Roof,5000.00\n")

    try:
        job = await service.import_data(
            business.id, filename, "text/csv", entity_type=EntityType.QUOTE
        )

        assert job.status == ImportStatus.COMPLETED

        # Verify Quote exists
        result = await async_session.execute(
            select(Quote).where(Quote.business_id == business.id)
        )
        quotes = result.scalars().all()
        assert len(quotes) == 1
        assert quotes[0].title == "New Roof"
        assert quotes[0].total_amount == 5000.00

        # Verify Customer was created
        result = await async_session.execute(
            select(Customer).where(
                Customer.business_id == business.id,
                Customer.id == quotes[0].customer_id,
            )
        )
        customer = result.scalars().first()
        assert customer is not None
        assert customer.name == "Quoty McQuote"

    finally:
        if os.path.exists(filename):
            os.remove(filename)


@pytest.mark.asyncio
async def test_import_requests(async_session: AsyncSession):
    business = Business(name="Req Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    user = User(business_id=business.id, email="r@test.com", role=UserRole.OWNER)
    async_session.add(user)
    await async_session.commit()

    service = DataManagementService(async_session)

    filename = "test_requests.csv"
    with open(filename, "w") as f:
        f.write("Name,Details\n")
        f.write("Need Help,Please fix my door\n")

    try:
        job = await service.import_data(
            business.id, filename, "text/csv", entity_type=EntityType.REQUEST
        )

        assert job.status == ImportStatus.COMPLETED

        # Verify Request
        result = await async_session.execute(
            select(Request).where(Request.business_id == business.id)
        )
        requests = result.scalars().all()
        assert len(requests) == 1
        assert requests[0].description == "Please fix my door"

    finally:
        if os.path.exists(filename):
            os.remove(filename)


@pytest.mark.asyncio
async def test_import_expenses(async_session: AsyncSession):
    business = Business(name="Exp Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    user = User(business_id=business.id, email="e@test.com", role=UserRole.OWNER)
    async_session.add(user)
    await async_session.commit()

    service = DataManagementService(async_session)

    filename = "test_expenses.csv"
    with open(filename, "w") as f:
        f.write("Vendor,Total,Category\n")
        f.write("Home Depot,150.25,Material\n")

    try:
        job = await service.import_data(
            business.id, filename, "text/csv", entity_type=EntityType.EXPENSE
        )

        assert job.status == ImportStatus.COMPLETED

        # Verify Expense
        result = await async_session.execute(
            select(Expense).where(Expense.business_id == business.id)
        )
        expenses = result.scalars().all()
        assert len(expenses) == 1
        assert expenses[0].description == "Home Depot"
        assert expenses[0].amount == 150.25
        assert expenses[0].category == ExpenseCategory.MATERIAL

    finally:
        if os.path.exists(filename):
            os.remove(filename)
