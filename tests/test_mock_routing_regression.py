import unittest
from datetime import datetime, timedelta, date
from src.models import Job, User, Customer, CustomerAvailability
from src.services.routing.mock import MockRoutingService
from src.services.routing.base import RoutingSolution

class TestMockRoutingRegression(unittest.TestCase):
    def setUp(self):
        self.service = MockRoutingService()
        self.employee = User(
            id=1,
            email="emp@example.com",
            default_start_location_lat=40.7128, # New York
            default_start_location_lng=-74.0060
        )

        # Job 1: Close to NY (Jersey City) ~ 6km
        self.job1 = Job(
            id=101,
            latitude=40.7282,
            longitude=-74.0776,
            estimated_duration=60,
            customer=Customer(id=1, availability=[])
        )

        # Job 2: Farther from NY (Newark) ~ 15km
        self.job2 = Job(
            id=102,
            latitude=40.7357,
            longitude=-74.1724,
            estimated_duration=60,
            customer=Customer(id=2, availability=[])
        )

    def test_travel_time_calculation_bug(self):
        """
        Test that travel time is calculated correctly (approx 2 mins per km).
        Current code does (dist / 1000) * 2 which treats dist as meters even though haversine returns km.
        """
        # Distance approx 6km.
        # Expected time @ 30km/h = 6 / 0.5 = 12 mins.
        # Buggy code: 6 / 1000 * 2 = 0.012 mins.

        routes = self.service.calculate_routes([self.job1], [self.employee])
        step = routes.routes[self.employee.id][0]

        # duration_from_prev is in seconds.
        # Expected: ~12 mins * 60 = 720 seconds.
        # Buggy: ~0.012 mins * 60 = 0.72 seconds.

        # Assert that duration is reasonable (> 1 minute)
        self.assertGreater(step.duration_from_prev, 60, "Travel time is suspiciously low, likely unit error")

    def test_routing_logic_chaining_bug(self):
        """
        Test that routing updates location after assignment.
        If we have Job 1 (6km from start) and Job 2 (15km from start, but 9km from Job 1).

        If calculated from start:
        Job 1: 6km
        Job 2: 15km

        If chained:
        Job 1: 6km
        Job 2: distance(Job1, Job2) ~ 9km

        The mock service currently calculates everything from start.
        """
        # Calculate routes for both jobs
        routes = self.service.calculate_routes([self.job1, self.job2], [self.employee])
        steps = routes.routes[self.employee.id]

        self.assertEqual(len(steps), 2)

        step1 = steps[0]
        step2 = steps[1]

        # Distance from Start to Job 1 (Jersey City) is ~6km
        # Distance from Start to Job 2 (Newark) is ~15km
        # Distance from Job 1 to Job 2 is ~9km

        # If logic is correct (chained), Step 2 distance should be ~9km.
        # If logic is buggy (always from start), Step 2 distance will be ~15km (or whatever sorting logic it uses)

        # Let's verify step 2 distance.
        # Using haversine for verification
        dist_start_job2 = self.service._haversine(
            self.employee.default_start_location_lat, self.employee.default_start_location_lng,
            self.job2.latitude, self.job2.longitude
        )

        self.assertNotAlmostEqual(step2.distance_to_prev, dist_start_job2, delta=0.1,
                                  msg="Step 2 distance calculated from Start instead of Previous Job")

    def test_availability_window_bug(self):
        """
        Test that availability windows are respected.
        """
        # Job with availability only in afternoon (14:00 - 16:00)
        # Mock service starts at 9:00.

        # Set availability for job 1
        today = date.today()
        start_time = datetime.combine(today, datetime.min.time()).replace(hour=14)
        end_time = datetime.combine(today, datetime.min.time()).replace(hour=16)

        self.job1.customer.availability = [
            CustomerAvailability(
                start_time=start_time,
                end_time=end_time,
                is_available=True
            )
        ]

        routes = self.service.calculate_routes([self.job1], [self.employee])
        step = routes.routes[self.employee.id][0]

        # Should be >= 14:00
        self.assertGreaterEqual(step.arrival_time.hour, 14, "Job scheduled before availability window")

if __name__ == '__main__':
    unittest.main()
