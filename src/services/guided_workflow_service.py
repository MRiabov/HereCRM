from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Service, LineItem
from datetime import datetime, date
from sqlalchemy.orm import joinedload

class GuidedWorkflowService:
    @staticmethod
    async def get_next_job_for_employee(db: AsyncSession, employee_id: int) -> Optional[Job]:
        """
        Query pending jobs for today for a specific employee, ordered by scheduled time.
        Returns the first one.
        """
        today = date.today()
        # Create a statement to find pending jobs for the employee today
        # We use joinedload to avoid lazy loading issues later
        stmt = (
            select(Job)
            .options(
                joinedload(Job.customer),
                joinedload(Job.line_items).joinedload(LineItem.service)
            )
            .where(
                and_(
                    Job.employee_id == employee_id,
                    Job.status == "pending",
                    Job.scheduled_at >= datetime.combine(today, datetime.min.time()),
                    Job.scheduled_at <= datetime.combine(today, datetime.max.time())
                )
            )
            .order_by(Job.scheduled_at.asc())
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def format_next_job_message(job: Job) -> str:
        """
        Formats a message with next job details, map link, and reminders.
        """
        customer_name = job.customer.name if job.customer else "Unknown Customer"
        address = job.location or "No address provided"
        
        # Build Google Maps link
        if job.latitude and job.longitude:
            map_link = f"https://www.google.com/maps/search/?api=1&query={job.latitude},{job.longitude}"
        else:
            # Fallback to address search if coordinates are missing
            safe_address = address.replace(" ", "+")
            map_link = f"https://www.google.com/maps/search/?api=1&query={safe_address}"

        reminders = ""
        # Collect reminders from all services associated with the job
        reminder_list = []
        for item in job.line_items:
            if item.service and item.service.reminder_text:
                reminder_list.append(item.service.reminder_text)
        
        if reminder_list:
            # Deduplicate reminders if multiple line items have the same service
            unique_reminders = list(dict.fromkeys(reminder_list))
            reminders = "\n\nReminders:\n- " + "\n- ".join(unique_reminders)

        msg = f"Next up: {customer_name} at {address}.\n\nMap Link: {map_link}{reminders}"
        return msg
