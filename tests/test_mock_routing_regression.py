import unittest
from datetime import datetime, date
from src.models import Job, User, Customer, CustomerAvailability
from src.services.routing.mock import MockRoutingService

class TestMockRoutingRegression(unittest.TestCase):
    """
    Regression tests for MockRoutingService covering:
    - Availability adherence
    - Travel time units (seconds vs minutes/hours)
    - Pathing logic (iterative nearest neighbor / chain topology)
    """

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

    def test_travel_time_calculation_units(self):
        """
        Verify travel time is calculated in seconds and uses correct speed (30km/h).
        30 km/h = 0.5 km/min.
        6 km => 12 mins => 720 seconds.
        """
        routes = self.service.calculate_routes([self.job1], [self.employee])
        step = routes.routes[self.employee.id][0]

        # duration_from_prev is in seconds.
        # Expected: ~12 mins * 60 = 720 seconds.
        self.assertGreater(step.duration_from_prev, 600, "Travel time is suspiciously low, likely unit error")
        self.assertLess(step.duration_from_prev, 900, "Travel time is suspiciously high")

    def test_routing_logic_chaining(self):
        """
        Verify that routing updates location after assignment (Chain Topology).
        Job 1 is closer to Start.
        Job 2 is closer to Job 1 than to Start.

        Route should be Start -> Job 1 -> Job 2.
        Distance for Job 2 should be calculated from Job 1, not Start.
        """
        # Calculate routes for both jobs
        routes = self.service.calculate_routes([self.job1, self.job2], [self.employee])
        steps = routes.routes[self.employee.id]

        self.assertEqual(len(steps), 2)

        step1 = steps[0] # Should be Job 1
        step2 = steps[1] # Should be Job 2

        self.assertEqual(step1.job.id, self.job1.id)
        self.assertEqual(step2.job.id, self.job2.id)

        # Distance from Start to Job 2 (Newark) is ~15km
        dist_start_job2 = self.service._haversine(
            self.employee.default_start_location_lat, self.employee.default_start_location_lng,
            self.job2.latitude, self.job2.longitude
        )

        # We expect step 2 distance to be significantly less than Start->Job2
        # because it's measured from Job 1
        self.assertNotAlmostEqual(step2.distance_to_prev, dist_start_job2, delta=0.1,
                                  msg="Step 2 distance calculated from Start instead of Previous Job")

        # Verify it matches Job1->Job2 distance
        dist_job1_job2 = self.service._haversine(
            self.job1.latitude, self.job1.longitude,
            self.job2.latitude, self.job2.longitude
        )
        self.assertAlmostEqual(step2.distance_to_prev, dist_job1_job2, delta=0.1)

    def test_availability_window_adherence(self):
        """
        Verify that availability windows are respected.
        Job available only in afternoon (14:00 - 16:00).
        """
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

        # Should be <= 16:00 (departure time)
        self.assertLessEqual(step.departure_time.hour, 16, "Job scheduled after availability window")

if __name__ == '__main__':
    unittest.main()
