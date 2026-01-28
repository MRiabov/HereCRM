from src.models import JobStatus
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.whatsapp_service import WhatsappService
from src.models import User, ConversationState, ConversationStatus
from src.uimodels import ExportQueryTool, ExitDataManagementTool
from src.services.template_service import TemplateService

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_parser():
    parser = AsyncMock()
    # Default behavior: return None or string for standard parse
    parser.parse.return_value = None
    return parser

@pytest.fixture
def mock_template_service():
    service = MagicMock(spec=TemplateService)
    service.render.side_effect = lambda key, **kwargs: f"TEMPLATE:{key}"
    return service

@pytest.fixture
def service(mock_session, mock_parser, mock_template_service):
    # We will patch DataManagementService inside tests or here
    with patch("src.services.whatsapp_service.DataManagementService") as MockDataService:
        svc = WhatsappService(mock_session, mock_parser, mock_template_service)
        # Mock the instance created inside __init__
        svc.data_service = AsyncMock()
        # Update the handler's reference to the data service
        svc.data_management_handler.data_service = svc.data_service
        return svc

@pytest.mark.asyncio
async def test_enter_data_management_mode(service):
    user = User(phone_number="123", business_id=1)
    state = ConversationState(user_id=123, state=ConversationStatus.IDLE)

    response = await service.idle_handler.handle(user, state, "manage data")

    assert state.state == ConversationStatus.DATA_MANAGEMENT
    assert "Data Management mode" in response

@pytest.mark.asyncio
async def test_data_management_export(service, mock_parser):
    user = User(phone_number="123", business_id=1)
    state = ConversationState(user_id=123, state=ConversationStatus.DATA_MANAGEMENT)

    # Mock LLM to return ExportQueryTool
    mock_parser.parse_data_management.return_value = ExportQueryTool(query="all customers", format="csv")

    # Mock Data Service return
    mock_export_req = MagicMock()
    mock_export_req.status = "COMPLETED"
    mock_export_req.public_url = "http://test.com/export.csv"
    service.data_service.export_data.return_value = mock_export_req

    response = await service.data_management_handler.handle(user, state, "export all customers")

    service.data_service.export_data.assert_called_once_with(1, "all customers", "csv", filters={})
    assert "Export completed" in response
    assert "http://test.com/export.csv" in response

@pytest.mark.asyncio
async def test_data_management_export_filtered(service, mock_parser):
    user = User(phone_number="123", business_id=1)
    state = ConversationState(user_id=123, state=ConversationStatus.DATA_MANAGEMENT)

    # Mock tool to return filters
    tool = ExportQueryTool(query="jobs", format="excel", entity_type="job", status="PENDING")
    mock_parser.parse_data_management.return_value = tool

    # Mock Data Service
    mock_export_req = MagicMock()
    mock_export_req.status = "PROCESSING"
    service.data_service.export_data.return_value = mock_export_req

    response = await service.data_management_handler.handle(user, state, "export pending jobs")

    service.data_service.export_data.assert_called_once_with(
        1, "jobs", "excel", filters={"entity_type": "job", "status": JobStatus.PENDING.name}
    )
    assert "Export processing" in response

@pytest.mark.asyncio
async def test_data_management_import(service):
    user = User(phone_number="123", business_id=1)
    state = ConversationState(user_id=123, state=ConversationStatus.DATA_MANAGEMENT)

    # Mock Data Service return
    mock_import_job = MagicMock()
    mock_import_job.status = "COMPLETED"
    mock_import_job.record_count = 10
    mock_import_job.error_log = []
    service.data_service.import_data.return_value = mock_import_job

    # Simulate media message
    response = await service.data_management_handler.handle(
        user, state, "", media_url="http://file.com/data.csv", media_type="text/csv"
    )

    service.data_service.import_data.assert_called_once_with(1, "http://file.com/data.csv", "text/csv")
    assert "Import started" in response
    assert "10 records processed" in response

@pytest.mark.asyncio
async def test_exit_data_management(service, mock_parser):
    user = User(phone_number="123", business_id=1)
    state = ConversationState(user_id=123, state=ConversationStatus.DATA_MANAGEMENT)

    # Mock LLM to return ExitDataManagementTool
    mock_parser.parse_data_management.return_value = ExitDataManagementTool()

    response = await service.data_management_handler.handle(user, state, "exit")

    assert state.state == ConversationStatus.IDLE
    assert "TEMPLATE:welcome_back" in response
