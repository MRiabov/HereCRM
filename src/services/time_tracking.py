from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import User, Job
from typing import Optional, Tuple

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

    async def check_out(self, user_id: int) -> Tuple[User, datetime, datetime]:
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
        
        user.current_shift_start = None
        await self.session.commit()
        
        return user, start_time, end_time

    async def start_job(self, job_id: int, user_id: int) -> Job:
        job = await self.session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Use begun_at instead of started_at as per WP02 implementation
        job.begun_at = datetime.now(timezone.utc)
        job.status = "in_progress"
        job.employee_id = user_id
        await self.session.commit()
        return job

    async def finish_job(self, job_id: int) -> Tuple[Job, datetime, datetime]:
        job = await self.session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if not job.begun_at:
            raise ValueError("Job not started")
        
        # Ensure aware
        start_time = job.begun_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        end_time = datetime.now(timezone.utc)
        
        job.begun_at = None
        job.status = "completed"
        await self.session.commit()
        
        return job, start_time, end_time
