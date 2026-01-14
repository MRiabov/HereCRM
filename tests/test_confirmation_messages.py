import pytest
from unittest.mock import MagicMock
from src.services.whatsapp_service import WhatsappService
from src.uimodels import AddJobTool, ScheduleJobTool
from src.services.template_service import TemplateService


@pytest.fixture
def mock_template_service():
    # We use a real TemplateService if possible to test the yaml rendering,
    # but for simplicity let's assume we can use the real one if we mock the file loading
    # or just use the logic in WhatsappService calling render.
    # Actually, let's use a real TemplateService with the real messages.yaml to be sure.
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
        category="job",
    )
    summary = service._generate_summary(tool)
    print(f"DEBUG: Generated Summary:\n{summary}")
    assert "Status: Done" in summary
    assert "Name: John" in summary
    assert "Phone: 0861234567" in summary
    assert "Value: 50" in summary


def test_schedule_job_summary(service):
    tool = ScheduleJobTool(
        customer_query="John", time="tomorrow at 10am", job_id=None, iso_time=None
    )
    summary = service._generate_summary(tool)
    print(f"DEBUG: Generated Summary:\n{summary}")
    assert "Schedule Job:" in summary
    assert "Client details:" in summary
    assert "Name: John" in summary
    assert "Time: tomorrow at 10am" in summary


def test_lead_summary(service):
    tool = AddJobTool(
        customer_name="Mary",
        customer_phone="0879998888",
        location="Main St 1",
        category="lead",
        description="Interested in quote",
    )
    summary = service._generate_summary(tool)
    print(f"DEBUG: Generated Lead Summary:\n{summary}")
    assert "Lead details:" in summary
    assert "Name: Mary" in summary
    assert "Phone: 0879998888" in summary
    assert "Address: Main St 1" in summary
    assert "Description: Interested in quote" in summary
    assert "Status:" not in summary
    assert "Value:" not in summary
