import datetime

from src.lib.text_formatter import render_employee_dashboard

def test_dashboard_rendering():
    # Mock data
    employees = [
        {
            'name': 'John Doe',
            'jobs': [
                {
                    'scheduled_at': datetime.datetime(2023, 10, 27, 9, 30),
                    'description': 'Fix sink',
                    'id': 101,
                    'location': '123 Main St'
                },
                {
                    'scheduled_at': datetime.datetime(2023, 10, 27, 14, 0),
                    'description': 'Install lights',
                    'id': 102,
                    'location': '456 Oak Ave'
                }
            ]
        },
        {
            'name': 'Jane Smith',
            'jobs': []
        }
    ]
    
    unscheduled = [
        {'description': 'Emergency leak', 'id': 201},
        {'description': 'Quote visit', 'id': 202}
    ]
    
    context = {
        'employees': employees,
        'unscheduled': unscheduled
    }
    
    output = render_employee_dashboard(context)
    
    # Assertions
    assert "Employees management:" in output
    assert "John Doe's schedule:" in output
    assert "09:30 - Fix sink #101 (123 Main St)" in output
    assert "14:00 - Install lights #102 (456 Oak Ave)" in output
    assert "Jane Smith's schedule:" in output
    
    assert "Unscheduled jobs:" in output
    assert "Emergency leak #201" in output
    assert "Quote visit #202" in output

def test_dashboard_rendering_empty():
    context = {
        'employees': [],
        'unscheduled': []
    }
    output = render_employee_dashboard(context)
    
    assert "Employees management:" in output
    assert "Unscheduled jobs:" in output
    assert "John Doe" not in output
