from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Customer
from src.repositories import JobRepository, CustomerRepository, RequestRepository


from datetime import datetime
from src.events import event_bus


class CRMService:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)

    async def create_job(
        self,
        customer_id: int,
        description: Optional[str] = None,
        value: Optional[float] = None,
        location: Optional[str] = None,
        status: str = "pending",
        scheduled_at: Optional[datetime] = None,
    ) -> Job:
        job = Job(
            business_id=self.business_id,
            customer_id=customer_id,
            description=description,
            value=value,
            location=location,
            status=status,
            scheduled_at=scheduled_at,
        )
        self.job_repo.add(job)
        await self.session.commit() # Must commit for other sessions (handlers) to see it

        # Emit event
        await event_bus.emit(
            "JOB_CREATED",
            {"job_id": job.id, "customer_id": customer_id, "business_id": self.business_id},
        )
        return job

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
            await self.session.flush()

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

        elif action == "log":
            old_status = req.status
            req.status = "logged"
            return f"✔ Request logged: {req.content[:30]}", {
                "action": "update",
                "entity": "request",
                "id": req.id,
                "old_status": old_status,
            }

        return f"Unknown action: {action}", None

    async def get_pipeline_summary(self) -> dict:
        summary_data = await self.customer_repo.get_pipeline_summary(self.business_id)
        return {
            stage.value: {
                "count": len(customers),
                "examples": [c.name for c in customers[:5]],
            }
            for stage, customers in summary_data.items()
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

