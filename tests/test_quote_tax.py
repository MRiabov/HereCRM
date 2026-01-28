import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.quote_service import QuoteService
from src.models import Quote, Business, QuoteStatus, QuoteLineItem, Job
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.tax_calculator import tax_calculator

@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    # Mock get
    session.get = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_create_quote_calculates_tax_added(mock_session):
    """
    Test that creating a quote calculates tax correctly (Tax Added).
    """
    # Setup
    quote_service = QuoteService(mock_session)
    business_id = 1
    customer_id = 101

    # Mock Business
    business = Business(id=business_id, workflow_tax_inclusive=False, name="Test Biz")
    mock_session.get.side_effect = lambda model, id: business if model == Business else None

    # Set default tax rate for test
    tax_calculator.default_tax_rate = 0.10 # 10%

    # Define lines
    lines = [
        {"description": "Service A", "quantity": 1, "unit_price": 100.0},
        {"description": "Service B", "quantity": 2, "unit_price": 50.0}
    ]
    # Raw Total = 200
    # Subtotal = 200
    # Tax = 20
    # Total = 220

    # Run
    quote = await quote_service.create_quote(customer_id, business_id, lines)

    # Assertions
    assert quote.subtotal == 200.0
    assert quote.tax_amount == 20.0
    assert quote.total_amount == 220.0
    assert quote.tax_rate == 0.10

@pytest.mark.asyncio
async def test_create_quote_calculates_tax_inclusive(mock_session):
    """
    Test that creating a quote calculates tax correctly (Tax Inclusive).
    """
    # Setup
    quote_service = QuoteService(mock_session)
    business_id = 1
    customer_id = 101

    # Mock Business
    business = Business(id=business_id, workflow_tax_inclusive=True, name="Test Biz")
    mock_session.get.side_effect = lambda model, id: business if model == Business else None

    # Set default tax rate for test
    tax_calculator.default_tax_rate = 0.10 # 10%

    # Define lines
    lines = [
        {"description": "Service A", "quantity": 1, "unit_price": 110.0}
    ]
    # Raw Total = 110 (which is Total Amount)
    # Subtotal = 110 / 1.1 = 100
    # Tax = 10

    # Run
    quote = await quote_service.create_quote(customer_id, business_id, lines)

    # Assertions
    assert quote.total_amount == 110.0
    assert quote.subtotal == 100.0
    assert quote.tax_amount == 10.0
    assert quote.tax_rate == 0.10

@pytest.mark.asyncio
async def test_confirm_quote_transfers_tax_to_job(mock_session):
    """
    Test that confirming a quote creates a job with preserved tax info.
    """
    quote_service = QuoteService(mock_session)

    # Setup existing quote
    quote = Quote(
        id=1,
        business_id=1,
        customer_id=101,
        status=QuoteStatus.SENT,
        external_token="abc",
        subtotal=100.0,
        tax_amount=10.0,
        tax_rate=0.10,
        total_amount=110.0,
        items=[QuoteLineItem(description="Item", quantity=1, unit_price=100.0, total=100.0)]
    )

    # Mock Select execution for confirm_quote
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = quote
    mock_session.execute.return_value = mock_result

    # Run
    await quote_service.confirm_quote("abc")

    # Assert
    # Inspect mock_session.add calls to find the Job
    job_found = False
    for call in mock_session.add.call_args_list:
        obj = call.args[0]
        if isinstance(obj, Job):
            job_found = True
            assert obj.subtotal == 100.0
            assert obj.tax_amount == 10.0
            assert obj.tax_rate == 0.10
            assert obj.value == 110.0
            break

    assert job_found, "Job was not added to session"
