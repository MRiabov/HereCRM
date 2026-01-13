from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Customer
from src.repositories import JobRepository, CustomerRepository, RequestRepository


class CRMService:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)

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

            job = Job(
                business_id=self.business_id,
                customer_id=customer_id,
                description=f"Converted from request: {req.content}. Time: {time or 'N/A'}",
                status="scheduled" if time else "pending",
            )
            if iso_time:
                from datetime import datetime

                try:
                    job.scheduled_at = datetime.fromisoformat(
                        iso_time.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            self.job_repo.add(job)
            await self.session.delete(req)
            await self.session.flush()

            return f"✔ Converted Request to Job: {job.description}", {
                "action": "promote",
                "entity": "job",
                "id": job.id,
                "old_request_content": req.content,
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
