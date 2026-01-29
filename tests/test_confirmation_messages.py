import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.whatsapp_service import WhatsappService
from src.uimodels import AddJobTool, AddLeadTool, ScheduleJobTool, AddRequestTool
from src.services.template_service import TemplateService


@pytest.fixture
def mock_template_service():
    return TemplateService()


@pytest.fixture
def service(mock_template_service):
    session = MagicMock()
    parser = MagicMock()
    return WhatsappService(session, parser, mock_template_service)


@pytest.fixture
def mock_user():
    return MagicMock(id=1, business_id=1, phone_number="+353861234567")


@pytest.mark.asyncio
async def test_add_job_summary_done(service, mock_user):
    tool = AddJobTool(
        customer_name="John",
        customer_phone="+353861234567",
        location="Barrack Street 67",
        price=50.0,
        description="Fix leak",
        status="COMPLETED",
    )
    # Replaced service._generate_summary with service.summary_generator.generate_summary
    summary = await service.summary_generator.generate_summary(tool, mock_user)
    assert "Completed" in summary
    assert "John" in summary
    assert "353861234567" in summary
    assert "50" in summary


@pytest.mark.asyncio
async def test_schedule_job_summary(service, mock_user):
    tool = ScheduleJobTool(
        customer_query="John", time="tomorrow at 10am", job_id=None, iso_time=None
    )
    # Mock customer search
    with patch(
        "src.repositories.CustomerRepository.search", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = []
        summary = await service.summary_generator.generate_summary(tool, mock_user)
        assert "Schedule" in summary or "Job" in summary  # Check for title
        assert "John" in summary
        assert "tomorrow at 10am" in summary


@pytest.mark.asyncio
async def test_lead_summary(service, mock_user):
    # Now using AddLeadTool as intended for leads/customers without jobs
    tool = AddLeadTool(
        name="Mary",
        phone="+353879998888",
        location="Main St 1",
        details="Interested in quote",
    )
    summary = await service.summary_generator.generate_summary(tool, mock_user)
    assert "Lead" in summary
    assert "Mary" in summary
    assert "353879998888" in summary
    assert "Main St 1" in summary
    assert "Interested in quote" in summary
    assert "Status:" not in summary
    assert "Value:" not in summary


@pytest.mark.asyncio
async def test_request_summary(service, mock_user):
    tool = AddRequestTool(
        description="Call John tomorrow",
        customer_name="John",
        customer_phone="+353861234567",
    )
    # Mock customer search
    with patch(
        "src.repositories.CustomerRepository.search", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = []
        summary = await service.summary_generator.generate_summary(tool, mock_user)
        assert "Request" in summary
        assert "John" in summary
        assert "353861234567" in summary
        # Depending on template it might still say Content or Description. Check WhatsappService handles variable name?
        # The template receives "content=description". Inspecting src/services/templates/request_summary.jinja2 isn't possible easily.
        # But commonly the key passed to render is what is used.
        # If I passed content=tool_call.description, template uses {{content}}.
        # So "Content:" in summary might still be valid if template hardcodes "Content: {{content}}".
        assert "Call John tomorrow" in summary


@pytest.mark.asyncio
async def test_request_summary_with_time(service, mock_user):
    tool = AddRequestTool(
        description="Call John tomorrow", customer_name="John", time="Tomorrow"
    )
    # Mock customer search
    with patch(
        "src.repositories.CustomerRepository.search", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = []
        summary = await service.summary_generator.generate_summary(tool, mock_user)
        assert "Tomorrow" in summary
