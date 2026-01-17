import os
from datetime import datetime
from unittest.mock import MagicMock
from src.services.pdf_generator import InvoicePDFGenerator
from src.models import Job, Customer, LineItem

def generate_debug_invoice():
    # Setup mocks
    mock_customer = MagicMock(spec=Customer)
    mock_customer.name = "Acme Corp"
    mock_customer.phone = "+1 (555) 012-3412"
    mock_customer.street = "456 Enterprise Drive"
    mock_customer.city = "Metropolis"
    mock_customer.country = "USA"

    mock_line_item1 = MagicMock(spec=LineItem)
    mock_line_item1.description = "Kitchen Remodel - Labor"
    mock_line_item1.quantity = 1.0
    mock_line_item1.unit_price = 1200.0
    mock_line_item1.total_price = 1200.0

    mock_line_item2 = MagicMock(spec=LineItem)
    mock_line_item2.description = "Luxury Tiles (sq ft)"
    mock_line_item2.quantity = 50.0
    mock_line_item2.unit_price = 15.0
    mock_line_item2.total_price = 750.0

    mock_job = MagicMock(spec=Job)
    mock_job.id = 998877
    mock_job.customer = mock_customer
    mock_job.line_items = [mock_line_item1, mock_line_item2]
    mock_job.value = 1950.0

    # Initialize generator
    generator = InvoicePDFGenerator()

    # Generate PDF
    print("Generating debug_invoice.pdf...")
    pdf_bytes = generator.generate(mock_job)

    with open("debug_invoice.pdf", "wb") as f:
        f.write(pdf_bytes)
    
    print("Success! debug_invoice.pdf created in current directory.")

if __name__ == "__main__":
    generate_debug_invoice()
