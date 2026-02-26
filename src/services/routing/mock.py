from datetime import datetime, timedelta, date
import math
from typing import List, Dict, Optional, Tuple
from src.models import Job, User
from .base import RoutingServiceProvider, RoutingSolution, RoutingStep


class MockRoutingService(RoutingServiceProvider):
    """
    A mock implementation of the RoutingServiceProvider for testing and development.
    Uses iterative nearest-neighbor assignment based on distance to employee's current location.
    """

    def calculate_routes(
        self, jobs: List[Job], employees: List[User]
    ) -> RoutingSolution:
        routes: Dict[int, List[RoutingStep]] = {e.id: [] for e in employees}

        # Filter valid jobs (must have location)
        valid_jobs = []
        unassigned_jobs = []

        for job in jobs:
            if job.latitude is not None and job.longitude is not None:
                valid_jobs.append(job)
            else:
                unassigned_jobs.append(job)

        # Initialize employee states
        # Map: employee_id -> {lat, lng, current_time}
        employee_states = {}
        for e in employees:
            if e.default_start_location_lat is not None and e.default_start_location_lng is not None:
                employee_states[e.id] = {
                    "lat": e.default_start_location_lat,
                    "lng": e.default_start_location_lng,
                    "time": datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
                }

        # Iterative assignment
        pending_jobs = list(valid_jobs)

        while pending_jobs:
            best_assignment: Optional[Tuple[int, Job, datetime, float, float]] = None
            best_dist = float("inf")

            # Check every job against every employee to find global nearest neighbor
            for job in pending_jobs:
                for emp_id, state in employee_states.items():
                    # Calculate distance and time
                    dist_km = self._haversine(state["lat"], state["lng"], job.latitude, job.longitude)

                    # 30km/h = 0.5 km/min -> 2 min/km
                    travel_time_mins = dist_km * 2

                    arrival_time = state["time"] + timedelta(minutes=travel_time_mins)

                    # Check availability
                    valid_arrival = self._check_availability(job, arrival_time)

                    if valid_arrival is not None:
                        # We prioritize minimizing distance (Spatial Optimization)
                        if dist_km < best_dist:
                            best_dist = dist_km
                            best_assignment = (emp_id, job, valid_arrival, dist_km, travel_time_mins)

            if best_assignment:
                emp_id, job, arrival_time, dist_km, travel_time_mins = best_assignment

                duration_mins = job.estimated_duration or 60
                departure_time = arrival_time + timedelta(minutes=duration_mins)

                # Record step
                routes[emp_id].append(
                    RoutingStep(
                        job=job,
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                        distance_to_prev=dist_km,
                        duration_from_prev=travel_time_mins * 60, # Seconds
                    )
                )

                # Update employee state
                employee_states[emp_id]["lat"] = job.latitude
                employee_states[emp_id]["lng"] = job.longitude
                employee_states[emp_id]["time"] = departure_time

                pending_jobs.remove(job)
            else:
                # No remaining jobs can be assigned (unreachable or availability constraints)
                unassigned_jobs.extend(pending_jobs)
                break

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={
                "mode": "mock",
                "algorithm": "iterative_nearest_neighbor",
                "processed_jobs": len(jobs),
            },
        )

    def _check_availability(self, job: Job, arrival_time: datetime) -> Optional[datetime]:
        """
        Check if the job can be performed starting at arrival_time (or later)
        within the customer's availability windows.

        Returns the effective start time (arrival_time or delayed start) if valid,
        or None if not valid.
        """
        # If no customer or no availability, assume available
        if not job.customer or not job.customer.availability:
            return arrival_time

        job_duration = timedelta(minutes=job.estimated_duration or 60)

        # Check against all windows
        # We assume availability windows are specific datetime ranges.
        for window in job.customer.availability:
            if not window.is_available:
                continue

            # For simplicity in mock, if window is for a different day, ignore it?
            # Or if window is generic (e.g. 9-5 any day), we might need logic.
            # Current model has specific datetime.

            # Strict date check:
            if window.start_time.date() != arrival_time.date():
                continue

            w_start = window.start_time
            w_end = window.end_time

            # Determine effective start
            effective_start = max(arrival_time, w_start)

            # Check if job fits
            if effective_start + job_duration <= w_end:
                return effective_start

        # If we went through all windows and found no match
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
