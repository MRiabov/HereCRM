from datetime import date, datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc
from sqlalchemy.orm import selectinload, joinedload

from src.models import Job, User, UserRole, Invoice, Customer
from src.schemas.pwa import ActivityType

class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_monthly_revenue(self, business_id: int) -> float:
        """
        Sum of job values for jobs scheduled in the current month that are not cancelled.
        """
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        stmt = select(func.sum(Job.value)).where(
            Job.business_id == business_id,
            Job.scheduled_at >= start_of_month,
            Job.status != "cancelled"
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0.0

    async def get_recent_activity(self, business_id: int, limit: int = 10) -> List[dict]:
        """
        Fetch recent activities across jobs, invoices, and customers.
        """
        activities = []
        
        # 1. Recent Invoices
        stmt = (
            select(Invoice)
            .join(Job)
            .where(Job.business_id == business_id)
            .options(joinedload(Invoice.job).joinedload(Job.customer))
            .order_by(desc(Invoice.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        invoices = result.scalars().unique().all()
        for inv in invoices:
            activities.append({
                "type": ActivityType.INVOICE,
                "title": "Invoice Generated",
                "description": f"Invoice generated for {inv.job.customer.name} - ${inv.job.value or 0.0:.2f}",
                "timestamp": inv.created_at
            })
            
        # 2. Recent Jobs
        stmt = (
            select(Job)
            .where(Job.business_id == business_id)
            .options(joinedload(Job.customer))
            .order_by(desc(Job.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().unique().all()
        for job in jobs:
            activities.append({
                "type": ActivityType.JOB,
                "title": "New Job",
                "description": f"Job created for {job.customer.name}: {job.description}",
                "timestamp": job.created_at
            })
            
        # 3. Recent Customers
        stmt = (
            select(Customer)
            .where(Customer.business_id == business_id)
            .order_by(desc(Customer.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        customers = result.scalars().all()
        for cust in customers:
            activities.append({
                "type": ActivityType.LEAD,
                "title": "New Customer",
                "description": f"Customer {cust.name} added to pipeline",
                "timestamp": cust.created_at
            })
            
        # Sort combined and limit
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]

    async def get_employee_schedules(self, business_id: int, target_date: date, timezone_str: str = "UTC") -> Dict[Optional[User], List[Job]]:
        """
        Query all users with roles member or owner for the business.
        Query all jobs for the given date assigned to these users OR unassigned.
        Return a structured dict: {user_obj_or_None: [job_list]}.
        
        The query is timezone-aware: target_date is interpreted in timezone_str.
        """
        import pytz
        try:
            tz = pytz.timezone(timezone_str)
        except Exception:
            tz = pytz.UTC

        # 1. Fetch all employees (Owners and Members)
        stmt = select(User).where(
            User.business_id == business_id,
            User.role.in_([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])
        )
        result = await self.session.execute(stmt)
        employees = result.scalars().all()

        # 2. Fetch jobs for these employees on the target date
        # Convert local date range to UTC
        local_start = datetime.combine(target_date, datetime.min.time())
        local_end = datetime.combine(target_date, datetime.max.time())
        
        # Localize and then normalize to UTC
        start_of_day = tz.localize(local_start).astimezone(pytz.UTC)
        end_of_day = tz.localize(local_end).astimezone(pytz.UTC)

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
            selectinload(Job.employee).selectinload(User.wage_config),
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
        Query all jobs where (employee_id is None OR scheduled_at is None) AND status is pending/open.
        """
        stmt = select(Job).where(
            Job.business_id == business_id,
            or_(
                Job.employee_id.is_(None),
                Job.scheduled_at.is_(None)
            ),
            Job.status.in_(["pending", "open"])
        ).options(
            selectinload(Job.customer),
            selectinload(Job.employee),
            selectinload(Job.employee).selectinload(User.wage_config),
            selectinload(Job.line_items)
        ).order_by(Job.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
