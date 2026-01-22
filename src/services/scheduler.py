import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Callable, List, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import User, UserRole, Job
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
            logger.info("SchedulerService started.")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("SchedulerService stopped.")

    def add_daily_job(self, func, hour=6, minute=30, id="daily_shift_check"):
        """Add a job to run daily at a specific UTC time."""
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone.utc)
        self.scheduler.add_job(func, trigger, id=id, replace_existing=True)
        logger.info(f"Added daily job '{id}' at {hour}:{minute} UTC")

    async def check_shifts(self):
        """
        Daily check to notify employees about their jobs.
        """
        logger.info("Running check_shifts...")
        try:
            async with AsyncSessionLocal() as session:
                # 1. Find all EMPLOYEES
                stmt = select(User).where(User.role == UserRole.EMPLOYEE)
                result = await session.execute(stmt)
                employees = result.scalars().all()

                if not employees:
                    logger.info("No employees found for shift notification.")
                    return

                # 2. For each employee, check for jobs today
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)

                logger.info(f"Checking shifts for {len(employees)} employees for date {today_start.date()}")

                for employee in employees:
                    if not employee.phone_number:
                        continue

                    # Find jobs assigned to this employee scheduled for today
                    stmt_jobs = select(Job).where(
                        Job.employee_id == employee.id,
                        Job.scheduled_at >= today_start,
                        Job.scheduled_at < today_end,
                        Job.status != 'completed'
                    ).order_by(Job.scheduled_at)
                    
                    result_jobs = await session.execute(stmt_jobs)
                    jobs = result_jobs.scalars().all()

                    if not jobs:
                        continue

                    # 3. Generate Summary
                    summary_lines = [f"🌅 Morning Overview for {employee.name or 'Employee'}:"]
                    summary_lines.append(f"You have {len(jobs)} jobs scheduled for today.")
                    
                    for job in jobs:
                        time_str = job.scheduled_at.strftime("%H:%M") if job.scheduled_at else "Time TBD"
                        loc = job.location or "No location"
                        desc = job.description or "No description"
                        summary_lines.append(f"- {time_str}: {desc} @ {loc}")

                    summary_lines.append("\nReply 'Start shift' when you are ready to begin.")

                    # 4. Enqueue Message
                    summary_text = "\n".join(summary_lines)
                    await messaging_service.enqueue_message(
                        recipient_phone=employee.phone_number,
                        content=summary_text,
                        channel="whatsapp",
                        trigger_source="scheduler"
                    )
                    logger.info(f"Enqueued shift summary for {employee.id}")

        except Exception as e:
            logger.error(f"Error in check_shifts: {e}")
scheduler_service = SchedulerService()
