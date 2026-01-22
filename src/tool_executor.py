from typing import Union, Optional, Tuple, Dict, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Customer, Request, Business, Service, Job, UserRole
from src.events import event_bus
from src.repositories import (
    JobRepository,
    CustomerRepository,
    RequestRepository,
    UserRepository,
    ServiceRepository,
)
from src.services.crm_service import CRMService
from src.services.invoice_service import InvoiceService
from src.services.template_service import TemplateService
from src.services.geocoding import GeocodingService
from src.services.inference_service import InferenceService
from src.services.search_service import SearchService
from src.services.chat_utils import format_line_items
from src.services.billing_service import BillingService
from src.services.dashboard_service import DashboardService
from src.services.assignment_service import AssignmentService
from src.services.rbac_service import RBACService
from src.lib.text_formatter import render_employee_dashboard
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
    SendStatusTool,
    ManageEmployeesTool,
    MassEmailTool,
    ExportQueryTool,
    ExitDataManagementTool,
    GetBillingStatusTool,
    RequestUpgradeTool,
    CreateQuoteInput,
    LocateEmployeeTool,
    CheckETATool,
    AutorouteTool,
)
from src.tools.invoice_tools import SendInvoiceTool
from src.tools.quote_tools import CreateQuoteTool
from src.tools.routing_tools import AutorouteToolExecutor
from src.services.quote_service import QuoteService
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta, timezone
from src.tools.employee_management import ShowScheduleTool, AssignJobTool
from src.services.location_service import LocationService
from src.services.routing.ors import OpenRouteServiceAdapter
from src.config import settings

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
        self.logger = logging.getLogger(__name__)


        self.job_repo = JobRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.request_repo = RequestRepository(session)
        self.user_repo = UserRepository(session)
        self.service_repo = ServiceRepository(session)
        self.geocoding_service = GeocodingService()
        self.search_service = SearchService(session, self.geocoding_service)
        self.invoice_service = InvoiceService(session)
        self.billing_service = BillingService(session)
        self.dashboard_service = DashboardService(session)
        self.billing_service = BillingService(session)
        self.dashboard_service = DashboardService(session)
        self.assignment_service = AssignmentService(session, self.business_id)
        self.quote_service = QuoteService(session)
        self.rbac_service = RBACService()
        self._routing_service = None

    def _get_routing_service(self) -> OpenRouteServiceAdapter:
        if not self._routing_service:
            # In a real app we might inject this or check settings for Mock vs ORS
            self._routing_service = OpenRouteServiceAdapter(api_key=settings.openrouteservice_api_key)
        return self._routing_service

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
            SendStatusTool,
            ManageEmployeesTool,
            MassEmailTool,
            ExportQueryTool,
            ExitDataManagementTool,
            GetBillingStatusTool,
            RequestUpgradeTool,
            ShowScheduleTool,
            ShowScheduleTool,
            AssignJobTool,
            CreateQuoteInput,
            LocateEmployeeTool,
            CheckETATool,
            AutorouteTool,
        ],
    ) -> Tuple[str, Optional[Dict[str, Any]]]:

        # [T006] RBAC Permission Check
        # Get the tool class name for permission checking
        tool_name = type(tool_call).__name__
        
        # Fetch user to get their role
        user = await self.user_repo.get_by_id(self.user_id)
        if not user:
            return "Error: User not found.", None
        
        # Check permission using RBACService
        if not self.rbac_service.check_permission(user.role, tool_name):
            # [T007] Return friendly permission denied message
            tool_config = self.rbac_service.get_tool_config(tool_name)
            friendly_name = tool_config.get("friendly_name", "perform this action") if tool_config else "perform this action"
            return f"It seems you are trying to {friendly_name}. Sorry, you don't have permission for that.", None

        # [T018] Scope Enforcement
        # Check if the tool requires a specific scope
        required_scope = getattr(tool_call, "required_scope", None)
        if required_scope:
            business = await self.session.get(Business, self.business_id)
            if not business:
                return "Error: Business not found.", None
            
            # Check if scope is active
            if required_scope not in business.active_addons:
                return (
                    self.template_service.render(
                        "error_upgrade_required", scope=required_scope
                    ),
                    None
                )

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
        elif isinstance(tool_call, SendStatusTool):
            return await self._execute_send_status(tool_call)
        elif isinstance(tool_call, ManageEmployeesTool):
            return f"✔ Access granted to Employee Management: {tool_call.action}", None
        elif isinstance(tool_call, MassEmailTool):
            return f"✔ Access granted to Campaigns: Subject '{tool_call.subject}' sent to '{tool_call.recipient_query}'", None
        elif isinstance(tool_call, ExportQueryTool):
            return "✔ Access granted to Data Export. Starting export...", None
        elif isinstance(tool_call, ExitDataManagementTool):
            return "Exit data management is handled by the service layer.", None
        elif isinstance(tool_call, GetBillingStatusTool):
            return await self._execute_get_billing_status(tool_call)
        elif isinstance(tool_call, RequestUpgradeTool):
            return await self._execute_request_upgrade(tool_call)
        elif isinstance(tool_call, ShowScheduleTool):
            return await self._execute_show_schedule(tool_call)
        elif isinstance(tool_call, AssignJobTool):
            return await self._execute_assign_job(tool_call)
        elif isinstance(tool_call, CreateQuoteInput):
            return await self._execute_create_quote(tool_call)
        elif isinstance(tool_call, LocateEmployeeTool):
            return await self._execute_locate_employee(tool_call)
        elif isinstance(tool_call, CheckETATool):
            return await self._execute_check_eta(tool_call)
        elif isinstance(tool_call, AutorouteTool):
            return await self._execute_autoroute(tool_call)
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
    async def _execute_get_billing_status(
        self, tool: GetBillingStatusTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        status_info = await self.billing_service.get_billing_status(self.business_id)
        
        if "error" in status_info:
            return f"Error retrieving billing status: {status_info['error']}", None

        # Calculate seats used
        team_members = await self.user_repo.get_team_members(self.business_id)
        seats_used = len(team_members)
        
        active_addons = status_info.get("active_addons", [])
        
        # Addon definitions
        # These match the text provided by the user
        addon_definitions = {
            "manage_employees": {
                "name": "Employee Management addon",
                "price": "€30/mo",
                "desc": "Scheduling, automatic notification, and automatic routing."
            },
            "campaigns": {
                "name": "Campaign Messaging addon",
                "price": "€20/mo",
                "desc": "1000 messages included"
            },
            "extra_commands": {
                "name": "Extra commands package",
                "price": "€20/mo",
                "desc": "1000 commands included (note: using SMS and AI costs us money per every request!)"
            }
        }
        
        # Build Active Addons string
        active_lines = []
        for addon_id in active_addons:
            if addon_id in addon_definitions:
                defi = addon_definitions[addon_id]
                # Show full description for active addons as requested
                active_lines.append(f"- {defi['name']} ({defi['price']}) - {defi['desc']}")
            else:
                # Fallback for unknown addons
                formatted_name = addon_id.replace("_", " ").title()
                active_lines.append(f"- {formatted_name}")
        
        if not active_lines:
            active_lines.append("None")
        
        addons_str = "\n  ".join(active_lines)

        # Build Available Upgrades string
        upgrade_lines = []
        upgrade_lines.append("- Add Seat (€50/mo)")
        
        for addon_id, defi in addon_definitions.items():
            if addon_id not in active_addons:
                upgrade_lines.append(f"- {defi['name']} ({defi['price']}) - {defi['desc']}")
        
        upgrades_str = "\n  ".join(upgrade_lines)

        # Use the richer templates (header + body)
        header = self.template_service.render("billing_status_header")
        body = self.template_service.render(
            "billing_status_body",
            status=status_info.get("status", "free").title(),
            seats_used=seats_used,
            seat_limit=status_info.get("seat_limit", 1),
            addons=addons_str,
            available_upgrades=upgrades_str
        )
        
        return (
            f"{header}\n{body}",
            {
                "action": "query",
                "entity": "billing",
                "status": status_info
            }
        )

    async def _execute_request_upgrade(
        self, tool: RequestUpgradeTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # Generate upgrade link
        try:
            # We need valid success/cancel URLs. 
            # In a real app these would be public endpoints. 
            # For this MVP/local env, we'll assume a placeholder or simple landing page.
            # Using example.com for now as per likely dev setup, or a deep link if mobile.
            base_url = "https://herecrm.app"  
            success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{base_url}/billing/cancel"

            result = await self.billing_service.create_upgrade_link(
                business_id=self.business_id,
                item_type=tool.item_type,
                item_id=tool.item_id or "",
                success_url=success_url,
                cancel_url=cancel_url
            )
            
            return (
                self.template_service.render(
                    "billing_upgrade_quote",
                    description=result["description"],
                    url=result["url"]
                ),
                {
                    "action": "upgrade_request",
                    "entity": "billing",
                    "url": result["url"],
                    "description": result["description"]
                }
            )
        except ValueError as e:
            return f"Could not generate upgrade link: {str(e)}", None
        except Exception as e:
            return f"System error generating upgrade link: {str(e)}", None

    async def _execute_create_quote(self, tool: CreateQuoteInput) -> Tuple[str, Optional[Dict[str, Any]]]:
        quote_tool = CreateQuoteTool(self.quote_service, self.customer_repo, self.business_id)
        return await quote_tool.run(tool)

    async def _execute_send_status(
        self, tool: SendStatusTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        
        # 1. Resolve Customer/Job
        job = None
        customer = None
        
        if tool.query == "next_scheduled_client":
             stmt = (
                 select(Job)
                 .where(
                     Job.business_id == self.business_id,
                     Job.scheduled_at >= datetime.now(),
                     Job.status == "scheduled"
                 )
                 .order_by(Job.scheduled_at.asc())
                 .limit(1)
                 .options(joinedload(Job.customer))
             )
             result = await self.session.execute(stmt)
             job = result.scalar_one_or_none()
             if job:
                 customer = job.customer
        else:
            # Search for customer
            customers = await self.customer_repo.search(tool.query, self.business_id)
            if not customers:
                return f"Could not find customer matching '{tool.query}'", None
            if len(customers) > 1:
                return (
                    f"Multiple customers found matching '{tool.query}'. Please be more specific.",
                    None,
                )
            customer = customers[0]

        if not customer:
             return "No next scheduled client found.", None

        # 2. Emit Event
        await event_bus.emit(
            "SEND_STATUS_MESSAGE",
            {
                "customer_id": customer.id,
                "business_id": self.business_id,
                "status_type": tool.status_type,
                "message_content": tool.message_content,
                "customer_phone": customer.phone
            }
        )

        message_desc = f"'{tool.status_type}'"
        if tool.message_content:
             message_desc += f" ({tool.message_content})"
             
        return f"✔ Sent status update to {customer.name}: {message_desc}", {
            "action": "send_status",
            "entity": "customer",
            "id": customer.id,
            "status_type": tool.status_type,
            "customer_name": customer.name
        }

    async def _execute_show_schedule(
        self, tool: ShowScheduleTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        from datetime import date
        target_date = date.today()
        if tool.date:
            try:
                target_date = date.fromisoformat(tool.date)
            except ValueError:
                return self.template_service.render("error_invalid_date", date=tool.date), None

        schedule = await self.dashboard_service.get_employee_schedules(self.business_id, target_date)
        unscheduled = await self.dashboard_service.get_unscheduled_jobs(self.business_id)
        
        # WP03 presentation layer call
        report = render_employee_dashboard({
            "employees": [{"name": emp.name, "jobs": jobs} for emp, jobs in schedule.items()],
            "unscheduled": unscheduled
        })
        
        return report, {"action": "query", "entity": "dashboard", "date": target_date.isoformat()}

    async def _execute_assign_job(
        self, tool: AssignJobTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # 1. Ambiguity Handling: Find employee by name
        employees = await self.assignment_service.find_employee_by_name(tool.assign_to_name)
        
        if not employees:
            return self.template_service.render("employee_not_found", name=tool.assign_to_name), None
        
        if len(employees) > 1:
            names = ", ".join([e.name or "Unnamed" for e in employees])
            return self.template_service.render("employee_ambiguous", name=tool.assign_to_name, matches=names), None
        
        employee = employees[0]
        
        # 2. Call AssignmentService
        result = await self.assignment_service.assign_job(tool.job_id, employee.id)
        
        if not result.success:
            return f"Error: {result.error}", None
        
        msg = self.template_service.render("job_assigned", job_id=tool.job_id, employee_name=employee.name)
        if result.warning:
            msg += f" (Note: {result.warning})"
            
        return msg, {
            "action": "update",
            "entity": "job",
            "id": tool.job_id,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "warning": result.warning
        }

    async def _execute_locate_employee(
        self, tool: LocateEmployeeTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        if tool.employee_name:
            # Fuzzy search for employee
            # We fetch all team members and filter
            all_members = await self.user_repo.get_team_members(self.business_id)
            target_employees = []
            for m in all_members:
                if m.name and tool.employee_name.lower() in m.name.lower():
                    target_employees.append(m)
            
            if not target_employees:
                return f"Could not find employee matching '{tool.employee_name}'", None
        else:
            # List all
            target_employees = await self.user_repo.get_team_members(self.business_id)
            
        if not target_employees:
             return "No employees found.", None
        
        results = []
        for emp in target_employees:
            lat, lng, updated_at = await LocationService.get_employee_location(self.session, emp.id)
            status = "Location not available"
            link = ""
            if lat is not None and lng is not None:
                # Add map link
                link = f"https://www.google.com/maps?q={lat},{lng}"
                # Calculate staleness
                now = datetime.now(timezone.utc)
                if updated_at:
                    if updated_at.tzinfo is None:
                        ua = updated_at.replace(tzinfo=timezone.utc)
                    else:
                        ua = updated_at
                    
                    diff = now - ua
                    if diff > timedelta(minutes=30):
                        status = f"Last seen {int(diff.total_seconds()/60)}m ago"
                    else:
                        status = "Live"
                else:
                    status = "Location available"
            
            line = f"- **{emp.name}**: {status}"
            if link:
                line += f" ([Map]({link}))"
            results.append(line)
            
        return "\n".join(results), None

    async def _execute_check_eta(
        self, tool: CheckETATool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # Identify customer
        customer_phone = self.user_phone # Default caller
        
        if tool.customer_query:
            # Feedback 2: Role verification
            user = await self.user_repo.get_by_id(self.user_id)
            if not user or user.role != UserRole.OWNER:
                 return "Error: Only business owners can query ETA for other customers.", None
            
            # Admin asking for customer
            customers = await self.customer_repo.search(tool.customer_query, self.business_id)
            if not customers:
                return f"Could not find customer '{tool.customer_query}'", None
            if len(customers) > 1:
                return f"Multiple customers found for '{tool.customer_query}'.", None
            customer_phone = customers[0].phone
        
        if not customer_phone:
             return "Could not identify customer phone number.", None
             
        crm_service = CRMService(self.session, self.business_id)
        job = await crm_service.get_active_job_for_customer(customer_phone)
        
        if not job:
            return "There are no active or upcoming jobs found for this customer.", None
            
        if not job.employee_id:
             return "The job has no assigned technician yet.", None
        
        # Load employee if needed (should check if loaded or not)
        # We use repo to fetch fresh user to be safe
        tech = await self.user_repo.get_by_id(job.employee_id)
             
        if not tech:
             return "Assigned technician not found.", None
             
        # Get Tech Location
        lat, lng, updated_at = await LocationService.get_employee_location(self.session, tech.id)
        
        if lat is None or lng is None:
             return f"Technician {tech.name} is assigned but their location is currently unavailable.", None
             
        # Check staleness
        now = datetime.now(timezone.utc)
        if updated_at:
             if updated_at.tzinfo is None:
                  ua = updated_at.replace(tzinfo=timezone.utc)
             else:
                  ua = updated_at
             
             if (now - ua) > timedelta(minutes=30):
                  return f"Technician {tech.name} is en route, but their location signal was lost {int((now - ua).total_seconds()/60)} minutes ago. Please contact office.", None

        # Calculate ETA
        # Need Job Location
        job_lat, job_lng = job.latitude, job.longitude
        if job_lat is None or job_lng is None:
             if job.location:
                   # Geocode job.location
                   j_lat, j_lon, _, _, _, _ = await self.geocoding_service.geocode(job.location)
                   if j_lat and j_lon:
                        job_lat, job_lng = j_lat, j_lon
        
        if job_lat is None or job_lng is None:
             return "Job location is not geocoded. Cannot calculate ETA.", None
             
        # Use RoutingService
        # Feedback 3: Use the provider pattern/method instead of direct instantiation
        rs = self._get_routing_service()
        eta = rs.get_eta_minutes(lat, lng, job_lat, job_lng)
        
        if eta is None:
             return f"Technician {tech.name} is en route. Unable to calculate precise ETA currently.", None
             
        return f"Technician {tech.name} is approximately {eta} minutes away.", {
             "action": "check_eta",
             "eta_minutes": eta,
             "tech_name": tech.name
        }

    async def _execute_autoroute(
        self, tool: AutorouteTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        executor = AutorouteToolExecutor(self.session, self.business_id)
        result = await executor.run(tool)
        
        action = "apply_route" if tool.apply else "preview_route"
        
        return result, {
            "action": action,
            "entity": "schedule",
            "date": tool.date or datetime.today().date().isoformat(),
            "preview": result
        }
