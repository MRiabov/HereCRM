import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.services.quote_service import QuoteService
from src.models import Quote, Customer, Business, QuoteStatus, QuoteLineItem

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def mock_s3_service():
    with patch("src.services.quote_service.S3Service") as mock:
        yield mock.return_value

@pytest.fixture
def mock_pdf_generator():
    with patch("src.services.quote_service.PDFGenerator") as mock:
        yield mock.return_value

@pytest.mark.asyncio
async def test_send_quote_success(mock_session, mock_s3_service, mock_pdf_generator):
    service = QuoteService(mock_session)

    # Setup Data
    quote = Quote(
        id=123,
        customer_id=456,
        business_id=789,
        status=QuoteStatus.DRAFT,
        total_amount=500.0,
        items=[QuoteLineItem(description="Test Item", quantity=1, unit_price=500.0, total=500.0)]
    )
    quote.customer = Customer(name="Test Customer")
    quote.business = Business(name="Test Business")

    # Mock get_quote
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = quote
    mock_session.execute.return_value = mock_result

    # Mock PDF generation and upload
    mock_pdf_generator.generate_quote.return_value = b"%PDF-QUOTE"
    mock_s3_service.upload_file.return_value = "https://s3.example.com/quote.pdf"

    # Act
    await service.send_quote(123)

    # Assert
    mock_pdf_generator.generate_quote.assert_called_once_with(quote)
    mock_s3_service.upload_file.assert_called_once()

    assert quote.blob_url == "https://s3.example.com/quote.pdf"
    assert quote.status == QuoteStatus.SENT

    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(quote)

@pytest.mark.asyncio
async def test_send_quote_pdf_failure(mock_session, mock_s3_service, mock_pdf_generator):
    service = QuoteService(mock_session)
    quote = Quote(id=123, customer_id=456, status=QuoteStatus.DRAFT)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = quote
    mock_session.execute.return_value = mock_result

    # Mock failure
    mock_pdf_generator.generate_quote.side_effect = RuntimeError("PDF Gen Failed")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to process quote PDF"):
        await service.send_quote(123)

    assert quote.status == QuoteStatus.DRAFT # Should not change status
    mock_s3_service.upload_file.assert_not_called()
    mock_session.commit.assert_not_called()
