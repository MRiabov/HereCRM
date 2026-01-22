import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.services.invoice_service import InvoiceService
from src.models import Job, Invoice, Customer, Business
from src.tools.invoice_tools import SendInvoiceTool
from src.tool_executor import ToolExecutor

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session

@pytest.fixture
def mock_s3_service():
    with patch("src.services.invoice_service.S3Service") as mock:
        yield mock.return_value

@pytest.fixture
def mock_pdf_generator():
    with patch("src.services.invoice_service.InvoicePDFGenerator") as mock:
        yield mock.return_value

@pytest.mark.asyncio
async def test_invoice_service_captures_payment_link(mock_session, mock_s3_service, mock_pdf_generator):
    service = InvoiceService(mock_session)
    business = Business(id=1, name="Test Biz", payment_link="https://pay.me/test")
    job = Job(id=1, business_id=1, business=business, description="Test Job", value=100.0)
    
    # Setup mocks
    mock_pdf_generator.generate.return_value = b"%PDF-mock"
    mock_s3_service.upload_file.return_value = "https://s3.example.com/invoice.pdf"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    # Execute
    invoice = await service.create_invoice(job)
    
    # Verify snapshot
    assert invoice.payment_link == "https://pay.me/test"
    # Verify passed to generator
    mock_pdf_generator.generate.assert_called_once()
    args, kwargs = mock_pdf_generator.generate.call_args
    assert kwargs["payment_link"] == "https://pay.me/test"

@pytest.mark.asyncio
async def test_tool_executor_appends_payment_link(mock_session):
    mock_template_service = MagicMock()
    executor = ToolExecutor(mock_session, 1, 1, "555555", mock_template_service)
    
    executor.customer_repo = AsyncMock()
    executor.job_repo = AsyncMock()
    executor.invoice_service = AsyncMock()
    
    # Test Data
    tool = SendInvoiceTool(query="John")
    customer = Customer(id=5, name="John Doe", phone="555")
    job = Job(id=50)
    invoice = Invoice(id=99, public_url="https://invoice.url", payment_link="https://pay.me/john")
    
    executor.customer_repo.search.return_value = [customer]
    executor.job_repo.get_most_recent_by_customer.return_value = job
    executor.invoice_service.create_invoice.return_value = invoice
    
    # Execute
    message, metadata = await executor._execute_send_invoice(tool)
    
    # Verify message contains payment link
    assert "https://invoice.url" in message
    assert "Pay here: https://pay.me/john" in message
    assert metadata["payment_link"] == "https://pay.me/john"

@pytest.mark.asyncio
async def test_pdf_generator_includes_payment_link():
    from src.services.pdf_generator import InvoicePDFGenerator
    
    # We mock the environment to return a template that we can check
    with patch("src.services.pdf_generator.Environment") as mock_env_cls:
        mock_env = mock_env_cls.return_value
        mock_template = MagicMock()
        mock_env.get_template.return_value = mock_template
        
        # HTML output mock
        mock_template.render.return_value = "<html>Pay Now button here</html>"
        
        with patch("src.services.pdf_generator.HTML") as mock_html_cls:
            mock_html = mock_html_cls.return_value
            mock_html.write_pdf.return_value = b"PDF_BYTES"
            
            generator = InvoicePDFGenerator()
            job = Job(id=1)
            
            generator.generate(job, payment_link="https://pay.link")
            
            # Verify context passed to render
            args, kwargs = mock_template.render.call_args
            assert kwargs["payment_link"] == "https://pay.link"
