import logging
from typing import Any
from datetime import datetime
from sqlalchemy import select
from src.events import event_bus, JOB_CREATED, JOB_UPDATED, JOB_ASSIGNED, JOB_UNASSIGNED, JOB_SCHEDULED
from src.database import AsyncSessionLocal
from src.repositories import JobRepository, UserRepository
from src.services.google_calendar_service import GoogleCalendarService
from src.models import Job, JobStatus

logger = logging.getLogger(__name__)

class CalendarSyncHandler:
    """
    Handles event-driven synchronization between HereCRM Jobs and Google Calendar.
    """
    def __init__(self):
        self.gcal_service = GoogleCalendarService()

    def register(self):
        """Register the handlers with the event bus."""
        event_bus.subscribe(JOB_CREATED, self.handle_job_created)
        event_bus.subscribe(JOB_UPDATED, self.handle_job_updated)
        event_bus.subscribe(JOB_SCHEDULED, self.handle_job_scheduled)
        event_bus.subscribe(JOB_ASSIGNED, self.handle_job_assigned)
        event_bus.subscribe(JOB_UNASSIGNED, self.handle_job_unassigned)
        logger.info("CalendarSyncHandler registered for Job events")

    async def handle_job_created(self, data: dict):
        # Only relevant if it's assigned at creation
        await self._sync_job(data.get("job_id"), data.get("business_id"))

    async def handle_job_updated(self, data: dict):
        await self._sync_job(data.get("job_id"), data.get("business_id"))

    async def handle_job_scheduled(self, data: dict):
        await self._sync_job(data.get("job_id"), data.get("business_id"))

    async def handle_job_assigned(self, data: dict):
        await self._sync_job(data.get("job_id"), data.get("business_id"))

    async def handle_job_unassigned(self, data: dict):
        # We need to delete the event from the old user's calendar
        job_id = int(data.get("job_id")) if data.get("job_id") else None
        employee_id = int(data.get("employee_id")) if data.get("employee_id") else None
        business_id = int(data.get("business_id")) if data.get("business_id") else None
        
        if not job_id or not employee_id or not business_id:
            return

        async with AsyncSessionLocal() as db:
            user_repo = UserRepository(db)
            job_repo = JobRepository(db)
            
            user = await user_repo.get_by_id(employee_id)
            job = await job_repo.get_by_id(job_id, business_id)
            
            if user and job and job.gcal_event_id:
                success = await self.gcal_service.delete_event(job.gcal_event_id, user, db)
                if success:
                    job.gcal_event_id = None
                    await db.commit()

    async def sync_all_user_jobs(self, user_id: int):
        """Sync all upcoming assigned jobs for a user to their Google Calendar."""
        async with AsyncSessionLocal() as db:
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            
            if not user or not user.google_calendar_sync_enabled:
                return

            # Fetch all upcoming jobs for this user
            from sqlalchemy.orm import selectinload
            stmt = (
                select(Job)
                .where(
                    Job.employee_id == user_id,
                    Job.scheduled_at >= datetime.now(),
                    Job.status != JobStatus.COMPLETED,
                    Job.status != JobStatus.CANCELLED
                )
                .options(selectinload(Job.customer))
            )
            result = await db.execute(stmt)
            jobs = result.scalars().all()
            
            for job in jobs:
                if job.gcal_event_id:
                    await self.gcal_service.update_event(job, user, db)
                elif job.scheduled_at:
                    event_id = await self.gcal_service.create_event(job, user, db)
                    if event_id:
                        job.gcal_event_id = event_id
            
            await db.commit()

    async def _sync_job(self, job_id_raw: Any, business_id_raw: Any):
        if job_id_raw is None or business_id_raw is None:
            return
            
        job_id = int(job_id_raw)
        business_id = int(business_id_raw)

        async with AsyncSessionLocal() as db:
            user_repo = UserRepository(db)
            
            # Fetch job with customer loaded
            from sqlalchemy.orm import selectinload
            stmt = (
                select(Job)
                .where(Job.id == job_id, Job.business_id == business_id)
                .options(selectinload(Job.customer))
            )
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            
            if not job or not job.employee_id:
                return

            user = await user_repo.get_by_id(job.employee_id)
            if not user or not user.google_calendar_sync_enabled:
                return

            if job.gcal_event_id:
                if job.scheduled_at:
                    # Update existing
                    await self.gcal_service.update_event(job, user, db)
                else:
                    # Job was unscheduled, delete the event
                    success = await self.gcal_service.delete_event(job.gcal_event_id, user, db)
                    if success:
                        job.gcal_event_id = None
            elif job.scheduled_at:
                # Create brand new
                event_id = await self.gcal_service.create_event(job, user, db)
                if event_id:
                    job.gcal_event_id = event_id
            
            await db.commit()

# Global Instance
calendar_sync_handler = CalendarSyncHandler()
