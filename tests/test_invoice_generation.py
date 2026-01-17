import pytest
import io
from datetime import datetime
from unittest.mock import MagicMock
from src.services.pdf_generator import InvoicePDFGenerator
from src.models import Job, Customer, LineItem, Business
from pdfminer.high_level import extract_text

def test_invoice_pdf_generation():
    # Setup mocks
    mock_business = MagicMock(spec=Business)
    mock_business.name = "Test Business"

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
    mock_job.business = mock_business
    mock_job.customer = mock_customer
    mock_job.line_items = [mock_line_item1, mock_line_item2]
    mock_job.value = 175.0
    # Description needed for scope section
    mock_job.description = "Scope of work test content"
    mock_job.status = "pending"

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
    mock_business = MagicMock(spec=Business)
    mock_business.name = "Test Business"

    mock_customer = MagicMock(spec=Customer)
    mock_customer.name = "Jane Smith"
    mock_customer.street = None
    mock_customer.city = None
    mock_customer.country = None
    mock_customer.phone = None

    mock_job = MagicMock(spec=Job)
    mock_job.id = 67890
    mock_job.business = mock_business
    mock_job.customer = mock_customer
    mock_job.line_items = []
    mock_job.value = 0.0
    mock_job.description = None
    mock_job.status = None

    generator = InvoicePDFGenerator()
    test_date = datetime(2025, 12, 25)
    
    pdf_bytes = generator.generate(mock_job, invoice_date=test_date)

    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF-")

def test_invoice_pdf_content_validation():
    """
    Validates that the generated PDF actually contains the expected user data
    using PDF text extraction.
    """
    # Setup Data
    mock_business = MagicMock(spec=Business)
    mock_business.name = "Acme Provider Inc"

    mock_customer = MagicMock(spec=Customer)
    mock_customer.name = "Target Customer LLC"
    mock_customer.phone = "+1-555-0199"
    mock_customer.street = "999 Target Way"
    mock_customer.city = "Bullseye"
    mock_customer.country = "Canada"

    mock_line_item = MagicMock(spec=LineItem)
    mock_line_item.description = "Premium Consultation"
    mock_line_item.quantity = 10.0
    mock_line_item.unit_price = 150.00
    mock_line_item.total_price = 1500.00

    mock_job = MagicMock(spec=Job)
    mock_job.id = 555001
    mock_job.business = mock_business
    mock_job.customer = mock_customer
    mock_job.line_items = [mock_line_item]
    mock_job.value = 1500.00
    mock_job.description = "Detailed analysis of business requirements."
    mock_job.status = "approved"

    generator = InvoicePDFGenerator()
    invoice_date = datetime(2026, 5, 20)

    # Generate PDF
    pdf_bytes = generator.generate(mock_job, invoice_date=invoice_date)

    # Extract text using pdfminer
    text = extract_text(io.BytesIO(pdf_bytes))

    # Assertions
    # 1. Check Invoice Details
    assert "INVOICE" in text
    assert "#555001" in text
    assert "Approved" in text
    assert "2026-05-20" in text # Invoice Date

    # 2. Check Customer Details
    assert "Target Customer LLC" in text
    assert "999 Target Way" in text
    assert "Bullseye" in text
    assert "Canada" in text

    # 3. Check Line Item Details
    assert "Premium Consultation" in text
    assert "10.00" in text # Quantity formatted
    assert "150.00" in text # Price formatted
    assert "1500.00" in text # Total formatted

    # 4. Check Business Name
    assert "Acme Provider Inc" in text

    # 5. Check Scope/Description
    assert "Detailed analysis of business requirements" in text

    # 6. Check Total
    assert "1500.00" in text
