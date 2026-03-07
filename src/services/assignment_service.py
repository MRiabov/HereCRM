from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel, ConfigDict

from src.models import Job, User
from src.repositories import JobRepository, UserRepository
from src.events import event_bus, JOB_ASSIGNED, JOB_UNASSIGNED


class AssignmentResult(BaseModel):
    success: bool
    warning: Optional[str] = None
    job: Optional[Job] = None
    error: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )  # Replaced class Config with model_config


class AssignmentService:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)
        self.user_repo = UserRepository(session)

    async def find_employee_by_name(self, name_fragment: str) -> List[User]:
        """
        Find employees by fuzzy name match or email.
        T005: Interpret user commands like "Assign to Bob".
        """
        if not name_fragment:
            return []

        # Case-insensitive match on name or email
        # We limit to the current business
        stmt = select(User).where(
            User.business_id == self.business_id,
            or_(
                User.name.ilike(f"%{name_fragment}%"),
                User.email.ilike(f"%{name_fragment}%"),
            ),
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_job(self, job_id: int, employee_id: int) -> AssignmentResult:
        """
        Assign a job to an employee with validation.
        T006: Enhanced Assign Job Logic.
        """
        # Validation 3: Verify job exists
        job = await self.job_repo.get_by_id(job_id, self.business_id)
        if not job:
            return AssignmentResult(success=False, error=f"Job {job_id} not found")

        # Validation 1: Ensure employee_id belongs to the same business
        employee = await self.user_repo.get_by_id(employee_id)
        if not employee or employee.business_id != self.business_id:
            return AssignmentResult(
                success=False,
                error=f"Employee {employee_id} not found or not in business",
            )

        warning = None
        # Validation 2: Ensure (softly) no overlap.
        # Check if employee has another job at job.scheduled_at
        if job.scheduled_at:
            # Simple conflict detection: Exact match on scheduled_at
            # In a real system, we'd check duration overlap.
            conflict_stmt = select(Job).where(
                Job.business_id == self.business_id,
                Job.employee_id == employee_id,
                Job.scheduled_at == job.scheduled_at,
                Job.id != job_id,
            )
            conflict_res = await self.session.execute(conflict_stmt)
            conflicts = conflict_res.scalars().all()

            if conflicts:
                warning = "Double booked"

        # Apply assignment
        old_employee_id = job.employee_id
        if old_employee_id and old_employee_id != employee_id:
            # It's a reassignment. First, unassign the old employee.
            job.employee_id = None
            await self.session.commit()
            await self.session.refresh(job)

            await event_bus.emit(
                JOB_UNASSIGNED,
                {
                    "job_id": job.id,
                    "employee_id": old_employee_id,
                    "business_id": self.business_id,
                },
            )
            # The event handlers run in isolated sessions and may clear gcal_event_id.
            # Refresh to get any changes they made.
            await self.session.refresh(job)

            # Explicitly clear gcal_event_id to ensure external syncs clean up correctly
            job.gcal_event_id = None

        job.employee_id = employee_id
        await self.session.commit()
        await self.session.refresh(job)

        await event_bus.emit(
            JOB_ASSIGNED,
            {
                "job_id": job.id,
                "employee_id": employee_id,
                "business_id": self.business_id,
            },
        )

        return AssignmentResult(success=True, warning=warning, job=job)

    async def unassign_job(self, job_id: int) -> AssignmentResult:
        """
        Remove assignment from a job.
        Base requirement from WP01.
        """
        job = await self.job_repo.get_by_id(job_id, self.business_id)
        if not job:
            return AssignmentResult(success=False, error=f"Job {job_id} not found")

        old_employee_id = job.employee_id
        job.employee_id = None
        await self.session.commit()
        await self.session.refresh(job)

        if old_employee_id:
            await event_bus.emit(
                JOB_UNASSIGNED,
                {
                    "job_id": job.id,
                    "employee_id": old_employee_id,
                    "business_id": self.business_id,
                },
            )

        return AssignmentResult(success=True, job=job)
