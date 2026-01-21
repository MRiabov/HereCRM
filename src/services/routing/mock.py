from datetime import datetime, timedelta, date
import math
from typing import List, Dict
from src.models import Job, User
from .base import RoutingServiceProvider, RoutingSolution, RoutingStep

class MockRoutingService(RoutingServiceProvider):
    """
    A mock implementation of the RoutingServiceProvider for testing and development.
    Uses simple greedy assignment based on distance to employee's start location.
    """
    
    def calculate_routes(self, jobs: List[Job], employees: List[User]) -> RoutingSolution:
        routes: Dict[int, List[RoutingStep]] = {e.id: [] for e in employees}
        unassigned_jobs: List[Job] = []
        
        # Mock times
        current_times = {e.id: datetime.combine(date.today(), datetime.min.time()).replace(hour=9) for e in employees}

        for job in jobs:
            # Skip jobs without location
            if job.latitude is None or job.longitude is None:
                unassigned_jobs.append(job)
                continue
                
            best_employee = None
            min_dist = float('inf')
            
            for employee in employees:
                # Use default start location. If missing, assume (0,0) or skip.
                # Here we skip employees without start location to mimic real constraints
                lat = employee.default_start_location_lat
                lng = employee.default_start_location_lng
                
                if lat is None or lng is None:
                    continue
                
                dist = self._haversine(job.latitude, job.longitude, lat, lng)
                
                if dist < min_dist:
                    min_dist = dist
                    best_employee = employee
            
            if best_employee:
                # Estimate travel time: 30km/h = 0.5 km/min
                travel_time_mins = (min_dist / 1000) * 2 
                duration_mins = job.estimated_duration or 60
                
                arrival = current_times[best_employee.id] + timedelta(minutes=travel_time_mins)
                departure = arrival + timedelta(minutes=duration_mins)
                
                routes[best_employee.id].append(RoutingStep(
                    job=job,
                    arrival_time=arrival,
                    departure_time=departure,
                    distance_to_prev=min_dist,
                    duration_from_prev=travel_time_mins * 60
                ))
                current_times[best_employee.id] = departure
            else:
                unassigned_jobs.append(job)
                
        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics={"mode": "mock", "algorithm": "greedy_haversine", "processed_jobs": len(jobs)}
        )

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
