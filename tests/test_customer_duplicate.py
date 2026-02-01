import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import MultipleResultsFound
from src.repositories import CustomerRepository
from src.models import Customer
from src.tool_executor import ToolExecutor
from src.uimodels import AddLeadTool

@pytest.mark.asyncio
async def test_get_by_name_handles_duplicates():
    """Verify that get_by_name returns the first result if multiple customers have the same name."""
    session = AsyncMock()
    repo = CustomerRepository(session)

    # Mock session.execute to return two customers
    c1 = Customer(id=1, name="Unknown")
    c2 = Customer(id=2, name="Unknown")

    # Mock the result object for SQLAlchemy 1.4/2.0
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = c1

    session.execute.return_value = mock_result

    result = await repo.get_by_name("Unknown", 1)
    assert result == c1

@pytest.mark.asyncio
async def test_add_lead_allows_unknown_if_phone_differs():
    """Verify that AddLeadTool allows adding a second 'Unknown' lead if the phone number is different."""

    session = AsyncMock()
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = MagicMock(role="OWNER")

    executor = ToolExecutor(session, 1, 1, "123", MagicMock())
    executor.user_repo = user_repo
    executor.customer_repo = AsyncMock()
    executor.geocoding_service = MagicMock()
    executor.geocoding_service.geocode = AsyncMock(return_value=(None, None, None, None, None, None, None))
    executor.template_service = MagicMock()
    executor.template_service.render.return_value = "Lead Created"

    # Mock get_by_name to return an existing "Unknown" customer
    # Ideally get_by_name shouldn't be called for "Unknown" but if it is, we want to ensure logic handles it.
    # With the fix, get_by_name should NOT be called.

    existing_customer = Customer(id=1, name="Unknown", phone="+1111111111")
    executor.customer_repo.get_by_name.return_value = existing_customer
    executor.customer_repo.get_by_phone.return_value = None # Different phone, so no phone collision

    # Try to add another lead with empty name (defaults to Unknown) and different phone
    tool = AddLeadTool(name="Unknown", phone="+2222222222")

    result, data = await executor.execute(tool)

    # Verify we didn't get blocked
    assert "Note: Customer 'Unknown' already exists." not in result
    assert "Lead Created" in result
    assert data["action"] == "create"

    # Verify get_by_name was NOT called (or if called, logic ignored it)
    # The code says: if name != "Unknown": get_by_name
    # So it should NOT be called.
    executor.customer_repo.get_by_name.assert_not_called()
