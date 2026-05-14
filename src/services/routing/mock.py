from datetime import datetime, timedelta, date, time
import math
from typing import List, Dict, Optional
from src.models import Job, User, CustomerAvailability
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
        # Start at 9:00 AM today
        start_of_day = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)

        current_times = {
            e.id: start_of_day
            for e in employees
        }

        # Track current location of each employee
        # Initialize with default start location
        current_locations = {}
        for e in employees:
            if e.default_start_location_lat is not None and e.default_start_location_lng is not None:
                current_locations[e.id] = (e.default_start_location_lat, e.default_start_location_lng)
            else:
                # Fallback or skip? If no start location, maybe assume (0,0) or skip.
                # For now, let's skip them in the loop if they don't have a location.
                pass

        for job in jobs:
            # Skip jobs without location
            if job.latitude is None or job.longitude is None:
                unassigned_jobs.append(job)
                continue

            best_employee = None
            min_dist = float("inf")
            best_arrival_time = None
            best_travel_time_mins = 0

            for employee in employees:
                if employee.id not in current_locations:
                    continue

                start_lat, start_lng = current_locations[employee.id]

                # Calculate distance from CURRENT location
                dist = self._haversine(start_lat, start_lng, job.latitude, job.longitude)

                # Estimate travel time: 30km/h
                # Time (hours) = Dist (km) / 30
                # Time (mins) = Dist (km) * 2
                travel_time_mins = dist * 2

                # Calculate arrival time
                arrival_time = current_times[employee.id] + timedelta(minutes=travel_time_mins)
                duration_mins = job.estimated_duration or 60

                # Check availability
                valid_arrival = self._check_availability(job, arrival_time, duration_mins)

                if valid_arrival:
                    # If valid, calculate 'cost' (e.g. distance or total time added)
                    # Here we stick to minimizing distance for simplicity,
                    # but we must ensure we use the potentially adjusted arrival time for availability

                    # If the job forces a wait, the distance doesn't change, but time does.
                    # Let's prioritize minimizing distance, then earliest arrival.
                    if dist < min_dist:
                        min_dist = dist
                        best_employee = employee
                        best_arrival_time = valid_arrival
                        best_travel_time_mins = travel_time_mins

            if best_employee:
                duration_mins = job.estimated_duration or 60
                departure = best_arrival_time + timedelta(minutes=duration_mins)

                routes[best_employee.id].append(
                    RoutingStep(
                        job=job,
                        arrival_time=best_arrival_time,
                        departure_time=departure,
                        distance_to_prev=min_dist,
                        duration_from_prev=best_travel_time_mins * 60, # seconds
                    )
                )
                current_times[best_employee.id] = departure
                current_locations[best_employee.id] = (job.latitude, job.longitude)
            else:
                unassigned_jobs.append(job)

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={
                "mode": "mock",
                "algorithm": "greedy_haversine_with_availability",
                "processed_jobs": len(jobs),
            },
        )

    def _check_availability(self, job: Job, arrival_time: datetime, duration_mins: int) -> Optional[datetime]:
        """
        Checks if the job can be performed at arrival_time given customer availability.
        Returns the adjusted arrival time (if waiting is needed) or None if impossible.
        """
        if not job.customer or not job.customer.availability:
            return arrival_time

        # Filter availability for the job's date (assuming route is for 'today' or job's date)
        # The mock service assumes all jobs are for 'today' based on the start_of_day logic.
        job_date = arrival_time.date()

        # Get windows for this day
        windows = [
            w for w in job.customer.availability
            if w.start_time.date() == job_date and w.is_available
        ]

        if not windows:
             # If availability is defined but no windows for today, assume unavailable?
             # Or does empty list mean 'no restrictions'?
             # The spec says "SC-002: Generated routes respect customer availability windows 100% of the time".
             # If `availability` relationship is loaded and empty, it might mean "no constraints" OR "unavailable".
             # Given the context of "setting availability", usually explicit windows mean "only these times".
             # But if the list is empty, it usually implies no specific constraints set yet.
             # However, if the user explicitly set "No availability today", it might be represented differently.
             # For now, let's assume if availability list is present but empty for the day,
             # and we are checking against it, maybe we should be strict.
             # But `job.customer.availability` is a list of ALL availability records.
             # If the user has availability records for OTHER days but not today, then today is unavailable.
             # If the user has NO availability records at all, then they are always available.
             if len(job.customer.availability) > 0:
                 # Has constraints, but none for today -> Unavailable
                 return None
             else:
                 # No constraints defined -> Available
                 return arrival_time

        # Sort windows by start time
        windows.sort(key=lambda x: x.start_time)

        for window in windows:
            # Window start/end are datetimes.
            w_start = window.start_time
            w_end = window.end_time

            # If we arrive before the window, we wait.
            if arrival_time < w_start:
                actual_start = w_start
            else:
                actual_start = arrival_time

            # Check if we can finish in the window
            actual_end = actual_start + timedelta(minutes=duration_mins)

            if actual_end <= w_end:
                return actual_start

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
        Mock ETA: haversine distance / 30km/h average speed.
        """
        dist = self._haversine(start_lat, start_lng, end_lat, end_lng)
        # 30 km/h = 0.5 km/min
        minutes = dist * 2
        return math.ceil(minutes / 5) * 5
