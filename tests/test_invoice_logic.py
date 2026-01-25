import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.services.invoice_service import InvoiceService
from src.models import Job, Invoice, Customer
from src.tools.invoice_tools import SendInvoiceTool
from src.tool_executor import ToolExecutor

@pytest.fixture
def mock_session():
    session = AsyncMock()
    # add and delete are synchronous in SQLAlchemy AsyncSession
    session.add = MagicMock()
    session.delete = MagicMock()
    return session

@pytest.fixture
def mock_s3_service():
    with patch("src.services.invoice_service.S3Service") as mock:
        yield mock.return_value

@pytest.fixture
def mock_pdf_generator():
    with patch("src.services.invoice_service.PDFGenerator") as mock:
        yield mock.return_value

@pytest.mark.asyncio
async def test_invoice_service_create(mock_session, mock_s3_service, mock_pdf_generator):
    service = InvoiceService(mock_session)
    job = Job(id=1, description="Test Job", value=100.0)
    
    # Setup mocks
    mock_pdf_generator.generate_invoice.return_value = b"%PDF-mock"
    mock_s3_service.upload_file.return_value = "https://s3.example.com/invoice.pdf"
    
    # Mock existing invoice check to return None
    # We need to explicitly return a MagicMock (not AsyncMock) for the result
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    # Execute
    invoice = await service.create_invoice(job)
    
    # Verify
    mock_pdf_generator.generate_invoice.assert_called_once_with(job, payment_link=None)
    mock_s3_service.upload_file.assert_called_once()
    assert invoice.job_id == 1
    assert invoice.public_url == "https://s3.example.com/invoice.pdf"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()

@pytest.mark.asyncio
async def test_invoice_service_existing(mock_session, mock_s3_service, mock_pdf_generator):
    service = InvoiceService(mock_session)
    job = Job(id=1)
    existing_invoice = Invoice(id=10, job_id=1, public_url="https://existing.url")
    
    # Mock existing invoice check
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_invoice
    mock_session.execute.return_value = mock_result

    # Execute without force
    invoice = await service.create_invoice(job, force_regenerate=False)
    
    # Verify we got existing back and NO generation happened
    assert invoice == existing_invoice
    mock_pdf_generator.generate_invoice.assert_not_called()
    mock_s3_service.upload_file.assert_not_called()

@pytest.mark.asyncio
async def test_invoice_service_force_regenerate(mock_session, mock_s3_service, mock_pdf_generator):
    service = InvoiceService(mock_session)
    job = Job(id=1)
    existing_invoice = Invoice(id=10, job_id=1)
    
    # Mock result
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_invoice
    mock_session.execute.return_value = mock_result
    
    mock_pdf_generator.generate_invoice.return_value = b"%PDF"
    mock_s3_service.upload_file.return_value = "https://new.url"

    # Execute WITH force
    invoice = await service.create_invoice(job, force_regenerate=True)
    
    # Verify generation happened
    mock_pdf_generator.generate_invoice.assert_called_once()
    assert invoice.public_url == "https://new.url"
    mock_session.add.assert_called_once()

@pytest.mark.asyncio
async def test_tool_executor_send_invoice(mock_session, mock_s3_service):
    # Setup Executor dependencies
    mock_template_service = MagicMock()
    # ToolExecutor(session, business_id, user_id, user_phone, template_service)
    executor = ToolExecutor(mock_session, 1, 1, "555555", mock_template_service)
    
    # Mock repositories (via direct attribute access/patch on instance would be better, but executor creates them in __init__)
    # So we need to patch the classes used in ToolExecutor __init__ OR set them after init.
    # It's easier to mock the attributes on the executor instance since we already have it.
    
    executor.customer_repo = AsyncMock()
    executor.job_repo = AsyncMock()
    executor.invoice_service = AsyncMock()
    
    # Test Data
    tool = SendInvoiceTool(query="John")
    customer = Customer(id=5, name="John Doe", phone="555")
    job = Job(id=50)
    invoice = Invoice(id=99, public_url="https://invoice.url")
    
    executor.customer_repo.search.return_value = [customer]
    executor.job_repo.get_most_recent_by_customer.return_value = job
    executor.invoice_service.create_invoice.return_value = invoice
    
    # Execute
    message, metadata = await executor._execute_send_invoice(tool)
    
    # Verify
    assert "https://invoice.url" in message
    assert metadata["action"] == "invoice_generated"
    assert metadata["url"] == "https://invoice.url"
    
    executor.customer_repo.search.assert_awaited_with("John", 1)
    executor.job_repo.get_most_recent_by_customer.assert_awaited_with(5, 1)
    executor.invoice_service.create_invoice.assert_awaited_with(job, force_regenerate=False)
