from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Job, Customer, PipelineStage, Business, PaymentTiming
from src.repositories import JobRepository, CustomerRepository, RequestRepository
from src.events import event_bus
from datetime import datetime, timedelta, timezone
from src.services.quote_service import QuoteService


class CRMService:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)
        self.quote_service = QuoteService(session)

    async def create_job(
        self,
        customer_id: int,
        description: Optional[str] = None,
        value: Optional[float] = None,
        location: Optional[str] = None,
        status: str = "pending",
        scheduled_at: Optional[datetime] = None,
        line_items: Optional[list] = None,
        postal_code: Optional[str] = None,
    ) -> Job:
        # [T009] Check payment timing
        paid = False
        business = await self.session.get(Business, self.business_id)
        if business and business.workflow_payment_timing == PaymentTiming.ALWAYS_PAID_ON_SPOT:
            paid = True

        job = Job(
            business_id=self.business_id,
            customer_id=customer_id,
            description=description,
            value=value,
            location=location,
            status=status,
            scheduled_at=scheduled_at,
            line_items=line_items or [],
            postal_code=postal_code,
            paid=paid,
        )
        self.job_repo.add(job)
        await self.session.commit() # Must commit for other sessions (handlers) to see it

        # Emit event
        await event_bus.emit(
            "JOB_CREATED",
            {"job_id": job.id, "customer_id": customer_id, "business_id": self.business_id},
        )
        return job

    async def get_active_job_for_customer(self, phone_number: str) -> Optional[Job]:
        customer = await self.customer_repo.get_by_phone(phone_number, self.business_id)
        if not customer:
            return None

        # Fetch active or upcoming jobs for this customer
        # Uses simplistic filtering in Python for now as active window logic is complex in SQL
        stmt = (
            select(Job)
            .where(Job.customer_id == customer.id)
            .order_by(Job.scheduled_at.desc())
            .limit(10)
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        now = datetime.now(timezone.utc)
        
        for job in jobs:
            if not job.scheduled_at:
                continue
                
            # Ensure scheduled_at is aware
            start = job.scheduled_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
                
            duration_min = job.estimated_duration or 60
            end = start + timedelta(minutes=duration_min)
            
            # Allow 30m buffer before and after
            buffered_start = start - timedelta(minutes=30)
            buffered_end = end + timedelta(minutes=30)
            
            if buffered_start <= now <= buffered_end:
                return job
                
        return None

    async def convert_request(
        self,
        query: str,
        action: str,
        time: Optional[str] = None,
        iso_time: Optional[str] = None,
    ) -> tuple[str, Optional[dict]]:
        # Find the request
        requests = await self.request_repo.search(query, self.business_id)
        if not requests:
            return f"Could not find request matching '{query}'", None

        req = requests[0]

        if action == "schedule":
            # Promotion logic: Request -> Job
            customers = await self.customer_repo.search(query, self.business_id)
            if not customers:
                all_customers = await self.customer_repo.get_all(self.business_id)
                if all_customers:
                    customer_id = all_customers[0].id
                else:
                    new_customer = Customer(
                        name="General Customer", business_id=self.business_id
                    )
                    self.customer_repo.add(new_customer)
                    await self.session.flush()
                    customer_id = new_customer.id
            else:
                customer_id = customers[0].id

            scheduled_at = None
            if iso_time:
                try:
                    scheduled_at = datetime.fromisoformat(
                        iso_time.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            job = await self.create_job(
                customer_id=customer_id,
                description=f"Converted from request: {req.content}. Time: {time or 'N/A'}",
                status="scheduled" if time else "pending",
                scheduled_at=scheduled_at,
            )
            await self.session.delete(req)
            await self.session.commit()
            await self.session.refresh(job)

            return f"✔ Converted Request to Job: {job.description}", {
                "action": "promote",
                "entity": "job",
                "id": job.id,
                "old_request_content": req.content,
                "description": job.description,
            }

        elif action == "complete":
            old_status = req.status
            req.status = "completed"
            return f"✔ Request marked as completed: {req.content[:30]}", {
                "action": "update",
                "entity": "request",
                "id": req.id,
                "old_status": old_status,
            }

        elif action == "quote":
            # Promotion logic: Request -> Quote
            customers = await self.customer_repo.search(query, self.business_id)
            if not customers:
                # Same fallback as schedule
                all_customers = await self.customer_repo.get_all(self.business_id)
                if all_customers:
                    customer_id = all_customers[0].id
                else:
                    new_customer = Customer(
                        name="General Customer", business_id=self.business_id
                    )
                    self.customer_repo.add(new_customer)
                    await self.session.flush()
                    customer_id = new_customer.id
            else:
                customer_id = customers[0].id

            quote = await self.quote_service.create_from_request(
                request_id=req.id,
                customer_id=customer_id
            )
            
            # Deletion logic matches 'schedule' action
            await self.session.delete(req)
            await self.session.commit()
            await self.session.refresh(quote)

            return f"✔ Converted Request to Quote: {req.content[:50]}", {
                "action": "promote",
                "entity": "quote",
                "id": quote.id,
                "old_request_content": req.content,
                "customer_name": customers[0].name if customers else "General Customer",
            }

        return f"Unknown action: {action}", None

    async def get_pipeline_summary(self) -> dict:
        summary_data = await self.customer_repo.get_pipeline_summary(self.business_id)
        return {
            stage.value: {
                "count": data["count"],
                "examples": [c.name for c in data["examples"]],
            }
            for stage, data in summary_data.items()
        }

    async def format_pipeline_summary(self) -> str:
        summary = await self.get_pipeline_summary()
        lines = ["### Pipeline Breakdown"]
        # Order them logically if possible, or just alphabetical
        stages = [
            "not_contacted",
            "contacted",
            "converted_once",
            "converted_recurrent",
            "not_interested",
            "lost",
        ]
        for stage_key in stages:
            if stage_key not in summary:
                continue
            data = summary[stage_key]
            count = data["count"]
            examples = data["examples"]
            name = stage_key.replace("_", " ").title()
            line = f"- **{name}**: {count} customer{'s' if count != 1 else ''}"
            if examples:
                line += f" ({', '.join(examples)})"
            lines.append(line)
        return "\n".join(lines)

    async def update_customer_stage(self, customer_id: int, stage: str) -> Customer:
        customer = await self.customer_repo.get_by_id(customer_id, self.business_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} not found.")

        try:
            new_stage = PipelineStage(stage)
        except ValueError:
            raise ValueError(f"Invalid pipeline stage: {stage}")

        customer.pipeline_stage = new_stage
        await self.session.flush()
        return customer

    async def update_job(
        self,
        job_id: int,
        description: Optional[str] = None,
        status: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Job:
        job = await self.job_repo.get_by_id(job_id, self.business_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found.")

        old_scheduled_at = job.scheduled_at

        if description is not None:
            job.description = description
        if status is not None:
            job.status = status
        if scheduled_at is not None:
            job.scheduled_at = scheduled_at

        await self.session.commit()
        await self.session.refresh(job)

        # Emit JOB_SCHEDULED if scheduled_at changed and is now set
        if scheduled_at and scheduled_at != old_scheduled_at:
            await event_bus.emit(
                "JOB_SCHEDULED",
                {
                    "job_id": job.id,
                    "customer_id": job.customer_id,
                    "business_id": self.business_id,
                    "scheduled_at": scheduled_at.isoformat(),
                },
            )

        return job

