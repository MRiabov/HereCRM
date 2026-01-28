from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import User, Job, JobStatus
from typing import Tuple, List

class TimeTrackingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_in(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.current_shift_start = datetime.now(timezone.utc)
        await self.session.commit()
        return user

    async def check_out(self, user_id: int) -> Tuple[User, datetime, datetime, List[Job]]:
        user = await self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if not user.current_shift_start:
            raise ValueError("Not checked in")
        
        # Ensure aware
        start_time = user.current_shift_start
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        end_time = datetime.now(timezone.utc)
        
        # Fetch jobs completed during this shift
        stmt = select(Job).where(
            Job.employee_id == user_id,
            Job.status == JobStatus.COMPLETED,
            Job.completed_at >= start_time
        ).order_by(Job.completed_at.asc())
        
        result = await self.session.execute(stmt)
        completed_jobs = result.scalars().all()
        
        user.current_shift_start = None
        await self.session.commit()
        
        return user, start_time, end_time, completed_jobs

    async def start_job(self, job_id: int, user_id: int) -> Job:
        # [FEATURE-005] Enforce one running job at a time
        stmt = select(Job).where(
            Job.employee_id == user_id,
            Job.status == JobStatus.IN_PROGRESS,
            Job.id != job_id
        )
        result = await self.session.execute(stmt)
        active_job = result.scalar_one_or_none()
        
        if active_job:
            raise ValueError(f"Cannot start job: You already have an active job in progress (Job #{active_job.id}). Please pause it or finish it first.")

        job = await self.session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # If resuming from paused, begun_at will be set to now
        job.begun_at = datetime.now(timezone.utc)
        job.status = JobStatus.IN_PROGRESS
        job.employee_id = user_id
        await self.session.commit()
        return job

    async def pause_job(self, job_id: int) -> Job:
        job = await self.session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != JobStatus.IN_PROGRESS or not job.begun_at:
            return job # Already not in progress
            
        # Ensure aware
        start_time = job.begun_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        job.total_actual_duration_seconds += int(duration.total_seconds())
        job.begun_at = None
        job.status = JobStatus.PAUSED
        await self.session.commit()
        return job

    async def finish_job(self, job_id: int) -> Tuple[Job, int]:
        job = await self.session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status not in [JobStatus.IN_PROGRESS, JobStatus.PAUSED]:
            raise ValueError("Job not started")

        total_duration = job.total_actual_duration_seconds
        
        if job.status == JobStatus.IN_PROGRESS and job.begun_at:
            # Ensure aware
            start_time = job.begun_at
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
                
            end_time = datetime.now(timezone.utc)
            duration = end_time - start_time
            total_duration += int(duration.total_seconds())
        
        job.total_actual_duration_seconds = total_duration
        job.begun_at = None
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        
        return job, total_duration
