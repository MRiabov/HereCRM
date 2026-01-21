import requests
from datetime import datetime
from typing import List, Dict, Any
from src.models import Job, User
from src.config import settings
from .base import RoutingServiceProvider, RoutingSolution, RoutingException, RoutingStep

class OpenRouteServiceAdapter(RoutingServiceProvider):
    """
    Adapter for OpenRouteService Optimization API.
    Builds payloads and parses responses to/from ORS VRP format.
    """
    BASE_URL = "https://api.openrouteservice.org/optimization"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openrouteservice_api_key

    def calculate_routes(self, jobs: List[Job], employees: List[User]) -> RoutingSolution:
        if not self.api_key:
            raise RoutingException("OpenRouteService API key is missing. Please configure OPENROUTESERVICE_API_KEY.")

        # Handle empty cases
        if not jobs:
            return RoutingSolution({e.id: [] for e in employees}, [], {"status": "no_jobs"})
        if not employees:
            return RoutingSolution({}, jobs, {"status": "no_employees"})

        # Filter jobs and employees with valid locations
        valid_jobs = []
        unassigned_invalid = []
        
        for j in jobs:
            if j.latitude is not None and j.longitude is not None:
                valid_jobs.append(j)
            else:
                unassigned_invalid.append(j)
        
        valid_employees = [e for e in employees if e.default_start_location_lat is not None and e.default_start_location_lng is not None]
        
        if not valid_jobs:
            return RoutingSolution({e.id: [] for e in employees}, jobs, {"status": "no_valid_jobs"})
        
        if not valid_employees:
            return RoutingSolution({}, jobs, {"status": "no_valid_employees_with_location"})

        payload = self.build_payload(valid_jobs, valid_employees)
        
        try:
            response = requests.post(
                self.BASE_URL,
                json=payload,
                headers={
                    "Authorization": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            
            solution = self.parse_response(response.json(), valid_jobs, valid_employees)
            
            # Append invalid jobs to unassigned in list
            solution.unassigned_jobs.extend(unassigned_invalid)
            
            # Ensure all employees exist in result
            for e in employees:
                if e.id not in solution.routes:
                    solution.routes[e.id] = []
                    
            return solution
            
        except requests.RequestException as e:
            raise RoutingException(f"OpenRouteService API request failed: {str(e)}")
        except ValueError as e:
            raise RoutingException(f"Failed to parse OpenRouteService response: {str(e)}")

    def build_payload(self, jobs: List[Job], employees: List[User]) -> Dict[str, Any]:
        """
        Constructs the JSON payload for ORS VRP endpoint.
        """
        ors_jobs = []
        for job in jobs:
            payload_job = {
                "id": job.id,
                "location": [job.longitude, job.latitude],
                "service": (job.estimated_duration or 60) * 60,  # Convert minutes to seconds
            }
            
            # Add time windows from CustomerAvailability if present
            if job.customer and job.customer.availability:
                windows = []
                for avail in job.customer.availability:
                    if avail.is_available:
                        # ORS expects Unix timestamps for time windows
                        windows.append([
                            int(avail.start_time.timestamp()),
                            int(avail.end_time.timestamp())
                        ])
                if windows:
                    payload_job["time_windows"] = windows
            
            ors_jobs.append(payload_job)

        vehicles = []
        for emp in employees:
            start_loc = [emp.default_start_location_lng, emp.default_start_location_lat]
            vehicle = {
                "id": emp.id,
                "profile": "driving-car",
                "start": start_loc,
                "end": start_loc, # Assume return to base for now
            }
            vehicles.append(vehicle)

        return {
            "jobs": ors_jobs,
            "vehicles": vehicles
        }

    def parse_response(self, response: Dict[str, Any], original_jobs: List[Job], employees: List[User]) -> RoutingSolution:
        """
        Parses ORS response into domain objects.
        """
        job_map = {j.id: j for j in original_jobs}
        routes: Dict[int, List[Job]] = {e.id: [] for e in employees}
        assigned_ids = set()

        if "routes" in response:
            for route_data in response["routes"]:
                vehicle_id = route_data.get("vehicle_id")
                # vehicle_id corresponds to User ID (int)
                if vehicle_id is None:
                    continue
                
                ordered_steps = []
                steps = route_data.get("steps", [])
                for step in steps:
                    if step.get("type") == "job":
                        job_id = step.get("id")
                        if job_id in job_map:
                            arrival_s = step.get("arrival")
                            service_s = step.get("service", 0)
                            
                            arrival_dt = None
                            departure_dt = None
                            
                            if arrival_s is not None:
                                # Convert seconds to datetime
                                arrival_dt = datetime.fromtimestamp(arrival_s)
                                departure_dt = datetime.fromtimestamp(arrival_s + service_s)
                            
                            ordered_steps.append(RoutingStep(
                                job=job_map[job_id],
                                arrival_time=arrival_dt,
                                departure_time=departure_dt
                            ))
                            assigned_ids.add(job_id)
                
                routes[vehicle_id] = ordered_steps

        unassigned_jobs = [j for j in original_jobs if j.id not in assigned_ids]
        
        # Check unassigned in response payload as cross-verification (optional)
        # unassigned_from_ors = response.get("unassigned", [])
        
        metrics = response.get("summary", {})

        return RoutingSolution(
            routes=routes,
            unassigned_jobs=unassigned_jobs,
            metrics=metrics
        )
