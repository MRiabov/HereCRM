import pytest
from unittest.mock import MagicMock
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


def test_add_job_summary_done(service):
    tool = AddJobTool(
        customer_name="John",
        customer_phone="0861234567",
        location="Barrack Street 67",
        price=50.0,
        description="Fix leak",
        status="done",
    )
    summary = service._generate_summary(tool)
    assert "Status: Done" in summary
    assert "Name: John" in summary
    assert "Phone: 0861234567" in summary
    assert "Value: 50" in summary


def test_schedule_job_summary(service):
    tool = ScheduleJobTool(
        customer_query="John", time="tomorrow at 10am", job_id=None, iso_time=None
    )
    summary = service._generate_summary(tool)
    assert "Schedule Job:" in summary
    assert "Client details:" in summary
    assert "Name: John" in summary
    assert "Time: tomorrow at 10am" in summary


def test_lead_summary(service):
    # Now using AddLeadTool as intended for leads/customers without jobs
    tool = AddLeadTool(
        name="Mary",
        phone="0879998888",
        location="Main St 1",
        details="Interested in quote",
    )
    summary = service._generate_summary(tool)
    assert "Lead details:" in summary
    assert "Name: Mary" in summary
    assert "Phone: 0879998888" in summary
    assert "Address: Main St 1" in summary
    assert "Description: Interested in quote" in summary
    assert "Status:" not in summary
    assert "Value:" not in summary


def test_request_summary(service):
    tool = AddRequestTool(
        content="Call John tomorrow", customer_name="John", customer_phone="0861234567"
    )
    summary = service._generate_summary(tool)
    assert "Request details:" in summary
    assert "Client details:" in summary
    assert "Name: John" in summary
    assert "Phone: 0861234567" in summary
    assert "Content: Call John tomorrow" in summary


def test_request_summary_with_time(service):
    tool = AddRequestTool(
        content="Call John tomorrow", customer_name="John", time="Tomorrow"
    )
    summary = service._generate_summary(tool)
    assert "Time: Tomorrow" in summary
