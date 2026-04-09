from datetime import datetime, timedelta, date
import math
from typing import List, Dict, Optional
from src.models import Job, User, CustomerAvailability
from .base import RoutingServiceProvider, RoutingSolution, RoutingStep


class MockRoutingService(RoutingServiceProvider):
    """
    A mock implementation of the RoutingServiceProvider for testing and development.
    Uses simple greedy assignment based on distance to employee's start location,
    respecting customer availability windows.
    """

    def calculate_routes(
        self, jobs: List[Job], employees: List[User]
    ) -> RoutingSolution:
        routes: Dict[int, List[RoutingStep]] = {e.id: [] for e in employees}
        unassigned_jobs: List[Job] = []

        # Mock times - start at 9:00 AM on today's date
        # Note: In production this should probably start from "now" or from specific date
        current_times = {
            e.id: datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
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

            # Default duration 60 mins
            duration_mins = job.estimated_duration or 60
            duration_delta = timedelta(minutes=duration_mins)

            for employee in employees:
                # Use default start location. If missing, assume (0,0) or skip.
                lat = employee.default_start_location_lat
                lng = employee.default_start_location_lng

                if lat is None or lng is None:
                    continue

                dist = self._haversine(job.latitude, job.longitude, lat, lng)

                # Calculate travel time: 30km/h = 0.5 km/min
                travel_time_mins = (dist / 1000) * 2
                travel_delta = timedelta(minutes=travel_time_mins)

                # Tentative arrival based on current time + travel
                tentative_arrival = current_times[employee.id] + travel_delta

                # Check Availability Constraints
                if job.customer and job.customer.availability:
                    # Filter for availability windows that overlap with the day?
                    # The spec implies specific date-time ranges.
                    # We just check if we can fit the job into any available window
                    # starting from tentative_arrival.

                    adjusted_arrival = self._adjust_for_availability(
                        tentative_arrival, duration_delta, job.customer.availability
                    )

                    if adjusted_arrival is None:
                        # Cannot fit this job with this employee's schedule constraints
                        continue

                    tentative_arrival = adjusted_arrival

                # Optimization: Minimize distance primarily (Greedy Nearest Neighbor)
                # Could also optimize for earliest arrival, but sticking to distance for simplicity/consistency
                if dist < min_dist:
                    min_dist = dist
                    best_employee = employee
                    best_arrival = tentative_arrival
                    best_departure = tentative_arrival + duration_delta

            if best_employee:
                routes[best_employee.id].append(
                    RoutingStep(
                        job=job,
                        arrival_time=best_arrival,
                        departure_time=best_departure,
                        distance_to_prev=min_dist,
                        duration_from_prev=(best_arrival - current_times[best_employee.id]).total_seconds(),
                    )
                )
                current_times[best_employee.id] = best_departure
            else:
                unassigned_jobs.append(job)

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={
                "mode": "mock",
                "algorithm": "greedy_haversine_availability",
                "processed_jobs": len(jobs),
            },
        )

    def _adjust_for_availability(
        self,
        arrival_time: datetime,
        duration: timedelta,
        availabilities: List[CustomerAvailability]
    ) -> Optional[datetime]:
        """
        Finds the earliest start time >= arrival_time such that [start, start + duration]
        is fully contained within one of the availability windows.

        If availability list is empty or all windows are passed, returns None?
        No, if list is empty, assume available (unless explicitly unavailable, but model defaults is_available=True).
        However, if availabilities are present, we assume strict adherence (whitelist).
        """
        if not availabilities:
            return arrival_time

        # Sort windows by start time just in case
        sorted_windows = sorted(availabilities, key=lambda x: x.start_time)

        for window in sorted_windows:
            if not window.is_available:
                continue

            # If window ends before we can even arrive, skip
            if window.end_time < arrival_time + duration:
                continue

            # If we arrive after window starts, check if we fit before it ends
            if arrival_time >= window.start_time:
                if arrival_time + duration <= window.end_time:
                    return arrival_time
            else:
                # We arrive before window starts.
                # Can we wait and start exactly at window start?
                # Check if window duration is enough
                if window.start_time + duration <= window.end_time:
                    return window.start_time

        return None

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
