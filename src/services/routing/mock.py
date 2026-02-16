from datetime import datetime, timedelta, date, time
import math
from typing import List, Dict, Optional, Any
from src.models import Job, User, CustomerAvailability
from .base import RoutingServiceProvider, RoutingSolution, RoutingStep


class MockRoutingService(RoutingServiceProvider):
    """
    A mock implementation of the RoutingServiceProvider for testing and development.
    Uses a greedy Nearest Neighbor approach: iteratively assigns the closest job
    to any employee's current location, respecting availability constraints.
    """

    def calculate_routes(
        self, jobs: List[Job], employees: List[User]
    ) -> RoutingSolution:
        # 1. Initialize
        routes: Dict[int, List[RoutingStep]] = {e.id: [] for e in employees}
        unassigned_jobs: List[Job] = []

        # Employee State: Current time and location
        # Default start time is 9:00 AM today
        start_of_day = datetime.combine(date.today(), datetime.min.time()).replace(
            hour=9
        )
        employee_state: Dict[int, Dict[str, Any]] = {}

        for e in employees:
            lat = e.default_start_location_lat
            lng = e.default_start_location_lng

            # If no start location, we can't route them effectively in a spatial model.
            # But for mock, maybe assume (0,0)? No, better to skip or treat as (0,0).
            # If (0,0) is used, distance will be huge to real locations.
            # Let's assume (0,0) if None to avoid crashing, but usually they should have location.
            if lat is None or lng is None:
                lat, lng = 0.0, 0.0

            employee_state[e.id] = {
                "time": start_of_day,
                "lat": lat,
                "lng": lng,
            }

        pending_jobs = list(jobs)

        # 2. Iterative Assignment
        while pending_jobs:
            best_assignment = None
            min_cost = float("inf")  # Cost = Travel Time + Wait Time? Or just distance?

            # Find the best (Employee, Job) pair
            for job in pending_jobs:
                # Skip jobs without location
                if job.latitude is None or job.longitude is None:
                    continue

                for emp in employees:
                    state = employee_state[emp.id]

                    # Calculate Travel
                    dist_km = self._haversine(
                        state["lat"], state["lng"], job.latitude, job.longitude
                    )

                    # 30km/h => 0.5 km/min => 2 mins/km
                    travel_time_mins = dist_km * 2
                    travel_time_sec = travel_time_mins * 60

                    arrival_time = state["time"] + timedelta(minutes=travel_time_mins)

                    # Check Availability
                    valid_arrival = self._check_availability(job, arrival_time)

                    if valid_arrival:
                        # Cost function: Minimize (Travel Time + Wait Time)
                        wait_time_sec = (valid_arrival - arrival_time).total_seconds()
                        total_cost = travel_time_sec + wait_time_sec

                        if total_cost < min_cost:
                            min_cost = total_cost
                            best_assignment = (
                                emp,
                                job,
                                valid_arrival,
                                dist_km,
                                travel_time_sec,
                            )

            if best_assignment:
                emp, job, arrival, dist_km, travel_sec = best_assignment

                # Update Route
                duration_mins = job.estimated_duration or 60
                departure = arrival + timedelta(minutes=duration_mins)

                routes[emp.id].append(
                    RoutingStep(
                        job=job,
                        arrival_time=arrival,
                        departure_time=departure,
                        distance_to_prev=dist_km,
                        duration_from_prev=travel_sec, # Strictly in seconds
                    )
                )

                # Update State
                employee_state[emp.id]["time"] = departure
                employee_state[emp.id]["lat"] = job.latitude
                employee_state[emp.id]["lng"] = job.longitude

                pending_jobs.remove(job)
            else:
                # No valid assignment found for ANY remaining job
                # Move all remaining valid-location jobs to unassigned
                # (Jobs without location are skipped in the loop but not removed)
                # We should separate them.

                # The loop only checks jobs with location.
                # If we are here, it means for all jobs with location, no employee could take them
                # (due to availability constraints or no employees).
                break

        # Add remaining to unassigned
        unassigned_jobs.extend(pending_jobs)

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={
                "mode": "mock",
                "algorithm": "nearest_neighbor",
                "processed_jobs": len(jobs),
            },
        )

    def _check_availability(self, job: Job, arrival_time: datetime) -> Optional[datetime]:
        """
        Check if arrival_time is valid for the job's customer availability.
        Returns the valid arrival time (which might be later than proposed if waiting is needed),
        or None if not possible.
        """
        if not job.customer or not job.customer.availability:
            return arrival_time  # Unrestricted

        # Filter windows for the specific day
        target_date = arrival_time.date()
        # Sort windows by start time
        windows = sorted(
            [w for w in job.customer.availability if w.start_time.date() == target_date],
            key=lambda w: w.start_time
        )

        if not windows:
            # If availability is defined but none for this day...
            # Spec says "treating non-empty availability lists as a whitelist".
            # If the list on the customer is non-empty, but none match today,
            # does that mean "unavailable today"? Yes.
            return None

        duration_mins = job.estimated_duration or 60
        job_end_time = arrival_time + timedelta(minutes=duration_mins)

        for window in windows:
            # Check if we can fit in this window

            # Window times are likely datetimes. If they are just times, we need to combine.
            # Assuming they are full datetimes as per model definition.

            # Case 1: Arrival is within window, and completion is within window
            if arrival_time >= window.start_time and job_end_time <= window.end_time:
                return arrival_time

            # Case 2: Arrival is BEFORE window, but we can wait until start.
            # New arrival = window.start_time
            # Check if new completion <= window.end_time
            if arrival_time < window.start_time:
                new_arrival = window.start_time
                new_end = new_arrival + timedelta(minutes=duration_mins)
                if new_end <= window.end_time:
                    return new_arrival

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
        # 30 km/h = 0.5 km/min => dist * 2 mins
        minutes = dist * 2
        return math.ceil(minutes / 5) * 5
