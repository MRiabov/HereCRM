import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import requests
from src.models import Job, User, Customer, CustomerAvailability
from src.services.routing.mock import MockRoutingService
from src.services.routing.ors import OpenRouteServiceAdapter
from src.services.routing.base import RoutingException

@pytest.fixture
def sample_jobs():
    job1 = Job(id=1, latitude=40.7128, longitude=-74.0060, estimated_duration=60) # NY
    job2 = Job(id=2, latitude=34.0522, longitude=-118.2437, estimated_duration=60) # LA
    job3 = Job(id=3, latitude=None, longitude=None) # No location
    return [job1, job2, job3]

@pytest.fixture
def sample_employees():
    emp1 = User(id=1, default_start_location_lat=40.7306, default_start_location_lng=-73.9352) # Brooklyn
    emp2 = User(id=2, default_start_location_lat=34.0522, default_start_location_lng=-118.2437) # LA
    emp3 = User(id=3, default_start_location_lat=None, default_start_location_lng=None) # No location
    return [emp1, emp2, emp3]

def test_mock_routing_service_assignments(sample_jobs, sample_employees):
    service = MockRoutingService()
    solution = service.calculate_routes(sample_jobs, sample_employees)
    
    # Employee 1 (NY) should get Job 1 (NY)
    assert sample_jobs[0] in solution.routes[1]
    
    # Employee 2 (LA) should get Job 2 (LA)
    assert sample_jobs[1] in solution.routes[2]
    
    # Job 3 (No loc) should be unassigned
    assert sample_jobs[2] in solution.unassigned_jobs
    
    # Employee 3 should have no routes (no start loc)
    # Note: Depending on logic, empty list or key missing. Implementation initializes all keys.
    assert len(solution.routes[3]) == 0

def test_ors_adapter_build_payload(sample_jobs, sample_employees):
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    
    # Add availability to job1
    customer = Customer(id=10)
    avail = CustomerAvailability(
        start_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 17, 0, tzinfo=timezone.utc),
        is_available=True
    )
    customer.availability = [avail]
    sample_jobs[0].customer = customer
    
    payload = adapter.build_payload(sample_jobs, sample_employees)
    
    assert "jobs" in payload
    assert "vehicles" in payload
    
    # Job 1 verification
    job1_payload = next((j for j in payload["jobs"] if j["id"] == 1), None)
    assert job1_payload is not None
    assert job1_payload["location"] == [-74.0060, 40.7128]
    assert "time_windows" in job1_payload
    assert job1_payload["time_windows"][0] == [int(avail.start_time.timestamp()), int(avail.end_time.timestamp())]

    # Vehicle 1 verification
    veh1 = next((v for v in payload["vehicles"] if v["id"] == 1), None)
    assert veh1 is not None
    assert veh1["start"] == [-73.9352, 40.7306]

@patch("requests.post")
def test_ors_adapter_calculate_routes_success(mock_post, sample_jobs, sample_employees):
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    
    # Mock Response
    mock_response = {
        "routes": [
            {
                "vehicle_id": 1,
                "steps": [
                    {"type": "start"},
                    {"type": "job", "id": 1},
                    {"type": "end"}
                ]
            }
        ],
        "summary": {"cost": 100},
        "unassigned": []
    }
    
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = mock_response
    
    # Logic note: calculate_routes filters invalid jobs first.
    # Job 3 is invalid (no loc).
    # Jobs Passed: 1, 2. Employees: 1, 2.
    # Response assigns Job 1 to User 1.
    # Job 2 is not in response routes -> Unassigned.
    
    solution = adapter.calculate_routes(sample_jobs, sample_employees)
    
    assert sample_jobs[0] in solution.routes[1]
    assert solution.metrics["cost"] == 100
    
    # Job 3 is unassigned (filtered before api call)
    assert sample_jobs[2] in solution.unassigned_jobs
    
    # Job 2 was valid but not assigned by 'api' (mock response didn't include it)
    assert sample_jobs[1] in solution.unassigned_jobs

@patch("requests.post")
def test_ors_adapter_api_failure(mock_post, sample_jobs, sample_employees):
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    mock_post.side_effect = requests.RequestException("API Error")
    
    # Should raise RoutingException
    with pytest.raises(RoutingException):
        adapter.calculate_routes(sample_jobs, sample_employees)

def test_ors_adapter_missing_key():
    adapter = OpenRouteServiceAdapter(api_key="") # Explicit empty
    
    # Should raise RoutingException
    with pytest.raises(RoutingException):
        adapter.calculate_routes([], [])
