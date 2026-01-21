from datetime import date, datetime, time
from typing import Dict, List
from sqlalchemy import select, and_
from src.models import User, Job
from src.repositories import UserRepository, JobRepository

class DashboardService:
    def __init__(self, session, business_id: int):
        self.session = session
        self.business_id = business_id
        self.user_repo = UserRepository(session)
        self.job_repo = JobRepository(session)

    async def get_employee_schedules(self, business_id: int, date_obj: date) -> Dict[User, List[Job]]:
        """
        Query all team members and their jobs for a specific date.
        """
        # 1. Get all team members (owners and members)
        team_members = await self.user_repo.get_team_members(business_id)

        # 2. Query jobs for the specified date
        start_of_day = datetime.combine(date_obj, time.min)
        end_of_day = datetime.combine(date_obj, time.max)
        
        # Use existing search capabilities
        jobs = await self.job_repo.search(
            query="all",
            business_id=business_id,
            min_date=start_of_day,
            max_date=end_of_day
        )

        # 3. Group jobs by employee
        schedule = {user: [] for user in team_members}
        user_map = {user.id: user for user in team_members}
        
        for job in jobs:
            if job.employee_id in user_map:
                schedule[user_map[job.employee_id]].append(job)
                
        return schedule

    async def get_unscheduled_jobs(self, business_id: int) -> List[Job]:
        """
        Query all jobs in the business that have no employee assigned.
        """
        stmt = select(Job).where(
            and_(
                Job.business_id == business_id,
                Job.employee_id == None,
                Job.status.in_(["pending", "open"])
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
