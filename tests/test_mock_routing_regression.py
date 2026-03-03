import pytest
from datetime import datetime, date, timezone, timedelta
from src.models import Job, User, Customer, CustomerAvailability
from src.services.routing.mock import MockRoutingService
from src.services.routing.base import RoutingSolution, RoutingStep

@pytest.fixture
def sample_jobs():
    job1 = Job(id=1, latitude=40.7128, longitude=-74.0060, estimated_duration=60)
    job2 = Job(id=2, latitude=40.7580, longitude=-73.9855, estimated_duration=60)
    return [job1, job2]

@pytest.fixture
def sample_employees():
    emp1 = User(id=1, default_start_location_lat=40.7306, default_start_location_lng=-73.9352)
    return [emp1]

def test_mock_routing_chain_topology(sample_jobs, sample_employees):
    service = MockRoutingService()
    solution = service.calculate_routes(sample_jobs, sample_employees)

    assert len(solution.routes[1]) == 2
    step1 = solution.routes[1][0]
    step2 = solution.routes[1][1]

    # Second step should calculate distance from first step's location, not start location
    dist_from_start_to_j2 = service._haversine(sample_jobs[1].latitude, sample_jobs[1].longitude, sample_employees[0].default_start_location_lat, sample_employees[0].default_start_location_lng)
    dist_from_j1_to_j2 = service._haversine(sample_jobs[1].latitude, sample_jobs[1].longitude, sample_jobs[0].latitude, sample_jobs[0].longitude)

    assert step2.distance_to_prev != dist_from_start_to_j2
    assert step2.distance_to_prev == dist_from_j1_to_j2

def test_mock_routing_availability(sample_jobs, sample_employees):
    service = MockRoutingService()

    # Setup availability for job1
    c1 = Customer(id=1)
    avail = CustomerAvailability(
        start_time=datetime.combine(date.today(), datetime.min.time()).replace(hour=11, tzinfo=timezone.utc),
        end_time=datetime.combine(date.today(), datetime.min.time()).replace(hour=13, tzinfo=timezone.utc),
        is_available=True
    )
    c1.availability = [avail]
    sample_jobs[0].customer = c1

    solution = service.calculate_routes(sample_jobs, sample_employees)

    # arrival at job1 should be pushed to 11:00
    job1_step = next(s for s in solution.routes[1] if s.job.id == 1)
    assert job1_step.arrival_time.hour == 11
