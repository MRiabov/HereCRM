import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.quote_tools import CreateQuoteTool
from src.uimodels import CreateQuoteInput, QuoteLineItemInput

@pytest.mark.asyncio
async def test_create_quote_tool_run():
    # Mock services
    mock_quote_service = AsyncMock()
    # Mock create_quote return value
    # Return a Quote-like object
    mock_quote = MagicMock()
    mock_quote.id = 1
    mock_quote.total_amount = 100.0
    mock_quote_service.create_quote.return_value = mock_quote
    
    # Mock send_quote (even if it doesn't exist on real class, we mocked the service)
    mock_quote_service.send_quote = AsyncMock()

    mock_customer_repo = AsyncMock()
    # Mock search result
    mock_customer = MagicMock()
    mock_customer.id = 10
    mock_customer.name = "Test Customer"
    mock_customer_repo.search.return_value = [mock_customer]

    business_id = 999
    
    tool = CreateQuoteTool(mock_quote_service, mock_customer_repo, business_id)

    input_data = CreateQuoteInput(
        customer_identifier="Test Customer",
        items=[
            QuoteLineItemInput(description="Window Cleaning", quantity=1, price=100.0)
        ]
    )

    result_msg, result_data = await tool.run(input_data)

    # Verify calls
    mock_customer_repo.search.assert_awaited_once_with("Test Customer", business_id)
    mock_quote_service.create_quote.assert_awaited_once()
    mock_quote_service.send_quote.assert_awaited_once_with(1)

    assert "Quote #1 created and sent to Test Customer" in result_msg
    assert result_data["id"] == 1
    assert result_data["action"] == "create_quote"

@pytest.mark.asyncio
async def test_create_quote_tool_customer_not_found():
    mock_quote_service = AsyncMock()
    mock_customer_repo = AsyncMock()
    mock_customer_repo.search.return_value = [] # No results

    tool = CreateQuoteTool(mock_quote_service, mock_customer_repo, 1)
    input_data = CreateQuoteInput(customer_identifier="Unknown", items=[])

    msg, data = await tool.run(input_data)
    assert "Could not find customer" in msg
    assert data is None

@pytest.mark.asyncio
async def test_create_quote_tool_ambiguous_customer():
    mock_quote_service = AsyncMock()
    mock_customer_repo = AsyncMock()
    mock_customer_repo.search.return_value = [MagicMock(), MagicMock()] # Two results

    tool = CreateQuoteTool(mock_quote_service, mock_customer_repo, 1)
    input_data = CreateQuoteInput(customer_identifier="Ambiguous", items=[])

    msg, data = await tool.run(input_data)
    assert "Multiple customers found" in msg
    assert data is None
