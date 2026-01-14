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
from src.services.template_service import TemplateService
from src.services.geocoding import GeocodingService
from src.uimodels import (
    AddJobTool,
    AddCustomerTool,
    ScheduleJobTool,
    StoreRequestTool,
    SearchTool,
    UpdateSettingsTool,
    ConvertRequestTool,
    HelpTool,
)


class ToolExecutor:
    def __init__(
        self,
        session: AsyncSession,
        business_id: int,
        user_phone: str,
        template_service: TemplateService,
    ):
        self.session = session
        self.business_id = business_id
        self.user_phone = user_phone
        self.template_service = template_service
        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)
        self.request_repo = RequestRepository(session)
        self.user_repo = UserRepository(session)
        self.geocoding_service = GeocodingService()

    async def execute(
        self,
        tool_call: Union[
            AddJobTool,
            AddCustomerTool,
            ScheduleJobTool,
            StoreRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
        ],
    ) -> tuple[str, Optional[dict]]:
        if isinstance(tool_call, AddJobTool):
            return await self._execute_add_job(tool_call)
        elif isinstance(tool_call, AddCustomerTool):
            return await self._execute_add_customer(tool_call)
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

    async def _execute_add_customer(
        self, tool: AddCustomerTool
    ) -> tuple[str, Optional[dict]]:
        # 1. Deduplication: Check if customer already exists
        customer = await self.customer_repo.get_by_name(tool.name, self.business_id)
        if not customer and tool.phone:
            customer = await self.customer_repo.get_by_phone(
                tool.phone, self.business_id
            )

        action = "create"
        if customer:
            action = "update"
            # Update missing details if applicable, but usually we just want to confirm existing
            if tool.details:
                if customer.details:
                    customer.details = f"{customer.details}\n{tool.details}"
                else:
                    customer.details = tool.details
        else:
            customer = Customer(
                name=tool.name,
                phone=tool.phone,
                details=tool.details,
                street=tool.street,
                city=tool.city,
                country=tool.country,
                original_address_input=tool.location,  # Map tool.location to raw input
                business_id=self.business_id,
            )
            self.customer_repo.add(customer)

        await self.session.flush()

        # Render Lead/Customer summary
        client_details = self.template_service.render(
            "client_details",
            name=customer.name,
            phone=customer.phone or "Not supplied",
            address=tool.location or "Not supplied",
        )

        return (
            self.template_service.render(
                "lead_summary",
                client_details=client_details,
                description=customer.details or "Not supplied",
            ),
            {
                "action": action,
                "entity": "lead",  # Using 'lead' as generic term for customer w/o job in UI context
                "id": customer.id,
                "customer_name": customer.name,
                "description": customer.details,
                "location": tool.location,
            },
        )

    async def _execute_add_job(self, tool: AddJobTool) -> tuple[str, Optional[dict]]:
        # 1. Find or create customer (Deduplication)
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
                # Store location in details if it's a new customer?
                # Or maybe we need location on Customer model?
                # The model has 'details' and 'phone'. 'Location' is on Job usually.
                # But 'client_details' template uses address.
                # Let's assume tool.location is for the Job, but if it helps identify customer...
            )
            self.customer_repo.add(customer)
            await self.session.flush()

        # 2. Create job
        job = Job(
            business_id=self.business_id,
            customer_id=customer.id,
            description=tool.description,
            value=tool.price,
            location=tool.location,
            status=tool.status or "pending",
        )
        self.job_repo.add(job)
        await self.session.flush()

        price_info = f" – €{job.value}" if job.value else " – No price"

        return (
            self.template_service.render(
                "job_added",
                category="Job",
                name=customer.name,
                location=job.location or "No location",
                price_info=price_info,
            ),
            {
                "action": "create",
                "entity": "job",
                "id": job.id,
                "category": "job",
                "customer_name": customer.name,
                "price": job.value,
                "location": job.location,
                "description": job.description,
            },
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
            if len(customers) == 1:
                # Use efficient scoped query in repository
                job = await self.job_repo.get_most_recent_by_customer(
                    customers[0].id, self.business_id
                )
            elif len(customers) > 1:
                return (
                    f"Multiple customers found matching '{tool.customer_query}'. Please be more specific (e.g., use full name or phone).",
                    None,
                )

        if job:
            # Update scheduled_at if iso_time is provided
            if tool.iso_time:
                from datetime import datetime

                try:
                    job.scheduled_at = datetime.fromisoformat(
                        tool.iso_time.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass  # Fallback to NL description if parsing fails

            # For now, we store natural language in description if parsing fails
            # In a real app we'd use a dedicated library like dateparser
            job.status = "scheduled"
            # We still keep it in description for the user to see exactly what was parsed
            if job.description and "(Scheduled:" not in job.description:
                job.description = f"{job.description} (Scheduled: {tool.time})"
            elif not job.description:
                job.description = f"(Scheduled: {tool.time})"

            return self.template_service.render(
                "job_scheduled", name=job.customer.name, time=tool.time
            ), {
                "action": "update",
                "entity": "job",
                "id": job.id,
                "old_status": "pending",
                "customer_name": job.customer.name,
                "description": job.description,
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
        return self.template_service.render(
            "request_stored", content=tool.content[:50]
        ), {
            "action": "create",
            "entity": "request",
            "id": req.id,
            "content": tool.content,
        }

    async def _execute_search(self, tool: SearchTool) -> tuple[str, Optional[dict]]:
        lines = []

        # Parse dates if present
        min_date = None
        max_date = None
        if tool.min_date:
            try:
                from datetime import datetime

                min_date = datetime.fromisoformat(tool.min_date.replace("Z", "+00:00"))
            except ValueError:
                pass
        if tool.max_date:
            try:
                from datetime import datetime

                max_date = datetime.fromisoformat(tool.max_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Resolve Geolocation if address provided but coords missing
        if tool.center_address and not (tool.center_lat and tool.center_lon):
            lat, lon = await self.geocoding_service.get_coordinates(tool.center_address)
            if lat and lon:
                tool.center_lat = lat
                tool.center_lon = lon

        # Dispatch based on entity_type
        if tool.entity_type == "job":
            jobs = await self.job_repo.search(
                tool.query,
                self.business_id,
                query_type=tool.query_type,
                min_date=min_date,
                max_date=max_date,
                status=tool.status,
                radius=tool.radius,
                center_lat=tool.center_lat,
                center_lon=tool.center_lon,
                center_address=tool.center_address,
            )
            if jobs:
                lines.append("Jobs:")
                for j in jobs:
                    lines.append(
                        f"- {j.description} (Status: {j.status}) - {j.scheduled_at or 'No schedule'}"
                    )

        elif tool.entity_type in ["customer", "lead"]:
            customers = await self.customer_repo.search(
                tool.query,
                self.business_id,
                entity_type=tool.entity_type,
                query_type=tool.query_type,
                min_date=min_date,
                max_date=max_date,
                radius=tool.radius,
                center_lat=tool.center_lat,
                center_lon=tool.center_lon,
                center_address=tool.center_address,
            )
            if customers:
                header = "Leads:" if tool.entity_type == "lead" else "Customers:"
                lines.append(header)
                for c in customers:
                    details_str = f" - {c.details}" if c.details else ""
                    lines.append(f"- {c.name} ({c.phone or 'No phone'}){details_str}")

        elif tool.entity_type == "request":
            requests = await self.request_repo.search(
                tool.query,
                self.business_id,
                min_date=min_date,
                max_date=max_date,
                status=tool.status,
            )
            if requests:
                lines.append("Requests:")
                for r in requests:
                    lines.append(f"- {r.content} (Status: {r.status})")

        else:
            # General Search (fallback to original behavior but with date filters if applicable?)
            # Usually "general" search is text based. If dates are provided, we should probably prefer structured.
            # But the user might say "search all for 'foo' today".
            # Let's run all searches with the date filters (best effort)

            # NOTE: For mix of "all", we default to "scheduled" for jobs and "added" for others?
            # Or just pass dates to all.
            pass_query_type = tool.query_type

            customers = await self.customer_repo.search(
                tool.query,
                self.business_id,
                query_type=pass_query_type
                if pass_query_type == "added"
                else None,  # Only filter customers by date if explicitly "added" query?
                # actually if user says "who did we schedule today", intent is Job.
                # If user says "who did we add today", intent is Customer/Job created.
                # Let's pass date filters to all repos.
                min_date=min_date,
                max_date=max_date,
                radius=tool.radius,
                center_lat=tool.center_lat,
                center_lon=tool.center_lon,
                center_address=tool.center_address,
            )
            jobs = await self.job_repo.search(
                tool.query,
                self.business_id,
                query_type=pass_query_type,
                min_date=min_date,
                max_date=max_date,
                status=tool.status,
                radius=tool.radius,
                center_lat=tool.center_lat,
                center_lon=tool.center_lon,
                center_address=tool.center_address,
            )
            requests = await self.request_repo.search(
                tool.query,
                self.business_id,
                min_date=min_date,
                max_date=max_date,
                status=tool.status,
            )

            if customers:
                lines.append("Customers:")
                for c in customers:
                    details_str = f" - {c.details}" if c.details else ""
                    lines.append(f"- {c.name} ({c.phone or 'No phone'}){details_str}")
            if jobs:
                lines.append("Jobs:")
                for j in jobs:
                    lines.append(f"- {j.description} (Status: {j.status})")
            if requests:
                lines.append("Requests:")
                for r in requests:
                    lines.append(f"- {r.content} (Status: {r.status})")

        if not lines:
            return self.template_service.render(
                "search_no_results", query=tool.query
            ), None

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
            self.template_service.render(
                "setting_updated", key=tool.setting_key, value=tool.setting_value
            ),
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
        return await service.convert_request(
            tool.query, tool.action, tool.time, tool.iso_time
        )
