from datetime import datetime, timedelta, date
import math
from typing import List, Dict, Optional
from src.models import Job, User
from .base import RoutingServiceProvider, RoutingSolution, RoutingStep


class MockRoutingService(RoutingServiceProvider):
    """
    A mock implementation of the RoutingServiceProvider for testing and development.
    Uses iterative nearest-neighbor assignment (greedy VRP) considering availability windows.
    """

    def calculate_routes(
        self, jobs: List[Job], employees: List[User]
    ) -> RoutingSolution:
        routes: Dict[int, List[RoutingStep]] = {e.id: [] for e in employees}
        unassigned_jobs: List[Job] = []

        # Initialize employee states: current location and current time
        # We use a dictionary to track mutable state for each employee
        employee_states = {}
        for e in employees:
            # Default start time 9:00 AM today
            start_time = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
            lat = e.default_start_location_lat
            lng = e.default_start_location_lng

            # Only consider employees with valid start locations
            if lat is not None and lng is not None:
                employee_states[e.id] = {
                    "lat": lat,
                    "lng": lng,
                    "time": start_time
                }

        # Filter jobs
        pending_jobs = []
        for job in jobs:
            if job.latitude is not None and job.longitude is not None:
                pending_jobs.append(job)
            else:
                unassigned_jobs.append(job)

        # Iteratively assign the "best" next job
        while pending_jobs:
            best_assignment = None
            min_cost = float("inf")

            # Find best (Employee, Job) pair
            # Cost = Travel Time + Wait Time (to minimize total time spent)

            for emp_id, state in employee_states.items():
                for job in pending_jobs:
                    # Calculate travel time
                    dist_km = self._haversine(state["lat"], state["lng"], job.latitude, job.longitude)

                    # Speed: 30 km/h = 0.5 km/min
                    # Time (min) = Dist (km) / 0.5 = Dist * 2
                    travel_time_mins = dist_km * 2
                    travel_time_seconds = travel_time_mins * 60

                    arrival_time = state["time"] + timedelta(minutes=travel_time_mins)
                    duration_mins = job.estimated_duration or 60

                    # Check availability
                    valid_window = True
                    adjusted_arrival_time = arrival_time
                    adjusted_departure_time = None

                    if job.customer and job.customer.availability:
                        # Check windows
                        # Find earliest window that fits
                        found_window = False
                        # Sort windows by start time to find earliest fit
                        sorted_windows = sorted(job.customer.availability, key=lambda x: x.start_time)

                        for window in sorted_windows:
                            if not window.is_available:
                                continue

                            w_start = window.start_time
                            w_end = window.end_time

                            # If we arrive before window start, we wait.
                            potential_arrival = max(arrival_time, w_start)
                            potential_departure = potential_arrival + timedelta(minutes=duration_mins)

                            if potential_departure <= w_end:
                                # Found a valid slot
                                adjusted_arrival_time = potential_arrival
                                adjusted_departure_time = potential_departure
                                found_window = True
                                break

                        if not found_window:
                            valid_window = False
                    else:
                        # No constraints
                        adjusted_departure_time = adjusted_arrival_time + timedelta(minutes=duration_mins)

                    if valid_window and adjusted_departure_time:
                        # Cost function: (Adjusted Arrival - Current Time).
                        # This includes Travel Time + Waiting Time.
                        cost = (adjusted_arrival_time - state["time"]).total_seconds()

                        # Tie-breaker: prioritize by job ID to be deterministic?
                        # Or strictly < so first found wins ties?
                        if cost < min_cost:
                            min_cost = cost
                            best_assignment = {
                                "emp_id": emp_id,
                                "job": job,
                                "arrival": adjusted_arrival_time,
                                "departure": adjusted_departure_time,
                                "dist_km": dist_km,
                                "travel_seconds": travel_time_seconds
                            }

            if best_assignment:
                emp_id = best_assignment["emp_id"]
                job = best_assignment["job"]

                # Apply assignment
                routes[emp_id].append(
                    RoutingStep(
                        job=job,
                        arrival_time=best_assignment["arrival"],
                        departure_time=best_assignment["departure"],
                        distance_to_prev=best_assignment["dist_km"],
                        duration_from_prev=best_assignment["travel_seconds"]
                    )
                )

                # Update state
                employee_states[emp_id]["lat"] = job.latitude
                employee_states[emp_id]["lng"] = job.longitude
                employee_states[emp_id]["time"] = best_assignment["departure"]

                pending_jobs.remove(job)
            else:
                # Cannot assign any remaining jobs (e.g., due to availability constraints)
                unassigned_jobs.extend(pending_jobs)
                break

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={
                "mode": "mock",
                "algorithm": "iterative_greedy_haversine",
                "processed_jobs": len(jobs),
            },
        )

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees) in Kilometers.
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
