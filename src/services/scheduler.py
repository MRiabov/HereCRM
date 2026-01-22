import logging
from datetime import datetime, timezone, timedelta
from typing import Callable, List, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models import User, Job
from src.services.messaging_service import messaging_service

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Service responsible for scheduling background tasks, such as daily shift summaries.
    Wraps AsyncIOScheduler.
    """
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler service started.")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler service stopped.")

    def add_daily_job(self, func: Callable, hour: int = 6, minute: int = 30):
        """Add a job to run daily at a specific time (UTC)."""
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone.utc)
        self.scheduler.add_job(func, trigger)
        logger.info(f"Added daily job '{func.__name__}' at {hour:02d}:{minute:02d} UTC")

    async def check_shifts(self):
        """
        Check for employees starting their shift and send them a summary.
        This function identifies users with jobs scheduled for the current day
        and sends them a formatted summary via the MessagingService.
        """
        logger.info("Running check_shifts task...")
        
        async with AsyncSessionLocal() as session:
            try:
                # Fetch all users with jobs scheduled for 'today'
                # We define 'today' based on UTC for now (MVP).
                # In a production app, we would process per-user timezone.
                now = datetime.now(timezone.utc)
                start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)

                # Query jobs in range with an assigned employee
                stmt = select(Job).where(
                    Job.scheduled_at >= start_of_day,
                    Job.scheduled_at < end_of_day,
                    Job.employee_id.is_not(None)
                )
                result = await session.execute(stmt)
                jobs = result.scalars().all()

                # Group by employee
                jobs_by_employee: Dict[int, List[Job]] = {}
                for job in jobs:
                    if job.employee_id is not None:
                        if job.employee_id not in jobs_by_employee:
                            jobs_by_employee[job.employee_id] = []
                        jobs_by_employee[job.employee_id].append(job)

                if not jobs_by_employee:
                    logger.info("No jobs found for today.")
                    return

                # Fetch users corresponding to these jobs
                user_ids = list(jobs_by_employee.keys())
                user_stmt = select(User).where(User.id.in_(user_ids))
                user_result = await session.execute(user_stmt)
                users = {u.id: u for u in user_result.scalars().all()}

                # Send notifications
                for emp_id, emp_jobs in jobs_by_employee.items():
                    user = users.get(emp_id)
                    if not user or not user.phone_number:
                        continue
                    
                    # Sort jobs by time
                    emp_jobs.sort(key=lambda x: x.scheduled_at or datetime.max.replace(tzinfo=timezone.utc))

                    summary_lines = [f"📅 *Your Schedule for {now.strftime('%A, %b %d')}*"]
                    for job in emp_jobs:
                        time_str = job.scheduled_at.strftime("%H:%M") if job.scheduled_at else "Time TBD"
                        description = job.description or "No description"
                        location = job.location or "No location provided"
                        summary_lines.append(f"• {time_str}: {description} @ {location}")
                    
                    summary_msg = "\n".join(summary_lines)
                    
                    # Enqueue message
                    await messaging_service.enqueue_message(
                        recipient_phone=user.phone_number,
                        content=summary_msg,
                        channel="whatsapp", # enforcing whatsapp for rich text
                        trigger_source="scheduler_shift_start"
                    )
                    logger.info(f"Sent schedule summary to user {user.id} ({user.phone_number})")

            except Exception as e:
                logger.error(f"Error in check_shifts: {e}", exc_info=True)

# Global instance
scheduler_service = SchedulerService()
