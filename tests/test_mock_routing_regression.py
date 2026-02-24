
import pytest
import asyncio
from datetime import datetime, date, time, timedelta
from src.services.routing.mock import MockRoutingService
from src.models import Job, User, Customer, CustomerAvailability

@pytest.mark.asyncio
async def test_mock_routing_distance_and_time():
    service = MockRoutingService()

    # Setup Employees
    emp1 = User(id=1, default_start_location_lat=40.7128, default_start_location_lng=-74.0060) # NYC

    # Setup Jobs
    # Job 1: ~11km North of NYC
    job1 = Job(id=1, latitude=40.8128, longitude=-74.0060, estimated_duration=60)
    # Job 2: ~11km North of Job 1 (~22km from NYC)
    job2 = Job(id=2, latitude=40.9128, longitude=-74.0060, estimated_duration=60)

    jobs = [job1, job2]
    employees = [emp1]

    solution = service.calculate_routes(jobs, employees)

    routes = solution.routes[1]
    assert len(routes) == 2

    step1 = routes[0]
    step2 = routes[1]

    # Check distance calculation
    # Job 1 distance from start should be approx 11.1km
    dist1 = step1.distance_to_prev
    assert 11.0 < dist1 < 11.3, f"Expected ~11.1km, got {dist1}"

    # Job 2 distance from Job 1 should be approx 11.1km.
    dist2 = step2.distance_to_prev
    assert 11.0 < dist2 < 11.3, f"Expected ~11.1km, got {dist2}. Distance likely calculated from start (22.2km) instead of previous job."

    # Check travel time
    # Time (hours) = Distance (km) / 30
    # Time (mins) = Distance (km) * 2
    # For ~11.1km: ~22.2 mins
    time1_mins = step1.duration_from_prev / 60
    assert 22.0 < time1_mins < 22.5, f"Expected ~22.2 mins, got {time1_mins}. Likely unit error."

@pytest.mark.asyncio
async def test_mock_routing_availability():
    service = MockRoutingService()
    employees = [User(id=1, default_start_location_lat=40.7128, default_start_location_lng=-74.0060)]

    # Customer available 10:00 - 12:00
    cust = Customer(id=1)
    avail = CustomerAvailability(
        customer_id=1,
        start_time=datetime.combine(date.today(), time(10, 0)),
        end_time=datetime.combine(date.today(), time(12, 0)),
        is_available=True
    )
    cust.availability = [avail]

    # Job very close to start, travel time minimal.
    # Start of day is 09:00.
    # Without availability check, arrival would be ~09:00.
    # With check, arrival should be 10:00.
    job3 = Job(id=3, latitude=40.7138, longitude=-74.0060, estimated_duration=60, customer=cust)

    jobs = [job3]
    solution = service.calculate_routes(jobs, employees)

    assert len(solution.routes[1]) == 1
    step = solution.routes[1][0]

    arrival_time = step.arrival_time
    assert arrival_time.hour == 10, f"Expected arrival at 10:00, got {arrival_time}"
    assert arrival_time.minute == 0
