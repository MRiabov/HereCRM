import pytest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Customer, Job, JobStatus, Invoice, Business, User, UserRole,InvoiceStatus
from src.services.invoice_service import InvoiceService
from src.tool_executor import ToolExecutor
from src.tools.invoice_tools import SendInvoiceTool

# Mock dependencies
@pytest.fixture
def mock_s3_service(monkeypatch):
    mock = MagicMock()
    mock.upload_file.return_value = "https://s3.example.com/invoice.pdf"
    
    # Patch the class in invoice_service.py so instantiation returns our mock
    mock_class = MagicMock(return_value=mock)
    monkeypatch.setattr("src.services.invoice_service.S3Service", mock_class)
    return mock

@pytest.fixture
def mock_pdf_generator(monkeypatch):
    mock = MagicMock()
    mock.generate_invoice.return_value = b"fake pdf content"
    mock.generate.return_value = b"fake pdf content"
    
    # Patch the class in invoice_service.py so instantiation returns our mock
    mock_class = MagicMock(return_value=mock)
    monkeypatch.setattr("src.services.invoice_service.PDFGenerator", mock_class)
    return mock

@pytest.fixture
def template_service():
    mock = MagicMock()
    mock.render.side_effect = lambda key, **kwargs: f"Rendered {key} {kwargs}" 
    return mock

@pytest.mark.asyncio
async def test_create_invoice_success(session: AsyncSession, mock_s3_service, mock_pdf_generator):
    # Setup
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.flush()
    
    customer = Customer(name="Test Client", business_id=biz.id)
    session.add(customer)
    await session.flush()
    
    job = Job(customer_id=customer.id, business_id=biz.id, description="Test Job", value=100.0, status=JobStatus.COMPLETED)
    session.add(job)
    await session.commit()
    
    service = InvoiceService(session)
    
    # Act
    invoice = await service.create_invoice(job)
    
    # Assert
    assert invoice is not None
    assert invoice.public_url == "https://s3.example.com/invoice.pdf"
    assert invoice.status == InvoiceStatus.GENERATED
    
    # Verify mocks called
    mock_pdf_generator.generate_invoice.assert_called_once()
    mock_s3_service.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_send_invoice_tool_success(session: AsyncSession, mock_s3_service, mock_pdf_generator, template_service):
    # Setup
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.flush()
    
    user = User(business_id=biz.id, name="Admin", role=UserRole.OWNER, phone_number="123")
    session.add(user)
    await session.flush()

    # Setup ToolExecutor
    executor = ToolExecutor(session, business_id=biz.id, user_id=user.id, user_phone="123", template_service=template_service)
    
    # Setup Data
    customer = Customer(name="John Doe", business_id=biz.id, phone="555-1234")
    session.add(customer)
    await session.flush()
    
    job = Job(customer_id=customer.id, business_id=biz.id, description="Roof Repair", value=500.0, status=JobStatus.COMPLETED)
    session.add(job)
    await session.commit()
    
    # Act
    tool = SendInvoiceTool(query="John")
    result, metadata = await executor.execute(tool)
    
    # Assert
    assert "https://s3.example.com/invoice.pdf" in result
    assert metadata["action"] == "invoice_generated"
    assert metadata["url"] == "https://s3.example.com/invoice.pdf"


@pytest.mark.asyncio
async def test_send_invoice_tool_no_job(session: AsyncSession, mock_s3_service, mock_pdf_generator, template_service):
    # Setup
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.flush()
    
    user = User(business_id=biz.id, name="Admin", role=UserRole.OWNER, phone_number="123")
    session.add(user)
    await session.flush()

    # Setup ToolExecutor
    executor = ToolExecutor(session, business_id=biz.id, user_id=user.id, user_phone="123", template_service=template_service)
    
    # Setup Data (Customer but no job)
    customer = Customer(name="Jane Doe", business_id=biz.id)
    session.add(customer)
    await session.commit()
    
    # Act
    tool = SendInvoiceTool(query="Jane")
    result, metadata = await executor.execute(tool)
    
    # Assert
    assert "No jobs found" in result
    assert metadata is None

@pytest.mark.asyncio
async def test_existing_invoice_warning(session: AsyncSession, mock_s3_service, mock_pdf_generator, template_service):
    # Setup
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.flush()
    
    user = User(business_id=biz.id, name="Admin", role=UserRole.OWNER, phone_number="123")
    session.add(user)
    await session.flush()

    # Setup ToolExecutor
    executor = ToolExecutor(session, business_id=biz.id, user_id=user.id, user_phone="123", template_service=template_service)
    
    # Setup Data
    customer = Customer(name="Bob Smith", business_id=biz.id)
    session.add(customer)
    await session.flush()
    
    job = Job(customer_id=customer.id, business_id=biz.id, description="Plumbing", value=200.0, status=JobStatus.COMPLETED)
    session.add(job)
    await session.flush()
    
    # Create existing invoice manually
    existing_invoice = Invoice(job_id=job.id, s3_key="old.pdf", public_url="http://old.com/inv.pdf", status=InvoiceStatus.SENT)
    session.add(existing_invoice)
    await session.commit()
    
    # Act 1: force_regenerate = False
    tool = SendInvoiceTool(query="Bob")
    result, metadata = await executor.execute(tool)
    
    # Assert 1: Should return existing
    assert "http://old.com/inv.pdf" in result
    # Mocks of generation/upload should NOT be called (only looked up)
    mock_pdf_generator.generate.assert_not_called()
    mock_s3_service.upload_file.assert_not_called()
    
    # Act 2: force_regenerate = True
    tool_force = SendInvoiceTool(query="Bob", force_regenerate=True)
    result_force, metadata_force = await executor.execute(tool_force)
    
    # Assert 2: Should generate new
    assert "https://s3.example.com/invoice.pdf" in result_force
    mock_pdf_generator.generate_invoice.assert_called()
    mock_s3_service.upload_file.assert_called()
