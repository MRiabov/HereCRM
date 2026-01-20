from typing import Union, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Job, Customer, Request
from src.repositories import (
    JobRepository,
    CustomerRepository,
    RequestRepository,
    UserRepository,
    ServiceRepository,
)
from src.events import event_bus
from src.services.crm_service import CRMService
from src.services.invoice_service import InvoiceService
from src.services.template_service import TemplateService
from src.services.geocoding import GeocodingService
from src.services.inference_service import InferenceService
from src.services.search_service import SearchService
from src.services.chat_utils import format_line_items
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
    GetPipelineTool,
    UpdateCustomerStageTool,
    AddServiceTool,
    EditServiceTool,
    DeleteServiceTool,
    ListServicesTool,
    ExitSettingsTool,
)
from src.tools.invoice_tools import SendInvoiceTool

class ToolExecutor:
    def __init__(
        self,
        session: AsyncSession,
        business_id: int,
        user_id: int,
        user_phone: str,
        template_service: TemplateService,
    ):
        self.session = session
        self.business_id = business_id
        self.user_id = user_id
        self.user_phone = user_phone
        self.template_service = template_service


        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)
        self.user_repo = UserRepository(session)
        self.service_repo = ServiceRepository(session)
        self.geocoding_service = GeocodingService()
        self.search_service = SearchService(session, self.geocoding_service)
        self.invoice_service = InvoiceService(session)

    async def _get_user_defaults(self) -> Tuple[Optional[str], Optional[str]]:
        user = await self.user_repo.get_by_id(self.user_id)
        if user and user.preferences:
            return user.preferences.get("default_city"), user.preferences.get("default_country")
        return None, None

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
            HelpTool,
            GetPipelineTool,
            UpdateCustomerStageTool,
            AddServiceTool,
            EditServiceTool,
            DeleteServiceTool,
            ListServicesTool,
            ExitSettingsTool,
            SendInvoiceTool,
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
        elif isinstance(tool_call, GetPipelineTool):
            return await self._execute_get_pipeline(tool_call)
        elif isinstance(tool_call, UpdateCustomerStageTool):
            return await self._execute_update_customer_stage(tool_call)
        elif isinstance(tool_call, AddServiceTool):
            return await self._execute_add_service(tool_call)
        elif isinstance(tool_call, EditServiceTool):
            return await self._execute_edit_service(tool_call)
        elif isinstance(tool_call, DeleteServiceTool):
            return await self._execute_delete_service(tool_call)
        elif isinstance(tool_call, ListServicesTool):
            return "List services is handled by the service layer directly (for formatting).", None
        elif isinstance(tool_call, ExitSettingsTool):
            return "Exit settings is handled by the service layer directly.", None
        elif isinstance(tool_call, HelpTool):
            return "Help is handled by the service layer directly.", None
        elif isinstance(tool_call, SendInvoiceTool):
            return await self._execute_send_invoice(tool_call)
        return "Unknown tool call", None

    # ... (other methods unchanged)

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
        # Check for user defaults first
        default_city, default_country = await self._get_user_defaults()
        
        # Use provided city/country if available, otherwise defaults for geocoding
        # Note: AddLeadTool has specific city/country fields, but also 'location' string.
        # If 'location' string is provided, we geocode it.
        # If specific city/country provided in tool, they override defaults for geocoding context?
        # Actually geocode method takes defaults to append to address string if missing.
        
        target_city = tool.city or default_city
        target_country = tool.country or default_country

        lat, lon, street, city, country, postal_code = await self.geocoding_service.geocode(
            tool.location or "",
            default_city=default_city,
            default_country=default_country
        )
        
        # If geocoding didn't return city/country (e.g. not found or not parsed), use the ones we have
        final_city = city or target_city
        final_country = country or target_country

        # 3. Create customer
        customer = Customer(
            business_id=self.business_id,
            name=customer_name,
            phone=tool.phone,
            details=tool.details,
            original_address_input=tool.location,
            latitude=lat,
            longitude=lon,
            street=street or tool.street,
            city=final_city,
            country=final_country,
            postal_code=postal_code,
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
            default_city, default_country = await self._get_user_defaults()
            lat, lon, street, city, country, postal_code = await self.geocoding_service.geocode(
                tool.location,
                default_city=default_city,
                default_country=default_country
            )
            if lat and lon:
                customer.latitude = lat
                customer.longitude = lon
            # We also update structured fields if geocoding returns them
            if street:
                customer.street = street
            if city:
                customer.city = city
            if country:
                customer.country = country
            if postal_code:
                customer.postal_code = postal_code
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
            # Create new customer
            default_city, default_country = await self._get_user_defaults()
            
            # Try to geocode the location if provided
            lat, lon, street, city, country, postal_code = None, None, None, None, None, None
            if tool.location:
                lat, lon, street, city, country, postal_code = await self.geocoding_service.geocode(
                    tool.location, 
                    default_city=default_city, 
                    default_country=default_country
                )
            
            # Use defaults if geocoding didn't fill them
            final_city = city or default_city
            final_country = country or default_country
            
            customer = Customer(
                business_id=self.business_id,
                name=customer_name,
                phone=tool.customer_phone,
                original_address_input=tool.location,
                latitude=lat,
                longitude=lon,
                street=street,
                city=final_city,
                country=final_country,
                postal_code=postal_code,
            )
            self.customer_repo.add(customer)
            await self.session.flush()

        # 2. Pre-process line items and value
        job_value = tool.price
        inferred_items = []
        if tool.line_items:
            inference_service = InferenceService(self.session)
            inferred_items = await inference_service.infer_line_items(
                self.business_id, tool.line_items
            )
            # Ensure price consistency: if line items exist, they define the value.
            job_value = round(sum(li.total_price for li in inferred_items), 2)

        # 3. Handle scheduling if time provided
        scheduled_at = None
        if tool.iso_time:
            from datetime import datetime
            try:
                scheduled_at = datetime.fromisoformat(
                    tool.iso_time.replace("Z", "+00:00")
                )
            except ValueError:
                pass
        
        description = tool.description
        if tool.time:
            if description:
                description = f"{description} (Scheduled: {tool.time})"
            else:
                description = f"(Scheduled: {tool.time})"

        # 4. Create job using CRMService to ensure events are fired
        crm_service = CRMService(self.session, self.business_id)
        job = await crm_service.create_job(
            customer_id=customer.id,
            description=description,
            value=job_value,
            location=tool.location,
            status=tool.status or ("scheduled" if tool.time else "pending"),
            scheduled_at=scheduled_at,
            line_items=inferred_items,
            postal_code=postal_code if 'postal_code' in locals() else None,
        )
        price_info = f" – €{job.value}" if job.value else " – No price"
        line_items_summary = ""
        if tool.line_items and job.line_items:
            line_items_summary = f"\n{format_line_items(job.line_items)}"

        return (
            self.template_service.render(
                "job_added",
                category="Job",
                name=customer.name,
                location=job.location or "No location",
                price_info=price_info,
            )
            + line_items_summary,
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
            # Use CRMService to update and emit event
            crm_service = CRMService(self.session, self.business_id)
            scheduled_at = None
            if tool.iso_time:
                from datetime import datetime
                try:
                    scheduled_at = datetime.fromisoformat(
                        tool.iso_time.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            job = await crm_service.update_job(
                job_id=job.id,
                scheduled_at=scheduled_at,
                description=f"{job.description} (Scheduled: {tool.time})" if job.description and "(Scheduled:" not in job.description else job.description or f"(Scheduled: {tool.time})",
                status="scheduled"
            )

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
        
        # Check for implicit contact event
        if tool.customer_name or tool.customer_phone:
            customer = None
            if tool.customer_name:
                customer = await self.customer_repo.get_by_name(tool.customer_name, self.business_id)
            if not customer and tool.customer_phone:
                customer = await self.customer_repo.get_by_phone(tool.customer_phone, self.business_id)
            
            if customer:
                from src.events import event_bus
                await event_bus.emit(
                    "CONTACT_EVENT",
                    {"customer_id": customer.id, "business_id": self.business_id}
                )
        return self.template_service.render(
            "request_stored", content=tool.content[:50]
        ), {
            "action": "create",
            "entity": "request",
            "id": req.id,
            "content": tool.content,
        }

    async def _execute_search(
        self, tool: SearchTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        result_text = await self.search_service.search(tool, self.business_id)
        return result_text, None

    async def _execute_update_settings(
        self, tool: UpdateSettingsTool
    ) -> tuple[str, Optional[dict]]:
        old_value = await self.user_repo.update_preferences(
            self.user_id, tool.setting_key, tool.setting_value
        )
        if old_value is None and not await self.user_repo.get_by_id(self.user_id):
            return "User not found.", None

        return (
            self.template_service.render(
                "setting_updated", key=tool.setting_key, value=tool.setting_value
            ),
            {
                "action": "update_settings",
                "entity": "user",
                "user_id": self.user_id,
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

    async def _execute_get_pipeline(
        self, tool: GetPipelineTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        crm_service = CRMService(self.session, self.business_id)
        report = await crm_service.format_pipeline_summary()
        return report, {"action": "query", "entity": "pipeline"}

    async def _execute_update_customer_stage(
        self, tool: UpdateCustomerStageTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        customers = await self.customer_repo.search(tool.query, self.business_id)
        if not customers:
            return f"Could not find customer matching '{tool.query}'", None
        if len(customers) > 1:
            return (
                f"Multiple customers found matching '{tool.query}'. Please be more specific.",
                None,
            )

        customer = customers[0]
        old_stage = customer.pipeline_stage.value
        crm_service = CRMService(self.session, self.business_id)
        try:
            await crm_service.update_customer_stage(customer.id, tool.stage)
        except ValueError as e:
            return str(e), None

        return f"✔ Updated {customer.name}'s stage to {tool.stage.replace('_', ' ').title()}", {
            "action": "update",
            "entity": "customer",
            "id": customer.id,
            "old_stage": old_stage,
            "new_stage": tool.stage,
        }

    async def _execute_add_service(
        self, tool: AddServiceTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        from src.models import Service

        service_name = tool.name.strip().title()
        existing = await self.service_repo.get_by_name(service_name, self.business_id)

        if existing:
            # Update existing service
            old_price = existing.default_price
            existing.default_price = tool.price
            existing.name = service_name
            await self.session.flush()
            
            return f"✔ Updated existing service *'{service_name}'* – Price: {tool.price:.2f}", {
                "action": "update",
                "entity": "service",
                "id": existing.id,
                "name": service_name,
                "old_price": old_price,
                "new_price": tool.price,
            }

        new_service = Service(
            business_id=self.business_id,
            name=service_name,
            default_price=tool.price,
        )
        self.service_repo.add(new_service)
        await self.session.flush()

        return self.template_service.render(
            "service_added", name=service_name, price=f"{tool.price:.2f}"
        ), {
            "action": "create",
            "entity": "service",
            "id": new_service.id,
            "name": service_name,
            "price": tool.price,
        }

    async def _execute_edit_service(
        self, tool: EditServiceTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # Fuzzy find service
        services = await self.service_repo.get_all_for_business(self.business_id)
        
        # Simple fuzzy match: strict case-insensitive first, then substring
        target = None
        for s in services:
            if s.name.lower() == tool.original_name.lower():
                target = s
                break
        
        if not target:
            # Substring match
             for s in services:
                if tool.original_name.lower() in s.name.lower():
                    target = s
                    break
        
        if not target:
             return f"Could not find service matching '{tool.original_name}'", None

        old_data = {"name": target.name, "default_price": target.default_price}
        
        if tool.new_name:
            target.name = tool.new_name
        if tool.new_price is not None:
             target.default_price = tool.new_price
        
        await self.session.flush()

        return f"Updated service '{target.name}' – Price: {target.default_price:.2f}", {
            "action": "update",
            "entity": "service",
            "id": target.id,
            "old_data": old_data,
        }

    async def _execute_delete_service(
        self, tool: DeleteServiceTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        services = await self.service_repo.get_all_for_business(self.business_id)
        
        target = None
        for s in services:
            if s.name.lower() == tool.name.lower():
                target = s
                break
        
        if not target:
             for s in services:
                if tool.name.lower() in s.name.lower():
                    target = s
                    break

        if not target:
            return f"Could not find service matching '{tool.name}' to delete.", None

        await self.session.delete(target)
        await self.session.flush()

        return self.template_service.render("service_deleted", id=target.name), {
             "action": "delete",
             "entity": "service",
             "id": target.id,
             "name": target.name,
        }

    async def _execute_send_invoice(
        self, tool: SendInvoiceTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # 1. Find Customer
        customers = await self.customer_repo.search(tool.query, self.business_id)
        if not customers:
            return f"Could not find customer matching '{tool.query}'", None
        if len(customers) > 1:
            return (
                f"Multiple customers found matching '{tool.query}'. Please be more specific.",
                None,
            )
        customer = customers[0]

        # 2. Find most recent job for customer
        job = await self.job_repo.get_most_recent_by_customer(customer.id, self.business_id)
        
        if not job:
            return f"No jobs found for customer {customer.name}. Cannot generate invoice.", None

        # 3. Create or Get Invoice
        try:
            invoice = await self.invoice_service.create_invoice(
                job, force_regenerate=tool.force_regenerate
            )
        except Exception as e:
             return f"Failed to generate invoice: {str(e)}", None

        # 4. Return result
        return (
            f"Here is the invoice for {customer.name} (Job #{job.id}): {invoice.public_url}",
            {
                "action": "invoice_generated",
                "entity": "invoice",
                "id": invoice.id,
                "job_id": job.id,
                "url": invoice.public_url,
                "customer": customer.name
            },
        )

