
import unittest
from datetime import datetime, date, timedelta
from src.services.routing.mock import MockRoutingService
from src.models import Job, User, Customer, CustomerAvailability

class TestMockRoutingBugs(unittest.TestCase):
    def setUp(self):
        self.service = MockRoutingService()

        # Setup Employee
        self.employee = User(
            id=1,
            default_start_location_lat=0.0,
            default_start_location_lng=0.0
        )

        # Setup Customer with Availability (for bug 1)
        # Available only 10:00 - 12:00
        self.customer_constrained = Customer(id=1)
        self.availability = CustomerAvailability(
            customer_id=1,
            start_time=datetime.combine(date.today(), datetime.min.time()).replace(hour=10),
            end_time=datetime.combine(date.today(), datetime.min.time()).replace(hour=12),
            is_available=True
        )
        self.customer_constrained.availability = [self.availability]

        # Setup Customer without Availability (for bugs 2 & 3)
        self.customer_open = Customer(id=2)
        self.customer_open.availability = [] # Explicitly empty list

    def test_availability_check_missing(self):
        """
        Bug 1: MockRoutingService does not check CustomerAvailability.
        Jobs should only be scheduled within availability windows.
        """
        job = Job(
            id=1,
            latitude=0.1, # Short distance (~11km, ~22mins)
            longitude=0.0,
            estimated_duration=60, # 1 hour
            customer=self.customer_constrained
        )

        # Service starts at 9:00 AM
        # Travel ~22 mins => Arrival 9:22 AM.
        # Window starts 10:00.
        # Should wait until 10:00.

        solution = self.service.calculate_routes([job], [self.employee])

        assigned_jobs = solution.routes[self.employee.id]
        if not assigned_jobs:
            self.fail("Job should be assigned (delayed to 10:00)")

        step = assigned_jobs[0]
        arrival_time = step.arrival_time
        print(f"Bug 1 Check: Job arrives at {arrival_time}. Window starts at 10:00.")

        self.assertGreaterEqual(arrival_time.hour, 10, "Job scheduled before availability window start")

    def test_travel_time_calculation_bug(self):
        """
        Bug 2: Travel time calculation uses wrong units (off by 1000).
        """
        # 1 degree latitude ~ 111 km.
        job = Job(
            id=2,
            latitude=1.0,
            longitude=0.0,
            estimated_duration=60,
            customer=self.customer_open
        )

        # Distance ~ 111 km.
        # Correct code (30km/h): dist * 2 = 222 mins.

        solution = self.service.calculate_routes([job], [self.employee])

        if not solution.routes[self.employee.id]:
            self.fail("Job not assigned (unexpected for open availability)")

        step = solution.routes[self.employee.id][0]

        duration_seconds = step.duration_from_prev
        duration_mins = duration_seconds / 60

        print(f"Bug 2 Check: Distance ~111km. Travel time calculated: {duration_mins} mins.")

        # Expectation: ~222 mins.
        self.assertGreater(duration_mins, 100, "Travel time calculation is way too small")

    def test_distance_calculation_bug(self):
        """
        Bug 3: Distance always calculated from Home, not previous job.
        """
        # Use smaller coordinates to avoid massive travel times that span days
        # But ensure relative distances show the issue.

        # Job 1: (1, 0). Dist from home (0,0) ~ 111 km.
        job1 = Job(
            id=3,
            latitude=1.0,
            longitude=0.0,
            estimated_duration=30,
            customer=self.customer_open
        )

        # Job 2: (1.1, 0). Dist from J1 ~ 11 km. Dist from home ~ 122 km.
        job2 = Job(
            id=4,
            latitude=1.1,
            longitude=0.0,
            estimated_duration=30,
            customer=self.customer_open
        )

        # We pass [job1, job2]
        solution = self.service.calculate_routes([job1, job2], [self.employee])
        routes = solution.routes[self.employee.id]

        if len(routes) < 2:
            self.fail(f"Both jobs should be assigned. Assigned: {len(routes)}")

        step2 = routes[1]
        dist_to_prev = step2.distance_to_prev

        print(f"Bug 3 Check: Step 2 distance from prev: {dist_to_prev} km.")

        # If logic correct (J1 -> J2), dist ~ 11 km.
        # If logic buggy (Home -> J2), dist ~ 122 km.
        self.assertLess(dist_to_prev, 50, "Distance calculated from Home instead of previous job")

if __name__ == "__main__":
    unittest.main()
