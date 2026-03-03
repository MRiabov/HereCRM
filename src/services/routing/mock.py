from datetime import datetime, timedelta, date
import math
from typing import List, Dict, Optional
from src.models import Job, User
from .base import RoutingServiceProvider, RoutingSolution, RoutingStep


class MockRoutingService(RoutingServiceProvider):
    """
    A mock implementation of the RoutingServiceProvider for testing and development.
    Uses simple greedy assignment based on distance to employee's start location.
    """

    def calculate_routes(
        self, jobs: List[Job], employees: List[User]
    ) -> RoutingSolution:
        routes: Dict[int, List[RoutingStep]] = {e.id: [] for e in employees}
        unassigned_jobs: List[Job] = []

        # Mock times
        from datetime import timezone
        current_times = {
            e.id: datetime.combine(date.today(), datetime.min.time()).replace(hour=9, tzinfo=timezone.utc)
            for e in employees
        }

        # Keep track of current location of employees
        current_locations = {
            e.id: (e.default_start_location_lat, e.default_start_location_lng)
            for e in employees
        }

        for job in jobs:
            # Skip jobs without location
            if job.latitude is None or job.longitude is None:
                unassigned_jobs.append(job)
                continue

            best_employee = None
            min_dist = float("inf")
            best_arrival = None
            best_departure = None
            best_travel_time_mins = None

            for employee in employees:
                lat, lng = current_locations[employee.id]

                if lat is None or lng is None:
                    continue

                dist = self._haversine(job.latitude, job.longitude, lat, lng)

                # Estimate travel time: 30km/h = 0.5 km/min
                travel_time_mins = (dist / 1000) * 2
                duration_mins = job.estimated_duration or 60

                arrival = current_times[employee.id] + timedelta(
                    minutes=travel_time_mins
                )

                # Check CustomerAvailability
                is_valid = True
                departure = arrival + timedelta(minutes=duration_mins)

                if job.customer and job.customer.availability:
                    found_window = False
                    for avail in job.customer.availability:
                        if avail.is_available and avail.start_time.date() == arrival.date():
                            found_window = True
                            if arrival < avail.start_time:
                                arrival = avail.start_time
                            departure = arrival + timedelta(minutes=duration_mins)
                            if departure > avail.end_time:
                                is_valid = False
                            break # Assume only one relevant window per day for mock simplicity

                    if not found_window:
                        is_valid = False

                if is_valid and dist < min_dist:
                    min_dist = dist
                    best_employee = employee
                    best_arrival = arrival
                    best_departure = departure
                    best_travel_time_mins = travel_time_mins

            if best_employee:
                routes[best_employee.id].append(
                    RoutingStep(
                        job=job,
                        arrival_time=best_arrival,
                        departure_time=best_departure,
                        distance_to_prev=min_dist,
                        duration_from_prev=best_travel_time_mins * 60,
                    )
                )
                current_times[best_employee.id] = best_departure
                current_locations[best_employee.id] = (job.latitude, job.longitude)
            else:
                unassigned_jobs.append(job)

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={
                "mode": "mock",
                "algorithm": "greedy_haversine",
                "processed_jobs": len(jobs),
            },
        )

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(
            math.radians(lat1)
        ) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def get_eta_minutes(
        self, start_lat: float, start_lng: float, end_lat: float, end_lng: float
    ) -> Optional[int]:
        """
        Mock ETA: haversine distance / 40km/h average speed.
        """
        dist = self._haversine(start_lat, start_lng, end_lat, end_lng)
        # 40 km/h = 40/60 km/min = 0.66 km/min
        minutes = dist / 0.66
        return math.ceil(minutes / 5) * 5
