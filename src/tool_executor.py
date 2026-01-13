from typing import Union, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Customer, Request
from src.repositories import (
    JobRepository,
    CustomerRepository,
    RequestRepository,
    UserRepository,
)
from src.services.crm_service import CRMService
from src.uimodels import (
    AddJobTool,
    ScheduleJobTool,
    StoreRequestTool,
    SearchTool,
    UpdateSettingsTool,
    ConvertRequestTool,
    HelpTool,
)


class ToolExecutor:
    def __init__(self, session: AsyncSession, business_id: int, user_phone: str):
        self.session = session
        self.business_id = business_id
        self.user_phone = user_phone
        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)
        self.user_repo = UserRepository(session)

    async def execute(
        self,
        tool_call: Union[
            AddJobTool,
            ScheduleJobTool,
            StoreRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
        ],
    ) -> tuple[str, Optional[dict]]:
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
        elif isinstance(tool_call, HelpTool):
            return "Help is handled by the service layer directly.", None
        return "Unknown tool call", None

    async def _execute_add_job(self, tool: AddJobTool) -> str:
        # 1. Find or create customer
        customer = await self.customer_repo.get_by_name(
            tool.customer_name, self.business_id
        )
        if not customer and tool.customer_phone:
            customer = await self.customer_repo.get_by_phone(
                tool.customer_phone, self.business_id
            )

        if not customer:
            customer = Customer(
                name=tool.customer_name,
                phone=tool.customer_phone,
                business_id=self.business_id,
            )
            self.customer_repo.add(customer)
            await self.session.flush()  # Get ID

        # 2. Create job
        job = Job(
            business_id=self.business_id,
            customer_id=customer.id,
            description=tool.description,
            value=tool.price,
            location=tool.location,
            status="pending",
        )
        self.job_repo.add(job)
        await self.session.flush()

        return (
            f"✔ Job added: {customer.name} – {job.location or 'No location'} – {f'€{job.value}' if job.value else 'No price'}",
            {"action": "create", "entity": "job", "id": job.id},
        )

    async def _execute_schedule_job(
        self, tool: ScheduleJobTool
    ) -> tuple[str, Optional[dict]]:
        # This is a bit complex as it might be a new job or existing
        # For now, let's assume it updates the most recent job or finds by query
        job = None
        if tool.job_id:
            job = await self.job_repo.get_by_id(tool.job_id, self.business_id)

        if not job and tool.customer_query:
            # Fuzzy find job by customer name/phone
            customers = await self.customer_repo.search(
                tool.customer_query, self.business_id
            )
            if customers:
                # Use efficient scoped query in repository
                job = await self.job_repo.get_most_recent_by_customer(
                    customers[0].id, self.business_id
                )

        if job:
            # For now, we store natural language in description if parsing fails
            # In a real app we'd use a dedicated library like dateparser
            job.status = "scheduled"
            # We still keep it in description for the user to see exactly what was parsed
            if "(Scheduled:" not in job.description:
                job.description = f"{job.description} (Scheduled: {tool.time})"

            return f"✔ Scheduled {job.customer.name} for {tool.time}", {
                "action": "update",
                "entity": "job",
                "id": job.id,
                "old_status": "pending",
            }

        return "Could not find a job to schedule. Try adding a job first.", None

    async def _execute_store_request(
        self, tool: StoreRequestTool
    ) -> tuple[str, Optional[dict]]:
        req = Request(
            business_id=self.business_id, content=tool.content, status="pending"
        )
        self.request_repo.add(req)
        await self.session.flush()
        return f"✔ Request stored: {tool.content[:50]}...", {
            "action": "create",
            "entity": "request",
            "id": req.id,
        }

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

    async def _execute_update_settings(
        self, tool: UpdateSettingsTool
    ) -> tuple[str, Optional[dict]]:
        old_value = await self.user_repo.update_preferences(
            self.user_phone, tool.setting_key, tool.setting_value
        )
        if old_value is None and not await self.user_repo.get_by_phone(self.user_phone):
            return "User not found.", None

        return (
            f"✔ Updated setting '{tool.setting_key}' to '{tool.setting_value}'",
            {
                "action": "update_settings",
                "entity": "user",
                "phone": self.user_phone,
                "setting_key": tool.setting_key,
                "old_value": old_value,
            },
        )

    async def _execute_convert_request(
        self, tool: ConvertRequestTool
    ) -> tuple[str, Optional[dict]]:
        service = CRMService(self.session, self.business_id)
        return await service.convert_request(tool.query, tool.action, tool.time)
