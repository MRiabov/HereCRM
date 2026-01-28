import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.whatsapp_service import WhatsappService
from src.uimodels import CreateQuoteTool, QuoteLineItemInput, ScheduleJobTool, AddRequestTool
from src.tools.invoice_tools import SendInvoiceTool
from src.models import User, Customer
from src.services.template_service import TemplateService

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def mock_parser():
    return MagicMock()

@pytest.fixture
def template_service():
    return TemplateService()

@pytest.fixture
def whatsapp_service(mock_session, mock_parser, template_service):
    return WhatsappService(mock_session, mock_parser, template_service)

@pytest.mark.asyncio
async def test_generate_summary_quote(whatsapp_service, mock_session):
    # Setup
    user = User(id=1, business_id=10)
    tool = CreateQuoteTool(
        customer_identifier="Margaret",
        items=[
            QuoteLineItemInput(description="fixing leaky sink", quantity=1, price=50.0)
        ]
    )
    
    mock_customer = Customer(id=1, name="Margaret", phone="1234567890", street="123 Main St")
    
    with MagicMock() as mock_repo_class:
        with MagicMock() as mock_repo_instance:
            import src.services.chat.utils.summary_generator
            src.services.chat.utils.summary_generator.CustomerRepository = mock_repo_class
            mock_repo_class.return_value = mock_repo_instance
            mock_repo_instance.search = AsyncMock(return_value=[mock_customer])
            
            summary = await whatsapp_service.summary_generator.generate_summary(tool, user)
            
            assert "Margaret" in summary
            assert "1234567890" in summary
            assert "123 Main St" in summary
            assert "fixing leaky sink" in summary
            assert "$50.00" in summary

@pytest.mark.asyncio
async def test_generate_summary_schedule(whatsapp_service, mock_session):
    # Setup
    user = User(id=1, business_id=10)
    tool = ScheduleJobTool(
        customer_query="John Doe",
        time="tomorrow at 2pm"
    )
    
    mock_customer = Customer(id=2, name="John Doe", phone="0987654321", street="456 Oak Ave")
    
    with MagicMock() as mock_repo_class:
        with MagicMock() as mock_repo_instance:
            import src.services.chat.utils.summary_generator
            src.services.chat.utils.summary_generator.CustomerRepository = mock_repo_class
            mock_repo_class.return_value = mock_repo_instance
            mock_repo_instance.search = AsyncMock(return_value=[mock_customer])
            
            summary = await whatsapp_service.summary_generator.generate_summary(tool, user)
            
            assert "John Doe" in summary
            assert "0987654321" in summary
            assert "456 Oak Ave" in summary
            assert "tomorrow at 2pm" in summary

@pytest.mark.asyncio
async def test_generate_summary_request(whatsapp_service, mock_session):
    # Setup
    user = User(id=1, business_id=10)
    tool = AddRequestTool(
        customer_name="Alice",
        description="Call back later",
        time="anytime"
    )
    
    mock_customer = Customer(id=3, name="Alice", phone="5551234", street="789 Pine Rd")
    
    with MagicMock() as mock_repo_class:
        with MagicMock() as mock_repo_instance:
            import src.services.chat.utils.summary_generator
            src.services.chat.utils.summary_generator.CustomerRepository = mock_repo_class
            mock_repo_class.return_value = mock_repo_instance
            mock_repo_instance.search = AsyncMock(return_value=[mock_customer])
            
            summary = await whatsapp_service.summary_generator.generate_summary(tool, user)
            
            assert "Alice" in summary
            assert "5551234" in summary
            assert "Call back later" in summary

@pytest.mark.asyncio
async def test_generate_summary_quote_no_contact(whatsapp_service, mock_session):
    # Setup
    user = User(id=1, business_id=10)
    tool = CreateQuoteTool(
        customer_identifier="Margaret",
        items=[
            QuoteLineItemInput(description="fixing leaky sink", quantity=1, price=50.0)
        ]
    )
    
    mock_customer = Customer(id=1, name="Margaret", phone=None, email=None, street="123 Main St")
    
    with MagicMock() as mock_repo_class:
        with MagicMock() as mock_repo_instance:
            import src.services.chat.utils.summary_generator
            src.services.chat.utils.summary_generator.CustomerRepository = mock_repo_class
            mock_repo_class.return_value = mock_repo_instance
            mock_repo_instance.search = AsyncMock(return_value=[mock_customer])
            
            summary = await whatsapp_service.summary_generator.generate_summary(tool, user)
            
            assert "Warning: could not find a contact detail to send the quote" in summary
            assert "Generate the quote without sending?" in summary

@pytest.mark.asyncio
async def test_generate_summary_invoice_no_contact(whatsapp_service, mock_session):
    # Setup
    user = User(id=1, business_id=10)
    tool = SendInvoiceTool(
        query="John Smith"
    )
    
    mock_customer = Customer(id=4, name="John Smith", phone=None, email=None, street="789 Blvd")
    
    with MagicMock() as mock_repo_class:
        with MagicMock() as mock_repo_instance:
            import src.services.chat.utils.summary_generator
            src.services.chat.utils.summary_generator.CustomerRepository = mock_repo_class
            mock_repo_class.return_value = mock_repo_instance
            mock_repo_instance.search = AsyncMock(return_value=[mock_customer])
            
            summary = await whatsapp_service.summary_generator.generate_summary(tool, user)
            
            assert "Generate and send invoice to John Smith" in summary
            assert "789 Blvd" in summary
            assert "Warning: could not find a contact detail to send the invoice" in summary
