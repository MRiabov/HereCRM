from datetime import date, datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from src.models import Job, User, UserRole

class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_employee_schedules(self, business_id: int, target_date: date) -> Dict[Optional[User], List[Job]]:
        """
        Query all users with roles member or owner for the business.
        Query all jobs for the given date assigned to these users OR unassigned.
        Return a structured dict: {user_obj_or_None: [job_list]}.
        """
        # 1. Fetch all employees (Owners and Members)
        stmt = select(User).where(
            User.business_id == business_id,
            User.role.in_([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])
        )
        result = await self.session.execute(stmt)
        employees = result.scalars().all()

        # 2. Fetch jobs for these employees on the target date
        # We assume scheduled_at is a datetime, so we check the date part
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Pre-initialize the schedule map
        schedule: Dict[Optional[User], List[Job]] = {emp: [] for emp in employees}
        schedule[None] = []  # Entry for unassigned jobs

        # Query jobs assigned to any of these employees OR unassigned on this date
        employee_ids = [emp.id for emp in employees]
        
        job_stmt = select(Job).where(
            Job.business_id == business_id,
            or_(
                Job.employee_id.in_(employee_ids) if employee_ids else False,
                Job.employee_id.is_(None)
            ),
            Job.scheduled_at >= start_of_day,
            Job.scheduled_at <= end_of_day
        ).options(
            selectinload(Job.customer),
            selectinload(Job.employee),
            selectinload(Job.line_items)
        ).order_by(Job.scheduled_at.asc())

        job_result = await self.session.execute(job_stmt)
        jobs = job_result.scalars().all()

        # Group jobs by employee
        for job in jobs:
            if job.employee_id is None:
                schedule[None].append(job)
                continue
                
            for emp in employees:
                if job.employee_id == emp.id:
                    schedule[emp].append(job)
                    break

        return schedule

    async def get_unscheduled_jobs(self, business_id: int) -> List[Job]:
        """
        Query all jobs where employee_id is None AND status is pending/open.
        """
        stmt = select(Job).where(
            Job.business_id == business_id,
            Job.employee_id.is_(None),
            Job.status.in_(["pending", "open"])
        ).order_by(Job.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
