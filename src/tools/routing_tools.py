
import asyncio
from datetime import date as date_cls, datetime, timedelta
from typing import List
import logging
from src.services.messaging_service import messaging_service

from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Business, JobStatus
from src.repositories import JobRepository, UserRepository
from src.services.routing.base import RoutingServiceProvider, RoutingSolution, RoutingException
from src.services.routing.ors import OpenRouteServiceAdapter
from src.services.routing.mock import MockRoutingService
from src.services.geocoding import GeocodingService
from src.uimodels import AutorouteTool
from src.config import settings
from src.services.template_service import TemplateService

logger = logging.getLogger(__name__)

class AutorouteToolExecutor:
    def __init__(self, session: AsyncSession, business_id: int, template_service: TemplateService):
        self.session = session
        self.business_id = business_id
        self.template_service = template_service
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

        # 2. Calculate Solution
        solution, employees_or_error = await self._calculate(target_date)
        if solution is None or not isinstance(employees_or_error, list):
            return str(employees_or_error)
        
        if input.apply:
            return await self.apply_schedule(solution, input.notify)
        
        # 3. Format Output
        routes_body = await self._format_solution_body(solution, employees_or_error)
        return self.template_service.render("autoroute_preview", date=target_date, routes=routes_body)

    async def _calculate(self, target_date: date_cls):
        """Internal helper to fetch data and call routing service."""
        # 1. Fetch data
        employees = await self.user_repo.get_team_members(self.business_id)
        if not employees:
            return None, "No employees found to route."

        # Jobs
        pending_jobs = await self.job_repo.search(query="all", business_id=self.business_id, status=JobStatus.pending)
        
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        scheduled_jobs = await self.job_repo.search(
            query="all", 
            business_id=self.business_id, 
            status=JobStatus.scheduled,
            min_date=start_of_day,
            max_date=end_of_day,
            query_type="scheduled"
        )
        
        all_jobs_map = {j.id: j for j in pending_jobs}
        for j in scheduled_jobs:
            all_jobs_map[j.id] = j
            
        all_jobs = list(all_jobs_map.values())
        
        # 1.5 Geocode missing locations
        if all_jobs:
            geocoder = GeocodingService()
            business = await self.session.get(Business, self.business_id)
            for job in all_jobs:
                if job.location and (not job.latitude or not job.longitude):
                    lat, lon, street, city, country, postcode, full_address = await geocoder.geocode(
                        job.location,
                        default_city=business.default_city if business else None,
                        default_country=business.default_country if business else None
                    )
                    if lat and lon:
                        job.latitude = lat
                        job.longitude = lon
                        if postcode and not job.postal_code:
                            job.postal_code = postcode
        
        if not all_jobs:
            return None, f"No jobs found to route for {target_date} (checked pending and scheduled)."

        # 2. Call Service
        try:
             loop = asyncio.get_running_loop()
             solution = await loop.run_in_executor(None, self.routing_service.calculate_routes, all_jobs, employees)
             return solution, employees
        except RoutingException as e:
             return None, f"Routing calculation failed: {str(e)}"
        except Exception as e:
             logger.exception("Unexpected routing error")
             return None, f"An unexpected error occurred during routing: {str(e)}"

    async def apply_schedule(self, solution: RoutingSolution, notify: bool) -> str:
        count = 0
        try:
            # We use the session transaction
            for emp_id, steps in solution.routes.items():
                # Find employee for notification
                employee = await self.user_repo.get_by_id(emp_id)

                for step in steps:
                    job = step.job
                    # Update job fields
                    job.employee_id = emp_id
                    job.status = JobStatus.scheduled
                    
                    if step.arrival_time:
                        # Arrival time is when the technician is expected to start/arrive
                        job.scheduled_at = step.arrival_time
                    
                    count += 1

                    if notify:
                        # 1. Notify Employee
                        if employee and employee.phone_number:
                            await messaging_service.enqueue_message(
                                recipient_phone=employee.phone_number,
                                content=f"New job assigned: {job.description} at {job.scheduled_at.strftime('%H:%M') if job.scheduled_at else 'N/A'}",
                                trigger_source="autoroute_assignment"
                            )
                        
                        # 2. Notify Customer (Placeholder as per Spec 013 "handoff to Msg Spec")
                        if job.customer and job.customer.phone:
                            # Just log for now to avoid spamming customers during testing/MVP
                            logger.info(f"Notification hook: Customer {job.customer.name} would be notified about job {job.id}")
            
            await self.session.commit()
            return self.template_service.render("autoroute_applied", count=count)
            
        except Exception as e:
            await self.session.rollback()
            logger.exception("Failed to apply routing schedule")
            return f"Failed to apply schedule: {str(e)}"

    async def _format_solution_body(self, solution: RoutingSolution, employees: List[User]) -> str:
        lines = []
        # Header is handled by template
        
        # Metrics
        total_distance = solution.metrics.get("distance", 0) # meters
        total_duration = solution.metrics.get("duration", 0) # seconds
        
        # Convert to km and hours/min
        dist_km = total_distance / 1000
        dur_hrs = total_duration / 3600
        
        lines.append(f"Total Distance: {dist_km:.1f} km, Est. Time: {dur_hrs:.1f} hrs")
        lines.append("")
        
        # Start time base is no longer needed to be calculated here for header, 
        # but is used for simulation below.
        # We need 'date' or we assume today/target date passed in?
        # The original method took 'date'.
        # Let's derive date from solution or just use a default since it's just for time calcs?
        # Actually, the original code used 'date' to set start_time_base.
        # I removed 'date' from args in my previous call.
        # I should restore 'date' access or pass it.
        # Or, I can just use datetime.today() if it's just for setting the hour to 9am.
        start_time_base = datetime.today().replace(hour=9, minute=0, second=0, microsecond=0)
        
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
