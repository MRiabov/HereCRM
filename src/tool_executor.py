from typing import Union, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Customer, Request
from src.repositories import JobRepository, CustomerRepository, RequestRepository, UserRepository
from src.uimodels import (
    AddJobTool,
    ScheduleJobTool,
    StoreRequestTool,
    SearchTool,
    UpdateSettingsTool,
    ConvertRequestTool
)

class ToolExecutor:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)
        self.user_repo = UserRepository(session)

    async def execute(self, tool_call: Union[AddJobTool, ScheduleJobTool, StoreRequestTool, SearchTool, UpdateSettingsTool, ConvertRequestTool]) -> tuple[str, Optional[dict]]:
        if isinstance(tool_call, AddJobTool):
            return await self._execute_add_job(tool_call)
        elif isinstance(tool_call, ScheduleJobTool):
            return await self._execute_schedule_job(tool_call)
        elif isinstance(tool_call, StoreRequestTool):
            return await self._execute_store_request(tool_call)
        elif isinstance(tool_call, SearchTool):
            return await self._execute_search(tool_call)
        elif isinstance(tool_call, UpdateSettingsTool):
            return await self._execute_update_settings(tool_call)
        elif isinstance(tool_call, ConvertRequestTool):
            return await self._execute_convert_request(tool_call)
        return "Unknown tool call", None

    async def _execute_add_job(self, tool: AddJobTool) -> str:
        # 1. Find or create customer
        customer = await self.customer_repo.get_by_name(tool.customer_name, self.business_id)
        if not customer and tool.customer_phone:
            customer = await self.customer_repo.get_by_phone(tool.customer_phone, self.business_id)
        
        if not customer:
            customer = Customer(
                name=tool.customer_name,
                phone=tool.customer_phone,
                business_id=self.business_id
            )
            self.customer_repo.add(customer)
            await self.session.flush() # Get ID

        # 2. Create job
        job = Job(
            business_id=self.business_id,
            customer_id=customer.id,
            description=tool.description,
            value=tool.price,
            location=tool.location,
            status="pending"
        )
        self.job_repo.add(job)
        await self.session.flush()
        
        return f"✔ Job added: {customer.name} – {job.location or 'No location'} – {f'€{job.value}' if job.value else 'No price'}", {"action": "create", "entity": "job", "id": job.id}

    async def _execute_schedule_job(self, tool: ScheduleJobTool) -> tuple[str, Optional[dict]]:
        # This is a bit complex as it might be a new job or existing
        # For now, let's assume it updates the most recent job or finds by query
        job = None
        if tool.job_id:
            job = await self.job_repo.get_by_id(tool.job_id, self.business_id)
        
        if not job and tool.customer_query:
            # Fuzzy find job by customer name/phone
            customers = await self.customer_repo.search(tool.customer_query, self.business_id)
            if customers:
                # Get the most recent job for the first matching customer
                jobs = await self.job_repo.get_all(self.business_id)
                # Simple filter for demo purposes, in real app would be better query
                customer_ids = [c.id for c in customers]
                matching_jobs = [j for j in jobs if j.customer_id in customer_ids]
                if matching_jobs:
                    job = matching_jobs[-1] # Most recent

        if job:
            job.description = f"{job.description} (Scheduled: {tool.time})"
            job.status = "scheduled"
            return f"✔ Scheduled {job.customer.name} for {tool.time}", {"action": "update", "entity": "job", "id": job.id, "old_status": "pending"}
        
        return "Could not find a job to schedule. Try adding a job first.", None

    async def _execute_store_request(self, tool: StoreRequestTool) -> tuple[str, Optional[dict]]:
        req = Request(
            business_id=self.business_id,
            content=tool.content,
            status="pending"
        )
        self.request_repo.add(req)
        await self.session.flush()
        return f"✔ Request stored: {tool.content[:50]}...", {"action": "create", "entity": "request", "id": req.id}

    async def _execute_search(self, tool: SearchTool) -> tuple[str, Optional[dict]]:
        customers = await self.customer_repo.search(tool.query, self.business_id)
        jobs = await self.job_repo.search(tool.query, self.business_id)
        requests = await self.request_repo.search(tool.query, self.business_id)
        
        lines = []
        if customers:
            lines.append("Customers:")
            for c in customers:
                lines.append(f"- {c.name} ({c.phone or 'No phone'})")
        if jobs:
            lines.append("Jobs:")
            for j in jobs:
                lines.append(f"- {j.description} (Status: {j.status})")
        if requests:
            lines.append("Requests:")
            for r in requests:
                lines.append(f"- {r.content} (Status: {r.status})")
            
        if not lines:
            return f"No results found for '{tool.query}'", None
            
        return "\n".join(lines), None

    async def _execute_update_settings(self, tool: UpdateSettingsTool) -> tuple[str, Optional[dict]]:
        # This usually applies to the user who sent the command
        # Since we don't have the user object here easily, we might need to pass it or find by phone
        # For now, let's assume we update all users in the business or it's handled differently
        # Actually, WP prompt says Maps UpdateSettingsTool -> UserRepository.update_preferences()
        # We need a phone number to identify the specific user.
        return "Settings update not implemented in ToolExecutor yet (needs user context).", None

    async def _execute_convert_request(self, tool: ConvertRequestTool) -> tuple[str, Optional[dict]]:
        # Find the request
        requests = await self.request_repo.search(tool.query, self.business_id)
        if not requests:
            return f"Could not find request matching '{tool.query}'", None
        
        req = requests[0]
        
        if tool.action == "schedule":
            # Promotion logic: Request -> Job
            # For now, we don't have customer data in Request, so we might need fuzzy search or ask
            # Simplified: Create a Job with current request content
            # Assuming we can find a customer associated with the request (future)
            # For now, just create a job and delete request
            job = Job(
                business_id=self.business_id,
                customer_id=1, # Default or fuzzy find
                description=f"Converted from request: {req.content}. Time: {tool.time or 'N/A'}",
                status="scheduled" if tool.time else "pending"
            )
            self.job_repo.add(job)
            await self.session.delete(req)
            return f"✔ Converted Request to Job: {job.description}", {"action": "promote", "entity": "job", "id": job.id, "old_request_content": req.content}
        
        elif tool.action == "complete":
            req.status = "completed"
            return f"✔ Request marked as completed: {req.content[:30]}", {"action": "update", "entity": "request", "id": req.id, "old_status": "pending"}
            
        return f"Unknown action: {tool.action}", None
