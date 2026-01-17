import pytest
from datetime import datetime
from unittest.mock import MagicMock
from src.services.pdf_generator import InvoicePDFGenerator
from src.models import Job, Customer, LineItem

def test_invoice_pdf_generation():
    # Setup mocks
    mock_customer = MagicMock(spec=Customer)
    mock_customer.name = "John Doe"
    mock_customer.phone = "+123456789"
    mock_customer.street = "123 Main St"
    mock_customer.city = "Testville"
    mock_customer.country = "USA"

    mock_line_item1 = MagicMock(spec=LineItem)
    mock_line_item1.description = "Test Service 1"
    mock_line_item1.quantity = 2.0
    mock_line_item1.unit_price = 50.0
    mock_line_item1.total_price = 100.0

    mock_line_item2 = MagicMock(spec=LineItem)
    mock_line_item2.description = "Test Service 2"
    mock_line_item2.quantity = 1.0
    mock_line_item2.unit_price = 75.0
    mock_line_item2.total_price = 75.0

    mock_job = MagicMock(spec=Job)
    mock_job.id = 12345
    mock_job.customer = mock_customer
    mock_job.line_items = [mock_line_item1, mock_line_item2]
    mock_job.value = 175.0

    # Initialize generator
    generator = InvoicePDFGenerator()

    # Generate PDF
    pdf_bytes = generator.generate(mock_job)

    # Assertions
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF-")

def test_invoice_pdf_generation_with_date():
    # Setup mocks
    mock_customer = MagicMock(spec=Customer)
    mock_customer.name = "Jane Smith"
    mock_customer.street = None
    mock_customer.city = None
    mock_customer.country = None
    mock_customer.phone = None

    mock_job = MagicMock(spec=Job)
    mock_job.id = 67890
    mock_job.customer = mock_customer
    mock_job.line_items = []
    mock_job.value = 0.0

    generator = InvoicePDFGenerator()
    test_date = datetime(2025, 12, 25)
    
    pdf_bytes = generator.generate(mock_job, invoice_date=test_date)

    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF-")
