import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.tools.employee_management import ShowScheduleTool, AssignJobTool
from src.tool_executor import ToolExecutor
from src.services.assignment_service import AssignmentResult

@pytest.mark.asyncio
async def test_employee_dashboard_flow_mocked():
    """
    Test the full flow using mocked services to behave like integration test
    but without needing a real DB (since we are in a dev environment).
    
    Flow:
    1. ShowScheduleTool -> Calls DashboardService -> Returns rendered string
    2. AssignJobTool -> Calls AssignmentService -> Returns success message
    """
    
    # Mock dependencies
    mock_session = AsyncMock()
    mock_dashboard_service = AsyncMock()
    mock_assignment_service = AsyncMock()
    mock_template_service = MagicMock()
    
    def mock_render(key, **kwargs):
        if key == "employee_ambiguous":
            return f"Status: Ambiguous. Did you mean {kwargs['matches']}?"
        if key == "employee_not_found":
            return f"Error: Could not find employee named '{kwargs['name']}'."
        if key == "job_assigned":
            return f"Assigned Job #{kwargs['job_id']} to {kwargs['employee_name']}"
        return f"[{key}]"
    mock_template_service.render.side_effect = mock_render
    
    # Setup Executor with mocked services
    # We need to patch the classes inside tool_executor so they return our mocks
    with patch('src.tool_executor.DashboardService', return_value=mock_dashboard_service), \
         patch('src.tool_executor.AssignmentService', return_value=mock_assignment_service), \
         patch('src.tool_executor.InvoiceService'), \
         patch('src.tool_executor.JobRepository'), \
         patch('src.tool_executor.CustomerRepository'), \
         patch('src.tool_executor.RequestRepository'), \
         patch('src.tool_executor.UserRepository'), \
         patch('src.tool_executor.ServiceRepository'), \
         patch('src.tool_executor.GeocodingService'), \
         patch('src.tool_executor.SearchService'):
        
        executor = ToolExecutor(
            session=mock_session,
            business_id=1,
            user_id=1,
            user_phone="123",
            template_service=mock_template_service
        )
        
        # Override the services directly just to be sure (since __init__ creates them)
        executor.dashboard_service = mock_dashboard_service
        executor.assignment_service = mock_assignment_service

        # --- Step 1: Show Schedule ---
        # Setup mock return
        mock_emp = MagicMock()
        mock_emp.name = "Alice"
        mock_job = MagicMock()
        mock_job.id = 101
        mock_job.description = "Fix sink"
        mock_job.scheduled_at = datetime(2023, 10, 27, 10, 0)
        mock_job.location = "123 Main St"
        
        mock_dashboard_service.get_employee_schedules.return_value = {mock_emp: [mock_job]}
        mock_dashboard_service.get_unscheduled_jobs.return_value = []
        
        tool = ShowScheduleTool(date="2023-10-27")
        result, metadata = await executor.execute(tool)
        
        # Verify calls
        mock_dashboard_service.get_employee_schedules.assert_awaited_once()
        assert "Employees management:" in result
        assert "Alice's schedule:" in result
        assert "Fix sink" in result
        assert metadata["action"] == "query"

        # --- Step 2: Assign Job ---
        # Setup mock for ambiguous case first
        mock_u1 = MagicMock()
        mock_u1.name = "John Doe"
        mock_u1.id = 2
        mock_u2 = MagicMock()
        mock_u2.name = "John Smith"
        mock_u2.id = 3
        
        mock_assignment_service.find_employee_by_name.return_value = [mock_u1, mock_u2]
        
        tool = AssignJobTool(job_id=99, assign_to_name="John")
        result, _ = await executor.execute(tool)
        
        assert "Status: Ambiguous" in result
        assert "John Doe" in result
        assert "John Smith" in result
        
        # Setup mock for success case
        mock_assignment_service.find_employee_by_name.return_value = [mock_u1]
        mock_assignment_service.assign_job.return_value = AssignmentResult(success=True, warning="Double booked")
        
        tool = AssignJobTool(job_id=99, assign_to_name="John Doe")
        result, metadata = await executor.execute(tool)
        
        mock_assignment_service.assign_job.assert_awaited_with(99, 2)
        assert "Assigned Job #99 to John Doe" in result
        assert "Note: Double booked" in result
        assert metadata["action"] == "update"
