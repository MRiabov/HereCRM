from typing import Union, Optional, Tuple, Dict, Any
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
from src.services.search_service import SearchService
from src.uimodels import (
    AddJobTool,
    AddLeadTool,
    EditCustomerTool,
    ScheduleJobTool,
    AddRequestTool,
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
        self.user_repo = UserRepository(session)
        self.geocoding_service = GeocodingService()
        self.search_service = SearchService(session, self.geocoding_service)

    async def execute(
        self,
        tool_call: Union[
            AddJobTool,
            AddLeadTool,
            EditCustomerTool,
            ScheduleJobTool,
            AddRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
        ],
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        if isinstance(tool_call, AddJobTool):
            return await self._execute_add_job(tool_call)
        elif isinstance(
            tool_call, AddLeadTool
        ):  # Changed from AddCustomerTool to AddLeadTool
            return await self._execute_add_lead(tool_call)  # Changed method call
        elif isinstance(tool_call, EditCustomerTool):
            return await self._execute_edit_customer(tool_call)
        elif isinstance(tool_call, ScheduleJobTool):
            return await self._execute_schedule_job(tool_call)
        elif isinstance(
            tool_call, AddRequestTool
        ):  # Changed from StoreRequestTool to AddRequestTool
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

    async def _execute_add_lead(  # Renamed from _execute_add_customer
        self,
        tool: AddLeadTool,  # Changed type hint from AddCustomerTool to AddLeadTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:  # Changed return type hint
        # 1. Check for duplicates
        customer_name = tool.name.title() if tool.name else "Unknown"
        existing = await self.customer_repo.get_by_name(customer_name, self.business_id)
        if not existing and tool.phone:
            existing = await self.customer_repo.get_by_phone(
                tool.phone, self.business_id
            )

        if existing:
            return f"Note: Customer '{customer_name}' already exists.", None

        # 2. Extract address
        lat, lon, street, city, country = await self.geocoding_service.geocode(
            tool.location
        )

        # 3. Create customer
        customer = Customer(
            business_id=self.business_id,
            name=customer_name,
            phone=tool.phone,
            details=tool.details,
            original_address_input=tool.location,
            latitude=lat,
            longitude=lon,
            street=street,
            city=city,
            country=country,
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
                "action": "create",
                "entity": "lead",  # Using 'lead' as generic term for customer w/o job in UI context
                "id": customer.id,
                "customer_name": customer.name,
                "description": customer.details,
                "location": tool.location,
            },
        )

    async def _execute_edit_customer(
        self, tool: EditCustomerTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:  # Changed return type hint
        # Find customer by query (Name, Phone, or Address)
        # We use repository search which handles name, phone, and original_address_input
        customers = await self.customer_repo.search(tool.query, self.business_id)
        if not customers:
            return f"Could not find customer matching '{tool.query}'", None
        if len(customers) > 1:
            return (
                f"Multiple customers found matching '{tool.query}'. Please be more specific.",
                None,
            )

        customer = customers[0]
        old_data = {
            "name": customer.name,
            "phone": customer.phone,
            "details": customer.details,
            "street": customer.street,
        }

        if tool.name:
            customer.name = tool.name.title()
        if tool.phone:
            customer.phone = tool.phone
        if tool.location:
            customer.original_address_input = tool.location
            # Re-geocode
            lat, lon, street, city, country = await self.geocoding_service.geocode(
                tool.location
            )
            if lat and lon:
                customer.latitude = lat
                customer.longitude = lon
            # We also update structured fields if geocoding returns them (currently mocking might return None, but implementation supports it)
            if street:
                customer.street = street
            if city:
                customer.city = city
            if country:
                customer.country = country
        if tool.details:
            customer.details = tool.details

        await self.session.flush()

        return f"✔ Updated customer: {customer.name}", {
            "action": "update",
            "entity": "customer",
            "id": customer.id,
            "old_data": old_data,
        }

    async def _execute_add_job(
        self, tool: AddJobTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:  # Changed return type hint
        # 1. Find or create customer (Deduplication)
        customer_name = tool.customer_name.title() if tool.customer_name else "Unknown"
        customer = await self.customer_repo.get_by_name(customer_name, self.business_id)
        if not customer and tool.customer_phone:
            customer = await self.customer_repo.get_by_phone(
                tool.customer_phone, self.business_id
            )

        if not customer:
            customer = Customer(
                business_id=self.business_id,
                name=customer_name,
                phone=tool.customer_phone,
                original_address_input=tool.location,
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
    ) -> Tuple[str, Optional[Dict[str, Any]]]:  # Changed return type hint
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

    async def _execute_store_request(  # Renamed from _execute_store_request
        self,
        tool: AddRequestTool,  # Changed type hint from StoreRequestTool to AddRequestTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:  # Changed return type hint
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
        result_text = await self.search_service.search(tool, self.business_id)
        return result_text, None

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
