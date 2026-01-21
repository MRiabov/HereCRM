from typing import Optional
from src.models import Job
from src.repositories import JobRepository

class AssignmentService:
    def __init__(self, session, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)

    async def assign_job(self, job_id: int, employee_id: int) -> Job:
        """
        Assign a job to an employee.
        """
        job = await self.job_repo.get_by_id(job_id, self.business_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.employee_id = employee_id
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def unassign_job(self, job_id: int) -> Job:
        """
        Remove the assignment from a job.
        """
        job = await self.job_repo.get_by_id(job_id, self.business_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.employee_id = None
        await self.session.commit()
        await self.session.refresh(job)
        return job
