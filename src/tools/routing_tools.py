
import asyncio
from datetime import date as date_cls, datetime, timedelta
from typing import List
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User
from src.repositories import JobRepository, UserRepository
from src.services.routing.base import RoutingServiceProvider, RoutingSolution, RoutingException
from src.services.routing.ors import OpenRouteServiceAdapter
from src.services.routing.mock import MockRoutingService
from src.uimodels import AutorouteTool
from src.config import settings

logger = logging.getLogger(__name__)

class AutorouteToolExecutor:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)
        self.user_repo = UserRepository(session)
        
        # Select Provider
        # If API key is present, use ORS, else Mock
        if settings.openrouteservice_api_key:
            self.routing_service: RoutingServiceProvider = OpenRouteServiceAdapter()
        else:
            logger.info("No OpenRouteService API key found, using Mock Routing Service.")
            self.routing_service = MockRoutingService()

    async def run(self, input: AutorouteTool) -> str:
        # 1. Parse date
        target_date = date_cls.today()
        if input.date:
             try:
                 target_date = date_cls.fromisoformat(input.date)
             except ValueError:
                 return f"Invalid date format: {input.date}. Please use YYYY-MM-DD."

        # 2. Fetch data
        # Employees
        employees = await self.user_repo.get_team_members(self.business_id)
        if not employees:
            return "No employees found to route."

        # Jobs
        # Fetch pending (backlog) - these are jobs that need to be done but aren't scheduled
        pending_jobs = await self.job_repo.search(query="all", business_id=self.business_id, status="pending")
        
        # Fetch scheduled for target_date - these are jobs already on the board for today
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        scheduled_jobs = await self.job_repo.search(
            query="all", 
            business_id=self.business_id, 
            status="scheduled",
            min_date=start_of_day,
            max_date=end_of_day,
            query_type="scheduled"
        )
        
        # Combine unique jobs
        all_jobs_map = {j.id: j for j in pending_jobs}
        for j in scheduled_jobs:
            all_jobs_map[j.id] = j
            
        all_jobs = list(all_jobs_map.values())
        
        if not all_jobs:
            return f"No jobs found to route for {target_date} (checked pending and scheduled)."

        # 3. Call Service (Run in thread to avoid blocking if sync)
        try:
             loop = asyncio.get_running_loop()
             solution = await loop.run_in_executor(None, self.routing_service.calculate_routes, all_jobs, employees)
        except RoutingException as e:
             return f"Routing calculation failed: {str(e)}"
        except Exception as e:
             logger.exception("Unexpected routing error")
             return f"An unexpected error occurred during routing: {str(e)}"

        # 4. Format Output
        return await self._format_solution(solution, target_date, employees)

    async def _format_solution(self, solution: RoutingSolution, date: date_cls, employees: List[User]) -> str:
        lines = []
        lines.append(f"Proposed Schedule for {date.isoformat()}")
        
        # Metrics
        total_distance = solution.metrics.get("distance", 0) # meters
        total_duration = solution.metrics.get("duration", 0) # seconds
        
        # Convert to km and hours/min
        dist_km = total_distance / 1000
        dur_hrs = total_duration / 3600
        
        lines.append(f"Total Distance: {dist_km:.1f} km, Est. Time: {dur_hrs:.1f} hrs")
        lines.append("")
        
        start_time_base = datetime.combine(date, datetime.min.time()).replace(hour=9, minute=0)
        
        # Create map for employee names
        emp_map = {e.id: e.name or e.email or f"Employee {e.id}" for e in employees}
        
        # Per Employee
        for emp_id, steps in solution.routes.items():
            emp_name = emp_map.get(emp_id, f"Employee {emp_id}")
            
            lines.append(f"Technician: {emp_name}")
            if not steps:
                lines.append("  - No jobs assigned")
            else:
                current_time = start_time_base
                for step in steps:
                    j = step.job
                    # Use actual times from solution if available
                    if step.arrival_time and step.departure_time:
                        time_str = f"{step.arrival_time.strftime('%H:%M')} - {step.departure_time.strftime('%H:%M')}"
                    else:
                        # Fallback estimation
                        duration_mins = j.estimated_duration or 60
                        end_time = current_time + timedelta(minutes=duration_mins)
                        time_str = f"{current_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
                        current_time = end_time + timedelta(minutes=15)
                    
                    customer_name = j.customer.name if j.customer else "Unknown Customer"
                    desc = j.description or 'No description'
                    if len(desc) > 30:
                        desc = desc[:30] + "..."
                        
                    lines.append(f"  - {time_str}: {customer_name} ({desc})")

            lines.append("")

        if solution.unassigned_jobs:
            lines.append("Unassigned Jobs:")
            for j in solution.unassigned_jobs:
                customer_name = j.customer.name if j.customer else "Unknown"
                reason = " (Location missing or capacity full)"
                if j.latitude is None or j.longitude is None:
                     if j.customer and (j.customer.latitude is None or j.customer.longitude is None):
                        reason = " (Missing Geolocation)"
                
                lines.append(f"  - {customer_name}: {j.description}{reason}")
        
        return "\n".join(lines)
