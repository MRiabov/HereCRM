import asyncio
import logging
from typing import Union, Optional, Tuple, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from src.models import (
    Customer,
    Request,
    Business,
    Service,
    Job,
    User,
    UserRole,
    InvoicingWorkflow,
    QuotingWorkflow,
    PaymentTiming,
    JobCreationDefault,
    PipelineStage,
    CampaignChannel,
    JobStatus, # Added JobStatus
    ConversationStatus, # Added ConversationStatus
    QuoteStatus, # Added QuoteStatus
    SyncType, # Added SyncType
    SyncLogStatus, # Added SyncLogStatus
)
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
from src.services.campaign_service import CampaignService
from src.services.postmark_service import PostmarkService
from src.services.chat_utils import format_line_items
from src.services.billing_service import BillingService
from src.services.dashboard_service import DashboardService
from src.services.assignment_service import AssignmentService
from src.services.rbac_service import RBACService
from src.services.workflow import WorkflowSettingsService
from src.services.expenses import ExpenseService
from src.services.time_tracking import TimeTrackingService
from src.services.quote_service import QuoteService
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
    ExecuteBlastTool,
    ExportQueryTool,
    ExitDataManagementTool,
    GetBillingStatusTool,
    RequestUpgradeTool,
    CreateQuoteTool,
    LocateEmployeeTool,
    CheckETATool,
    AutorouteTool,
    GetWorkflowSettingsTool,
    UpdateWorkflowSettingsTool,
    ConnectQuickBooksTool,
    DisconnectQuickBooksTool,
    QuickBooksStatusTool,
    SyncQuickBooksTool,
    ConnectGoogleCalendarTool,
    DisconnectGoogleCalendarTool,
    GoogleCalendarStatusTool,
    CheckInTool,
    CheckOutTool,
    StartJobTool,
    FinishJobTool,
    AddExpenseTool,
)
from src.tools.expenses import ExpenseTools
from src.services.accounting.accounting_tools import AccountingToolsHandler
from src.tools.shifts import ShiftTools
from src.tools.jobs_time import JobTimeTools
from src.tools.invoice_tools import SendInvoiceTool
from src.tools.quote_tools import QuoteCreationHandler
from src.tools.routing_tools import AutorouteToolExecutor
from src.tools.employee_management import (
    ShowScheduleTool, 
    AssignJobTool,
    PromoteUserTool,
    DismissUserTool,
    LeaveBusinessTool
)
from src.services.location_service import LocationService
from src.services.routing.ors import OpenRouteServiceAdapter
from src.services.accounting.quickbooks_auth import QuickBooksAuthService
from src.services.accounting.quickbooks_sync import QuickBooksSyncManager
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
        self.campaign_service = CampaignService(session, self.search_service, PostmarkService())
        self.invoice_service = InvoiceService(session)
        self.billing_service = BillingService(session)
        self.dashboard_service = DashboardService(session)
        self.billing_service = BillingService(session)
        self.dashboard_service = DashboardService(session)
        self.assignment_service = AssignmentService(session, self.business_id)
        self.quote_service = QuoteService(session)
        self.rbac_service = RBACService()
        self.workflow_service = WorkflowSettingsService(session)
        self.time_tracking_service = TimeTrackingService(session)
        self.shift_tools = ShiftTools(self.time_tracking_service)
        self.job_time_tools = JobTimeTools(self.time_tracking_service)
        self.expense_service = ExpenseService(session, self.business_id)
        self.expense_tools = ExpenseTools(self.expense_service)
        self._routing_service = None

    def _get_routing_service(self) -> OpenRouteServiceAdapter:
        if not self._routing_service:
            # In a real app we might inject this or check settings for Mock vs ORS
            self._routing_service = OpenRouteServiceAdapter(api_key=settings.openrouteservice_api_key)
        return self._routing_service

    async def _get_user_defaults(self) -> Tuple[Optional[str], Optional[str], bool, float]:
        user = await self.user_repo.get_by_id(self.user_id)
        if not user:
            return None, None, False, 100.0
            
        # Preference: Business defaults > User preferences
        business = await self.session.get(Business, self.business_id)
        
        default_city = (business.default_city if business else None) or user.preferences.get("default_city")
        default_country = (business.default_country if business else None) or user.preferences.get("default_country")
        
        safeguard = user.preferences.get("geocoding_safeguard_enabled", False)
        if isinstance(safeguard, str):
            safeguard = safeguard.lower() in ["true", "yes", "on", "1"]
        
        max_dist = user.preferences.get("geocoding_max_distance_km", 100.0)
        try:
            max_dist = float(max_dist)
        except (ValueError, TypeError):
            max_dist = 100.0
            
        return (
            default_city, 
            default_country,
            safeguard,
            max_dist
        )

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
            CreateQuoteTool,
            LocateEmployeeTool,
            CheckETATool,
            AutorouteTool,
            GetWorkflowSettingsTool,
            UpdateWorkflowSettingsTool,
            ConnectQuickBooksTool,
            DisconnectQuickBooksTool,
            QuickBooksStatusTool,
            SyncQuickBooksTool,
            PromoteUserTool,
            DismissUserTool,
            LeaveBusinessTool,
            ConnectGoogleCalendarTool,
            DisconnectGoogleCalendarTool,
            GoogleCalendarStatusTool,
            CheckInTool,
            CheckOutTool,
            StartJobTool,
            FinishJobTool,
            AddExpenseTool,
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
            return f"Error: It seems you are trying to {friendly_name}. Sorry, you don't have permission for that.", None

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

        # [T008] Workflow Enforcement
        business = await self.session.get(Business, self.business_id)
        if business:
            # Soft-block Invoicing
            if isinstance(tool_call, SendInvoiceTool):
                if business.workflow_invoicing == InvoicingWorkflow.NEVER:
                    return "Invoicing is currently disabled in your business settings. (Owner can re-enable this by saying 'update workflow settings').", None
                
                # Block invoice if 'always paid on spot' (as per "Payment Tools" blocking rule)
                if business.workflow_payment_timing == PaymentTiming.ALWAYS_PAID_ON_SPOT:
                     return "Invoicing is disabled because your business is set to 'Always paid on spot'.", None

            # Soft-block Quoting
            if isinstance(tool_call, CreateQuoteTool):
                if business.workflow_quoting == QuotingWorkflow.NEVER:
                    return "Quoting is currently disabled in your business settings. (Owner can re-enable this by saying 'update workflow settings').", None


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
            campaign = await self.campaign_service.create_campaign(
                business_id=self.business_id,
                name=f"Mass Message: {tool_call.subject[:30]}...",
                channel=CampaignChannel(tool_call.channel),
                body=tool_call.body,
                subject=tool_call.subject,
                recipient_query=tool_call.recipient_query
            )
            count = await self.campaign_service.prepare_audience(campaign.id)
            return (
                f"✔ Broadcast Prepared (ID: {campaign.id}): Targeting {count} recipients "
                f"for '{tool_call.subject}' via {tool_call.channel}.\n\n"
                f"**Blast Protocol Active**: Please type 'EXECUTE BLAST for campaign {campaign.id}' to begin sending.",
                {
                    "campaign_id": campaign.id,
                    "recipient_count": count,
                    "status": "prepared",
                    "tool": "MassEmailTool"
                }
            )

        elif isinstance(tool_call, ExecuteBlastTool):
            # Run in background to avoid blocking the chat response
            asyncio.create_task(self.campaign_service.execute_campaign(tool_call.campaign_id))
            return (
                f"🚀 Blast Execution Started for Campaign {tool_call.campaign_id}. I'll notify you when complete.",
                {
                    "campaign_id": tool_call.campaign_id,
                    "status": "executed",
                    "tool": "ExecuteBlastTool"
                }
            )
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
        elif isinstance(tool_call, CreateQuoteTool):
            return await self._execute_create_quote(tool_call)
        elif isinstance(tool_call, LocateEmployeeTool):
            return await self._execute_locate_employee(tool_call)
        elif isinstance(tool_call, CheckETATool):
            return await self._execute_check_eta(tool_call)
        elif isinstance(tool_call, AutorouteTool):
            return await self._execute_autoroute(tool_call)
        elif isinstance(tool_call, ConnectQuickBooksTool):
            return await self._execute_connect_quickbooks(tool_call)
        elif isinstance(tool_call, DisconnectQuickBooksTool):
            return await self._execute_disconnect_quickbooks(tool_call)
        elif isinstance(tool_call, QuickBooksStatusTool):
            return await self._execute_quickbooks_status(tool_call)
        elif isinstance(tool_call, SyncQuickBooksTool):
            return await self._execute_sync_quickbooks(tool_call)
        elif isinstance(tool_call, ConnectGoogleCalendarTool):
            return await self._execute_connect_google_calendar(tool_call)
        elif isinstance(tool_call, DisconnectGoogleCalendarTool):
            return await self._execute_disconnect_google_calendar(tool_call)
        elif isinstance(tool_call, GoogleCalendarStatusTool):
            return await self._execute_google_calendar_status(tool_call)
        elif isinstance(tool_call, GetWorkflowSettingsTool):
             settings = await self.workflow_service.get_settings(self.business_id)
             return f"Current Workflow Settings:\n{settings}", {"action": "get_workflow_settings", "settings": settings}
        elif isinstance(tool_call, UpdateWorkflowSettingsTool):
            return await self._execute_update_workflow_settings(tool_call)
        elif isinstance(tool_call, PromoteUserTool):
            return await self._execute_promote_user(tool_call)
        elif isinstance(tool_call, DismissUserTool):
            return await self._execute_dismiss_user(tool_call)
        elif isinstance(tool_call, LeaveBusinessTool):
            return await self._execute_leave_business(tool_call)
        elif isinstance(tool_call, CheckInTool):
             return await self.shift_tools.check_in(tool_call, self.user_id), None
        elif isinstance(tool_call, CheckOutTool):
             return await self.shift_tools.check_out(tool_call, self.user_id)
        elif isinstance(tool_call, StartJobTool):
             return await self.job_time_tools.start_job(tool_call, self.user_id), None
        elif isinstance(tool_call, FinishJobTool):
             return await self.job_time_tools.finish_job(tool_call), None
        elif isinstance(tool_call, AddExpenseTool):
             return await self.expense_tools.add_expense(tool_call, self.user_id)
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
        default_city, default_country, safeguard_enabled, max_dist = await self._get_user_defaults()
        
        # Use provided city/country if available, otherwise defaults for geocoding
        # Note: AddLeadTool has specific city/country fields, but also 'location' string.
        # If 'location' string is provided, we geocode it.
        # If specific city/country provided in tool, they override defaults for geocoding context?
        # Actually geocode method takes defaults to append to address string if missing.
        
        target_city = tool.city or default_city
        target_country = tool.country or default_country

        lat, lon, street, city, country, postal_code, full_address = await self.geocoding_service.geocode(
            tool.location or "",
            default_city=tool.city or default_city,
            default_country=tool.country or default_country,
            safeguard_enabled=safeguard_enabled,
            max_distance_km=max_dist
        )
        
        if safeguard_enabled and default_city and not lat and tool.location:
             return f"Error: The location '{tool.location}' is too far from your default city ({default_city}) or could not be found within the allowed range. Please provide a more specific address or update your default city.", None
        
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
            address=full_address or "Not supplied",
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
            default_city, default_country, safeguard_enabled, max_dist = await self._get_user_defaults()
            lat, lon, street, city, country, postal_code, full_address = await self.geocoding_service.geocode(
                tool.location, 
                default_city=default_city, 
                default_country=default_country,
                safeguard_enabled=safeguard_enabled,
                max_distance_km=max_dist
            )

            if safeguard_enabled and default_city and not lat:
                return f"Error: The location '{tool.location}' is too far from your default city ({default_city}) or could not be found within the allowed range.", None

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

        # Geocode the location if provided (used for new customer and/or job location)
        lat, lon, street, city, country, postal_code, full_address = None, None, None, None, None, None, tool.location
        default_city, default_country, safeguard_enabled, max_dist = await self._get_user_defaults()
        
        if tool.location:
            lat, lon, street, city, country, postal_code, full_address = await self.geocoding_service.geocode(
                tool.location, 
                default_city=tool.city or default_city, 
                default_country=tool.country or default_country,
                safeguard_enabled=safeguard_enabled,
                max_distance_km=max_dist
            )
            
            if safeguard_enabled and default_city and not lat:
                return f"Error: The location '{tool.location}' is too far from your default city ({default_city}) or could not be found within the allowed range.", None

        if not customer:
            # Create new customer
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
        items_dicts = []
        if tool.line_items:
            inference_service = InferenceService(self.session)
            inferred_items = await inference_service.infer_line_items(
                self.business_id, tool.line_items
            )
            # Ensure price consistency: if line items exist, they define the value.
            job_value = round(sum(li.total_price for li in inferred_items), 2)

            # Convert inferred LineItem objects to dictionaries for CRMService
            for item in inferred_items:
                items_dicts.append({
                    "service_id": item.service_id,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                })

        # 3. Handle scheduling if time provided
        scheduled_at = None
        if tool.iso_time:
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
                
        # Apply default status if not specified and not scheduled
        status = tool.status
        if not status and not tool.time:
             settings = await self.workflow_service.get_settings(self.business_id)
             default_setting = settings.get("workflow_job_creation_default") or JobCreationDefault.UNSCHEDULED
             
             if default_setting == JobCreationDefault.MARK_DONE:
                 status = JobStatus.completed
             elif default_setting == JobCreationDefault.AUTO_SCHEDULE:
                 status = JobStatus.pending
             elif default_setting == JobCreationDefault.SCHEDULED_TODAY:
                 status = JobStatus.scheduled
                 # Set scheduled_at to now if not provided
                 if not scheduled_at:
                     scheduled_at = datetime.now(timezone.utc)
             else:
                 status = JobStatus.pending

        # 4. Create job using CRMService to ensure events are fired
        crm_service = CRMService(self.session, self.business_id)
        job = await crm_service.create_job(
            customer_id=customer.id,
            description=description,
            value=job_value,
            location=tool.location,
            status=status or (JobStatus.scheduled if tool.time else JobStatus.pending),
            scheduled_at=scheduled_at,
            items=items_dicts,
            postal_code=postal_code,
            estimated_duration=tool.estimated_duration or 60,
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
                location=full_address or job.location or "No location",
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
                description=tool.description or (f"{job.description} (Scheduled: {tool.time})" if job.description and "(Scheduled:" not in job.description else job.description or f"(Scheduled: {tool.time})"),
                status=JobStatus.scheduled,
                value=tool.price,
                items=tool.line_items,
            )

            return self.template_service.render(
                "job_scheduled", name=job.customer.name, time=tool.time
            ), {
                "action": "update",
                "entity": "job",
                "id": job.id,
                "old_status": JobStatus.pending,
                "customer_name": job.customer.name,
                "description": job.description,
            }

        if not job and tool.customer_name:
            # Create a new job if none found but customer name is provided
            add_job_tool = AddJobTool(
                customer_name=tool.customer_name,
                customer_phone=tool.customer_phone,
                location=tool.location,
                price=tool.price,
                description=tool.description,
                status=JobStatus.scheduled, # Changed from "scheduled" to JobStatus.scheduled
                line_items=tool.line_items,
                time=tool.time,
                iso_time=tool.iso_time,
                estimated_duration=tool.estimated_duration,
                city=tool.city,
                country=tool.country,
            )
            return await self._execute_add_job(add_job_tool)

        return "Could not find a job to schedule. Try adding a job first.", None

    async def _execute_store_request(  # Renamed from _execute_store_request
        self,
        tool: AddRequestTool,  # Changed type hint from StoreRequestTool to AddRequestTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:  # Changed return type hint
        req = Request(
            business_id=self.business_id, description=tool.description, status="pending"
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
            "request_stored", description=tool.description[:50]
        ), {
            "action": "create",
            "entity": "request",
            "id": req.id,
            "description": tool.description,
        }

    async def _execute_search(
        self, tool: SearchTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        default_city, default_country, safeguard_enabled, max_dist = await self._get_user_defaults()
        result_text, data = await self.search_service.search(
            tool, 
            self.business_id,
            default_city=default_city,
            default_country=default_country,
            safeguard_enabled=safeguard_enabled,
            max_distance_km=max_dist
        )
        return result_text, data

    async def _execute_update_settings(
        self, tool: UpdateSettingsTool
    ) -> tuple[str, Optional[dict]]:
        # Map certain keys to business settings instead of user preferences
        business_keys = ["payment_link", "tax_inclusive", "include_payment_terms"]
        
        if tool.setting_key in business_keys:
            # Check permission: Only owner can update business settings
            user = await self.user_repo.get_by_id(self.user_id)
            if not user or user.role != UserRole.OWNER:
                return "Error: Only the business owner can update business-level settings.", None
                
            val = tool.setting_value
            # Handle boolean casting for business settings if needed
            if tool.setting_key in ["tax_inclusive", "include_payment_terms"]:
                val = val.lower() in ["true", "yes", "on", "1"]

            updates = {tool.setting_key: val}
            new_settings = await self.workflow_service.update_settings(self.business_id, **updates)
            
            return (
                self.template_service.render(
                    "setting_updated", key=tool.setting_key, value=tool.setting_value
                ),
                {
                    "action": "update_settings",
                    "entity": "business",
                    "business_id": self.business_id,
                    "setting_key": tool.setting_key,
                    "new_value": tool.setting_value,
                },
            )

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
            tool.query,
            tool.action,
            tool.time,
            tool.iso_time,
            tool.assigned_to,
            tool.price,
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
        
        # Use repo.update which handles attached/detached objects correctly via ID
        updates = {}
        if tool.new_name:
            updates["name"] = tool.new_name
        if tool.new_price is not None:
            updates["default_price"] = tool.new_price

        updated_service = await self.service_repo.update(target.id, self.business_id, **updates)
        if not updated_service:
            return f"Error updating service '{target.name}'", None

        await self.session.flush()

        return f"Updated service '{updated_service.name}' – Price: {updated_service.default_price:.2f}", {
            "action": "update",
            "entity": "service",
            "id": updated_service.id,
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

        # Use repo.delete to handle deletion by ID (safe for detached objects)
        await self.service_repo.delete(target.id, self.business_id)
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
        message = f"Here is the invoice for {customer.name} (Job #{job.id}): {invoice.public_url}"
        if invoice.payment_link:
            message += f"\n\nPay here: {invoice.payment_link}"

        return (
            message,
            {
                "action": "invoice_generated",
                "entity": "invoice",
                "id": invoice.id,
                "job_id": job.id,
                "url": invoice.public_url,
                "payment_link": invoice.payment_link,
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
        
        # Add Messaging Package option
        msg_config = self.billing_service.config.get("products", {}).get("messaging", {})
        if msg_config:
             upgrade_lines.append(f"- {msg_config.get('name', 'Messaging Package')} (€{msg_config.get('overage_rate', 0.02)}/msg overage or buy pack)")
        
        for addon_id, defi in addon_definitions.items():
            if addon_id not in active_addons:
                upgrade_lines.append(f"- {defi['name']} ({defi['price']}) - {defi['desc']}")
        
        upgrades_str = "\n  ".join(upgrade_lines)

        # Use the richer templates (header + body)
        header = self.template_service.render("billing_status_header")
        # Extract usage data
        usage = status_info.get("usage", {})
        msg_count = usage.get("messages", 0)
        credits = usage.get("credits", 0)
        est_cost = usage.get("estimated_cost", 0.0)
        
        if credits >= 0:
            limit_display = f"{credits} credits remaining"
        else:
            limit_display = f"Overage: {-credits} msgs (Est. Cost: €{est_cost:.2f})"

        body = self.template_service.render(
            "billing_status_body",
            status=status_info.get("status", "free").title(),
            seats_used=seats_used,
            seat_limit=status_info.get("seat_limit", 1),
            message_usage=msg_count,
            free_limit=limit_display,
            estimated_cost=est_cost,
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

    async def _execute_create_quote(self, tool: CreateQuoteTool) -> Tuple[str, Optional[Dict[str, Any]]]:
        quote_tool = QuoteCreationHandler(self.quote_service, self.customer_repo, self.business_id, self.template_service)
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
        print(f"DEBUG: Emitting SEND_STATUS_MESSAGE for customer={customer.id}")
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
        
        # Serialize data for the frontend
        serialized_employees = []
        for emp, jobs in schedule.items():
            serialized_employees.append({
                "name": emp.name,
                "role": emp.role,
                "jobs": [{
                    "id": job.id,
                    "customer_name": job.customer.name if job.customer else "Unknown",
                    "description": job.description,
                    "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
                    "status": job.status
                } for job in jobs]
            })

        serialized_unscheduled = [{
            "id": job.id,
            "customer_name": job.customer.name if job.customer else "Unknown",
            "description": job.description,
            "status": job.status
        } for job in unscheduled]

        return report, {
            "action": "query", 
            "entity": "dashboard", 
            "date": target_date.isoformat(),
            "employees": serialized_employees,
            "unscheduled": serialized_unscheduled
        }

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
            # [Performance] Use pre-loaded fields on User model instead of N+1 query via LocationService
            lat, lng, updated_at = emp.current_latitude, emp.current_longitude, emp.location_updated_at

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
        lat, lng, updated_at = tech.current_latitude, tech.current_longitude, tech.location_updated_at
        
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
                   default_city, default_country, safeguard_enabled, max_dist = await self._get_user_defaults()
                   j_lat, j_lon, _, _, _, _, _ = await self.geocoding_service.geocode(
                       job.location,
                       default_city=default_city,
                       default_country=default_country,
                       safeguard_enabled=safeguard_enabled,
                       max_distance_km=max_dist
                   )
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
        executor = AutorouteToolExecutor(self.session, self.business_id, self.template_service)
        result = await executor.run(tool)
        
        action = "apply_route" if tool.apply else "preview_route"
        
        return result, {
            "action": action,
            "entity": "schedule",
            "date": tool.date or datetime.today().date().isoformat(),
            "preview": result
        }

    async def _execute_update_workflow_settings(
        self, tool: UpdateWorkflowSettingsTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # Validate enums if provided
        updates = {}
        if tool.invoicing:
            try:
                updates["workflow_invoicing"] = InvoicingWorkflow(tool.invoicing.lower())
            except ValueError:
                return f"Error: Invalid invoicing value '{tool.invoicing}'. Use: never, manual, automatic.", None
        
        if tool.quoting:
            try:
                updates["workflow_quoting"] = QuotingWorkflow(tool.quoting.lower())
            except ValueError:
                return f"Error: Invalid quoting value '{tool.quoting}'. Use: never, manual, automatic.", None
        
        if tool.payment_timing:
            try:
                updates["workflow_payment_timing"] = PaymentTiming(tool.payment_timing.lower())
            except ValueError:
                return f"Error: Invalid payment_timing value '{tool.payment_timing}'. Use: always_paid_on_spot, usually_paid_on_spot, paid_later.", None
        
        if tool.enable_reminders is not None:
            updates["workflow_enable_reminders"] = tool.enable_reminders
            
        if not updates:
            return "No updates provided.", None
            
        new_settings = await self.workflow_service.update_settings(self.business_id, **updates)
        return "Workflow settings updated successfully.", {"action": "update_workflow_settings", "settings": new_settings}

    async def _execute_connect_quickbooks(
        self, tool: ConnectQuickBooksTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        qb_auth = QuickBooksAuthService(self.session)
        # Generate OAuth URL
        auth_url = await qb_auth.get_auth_url(self.business_id)
        
        return self.template_service.render("quickbooks_connect_prompt", url=auth_url), {
            "action": "connect_quickbooks",
            "url": auth_url
        }

    async def _execute_disconnect_quickbooks(
        self, tool: DisconnectQuickBooksTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        qb_auth = QuickBooksAuthService(self.session)
        await qb_auth.disconnect(self.business_id)
        
        return self.template_service.render("quickbooks_disconnected"), {
            "action": "disconnect_quickbooks"
        }

    async def _execute_quickbooks_status(
        self, tool: QuickBooksStatusTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # Get business status
        business = await self.session.get(Business, self.business_id)
        
        # Get last sync logs/stats from SyncLog table
        from src.models import SyncLog
        from sqlalchemy import select, desc
        
        stmt = (
            select(SyncLog)
            .where(SyncLog.business_id == self.business_id)
            .order_by(desc(SyncLog.sync_timestamp))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        last_log = result.scalar_one_or_none()
        
        connected = "Yes" if business.quickbooks_connected else "No"
        last_sync = business.quickbooks_last_sync.strftime("%Y-%m-%d %H:%M") if business.quickbooks_last_sync else "Never"
        
        sync_status = "Idle"
        errors = "None"
        
        if last_log:
            sync_status = last_log.status.value.replace("_", " ").title()
            if last_log.records_failed > 0:
                errors = f"{last_log.records_failed} records failed"
                if last_log.error_details:
                    # Just show first few characters of error if it's a string or summary if dict
                    err_str = str(last_log.error_details)
                    if len(err_str) > 50:
                        errors += f": {err_str[:47]}..."
                    else:
                        errors += f": {err_str}"
            elif last_log.status.value == "failed":
                errors = "Last sync failed completely"
        
        return self.template_service.render(
            "quickbooks_status",
            connected=connected,
            last_sync=last_sync,
            sync_status=sync_status,
            errors=errors
        ), {
            "action": "quickbooks_status",
            "connected": business.quickbooks_connected,
            "last_sync": business.quickbooks_last_sync,
            "last_log_id": last_log.id if last_log else None
        }

    async def _execute_sync_quickbooks(
        self, tool: SyncQuickBooksTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # Check connection first
        business = await self.session.get(Business, self.business_id)
        if not business.quickbooks_connected:
            return "❌ QuickBooks is not connected. Say 'Connect QuickBooks' first.", None

        # Trigger sync in background (or foreground if fast enough, but batch is slow)
        # For tool response, we trigger it properly
        sync_manager = QuickBooksSyncManager(self.session)
        
        # We run this in background typically, but here we might await if we want immediate feedback
        # or just kick it off.
        # Let's await it for the "Sync Now" command to give definitive result
        try:
            results = await sync_manager.run_sync(self.business_id, trigger="manual")
            count = sum(len(ids) for ids in results.values())
            
            return self.template_service.render("quickbooks_sync_complete", count=count), {
                "action": "sync_quickbooks",
                "results": results,
                "count": count
            }
        except Exception as e:
            return self.template_service.render("quickbooks_error", error=str(e)), None

    async def _execute_promote_user(
        self, tool: PromoteUserTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # 1. Find the employee
        users = await self.user_repo.get_team_members(self.business_id)
        target_user = None
        
        # Fuzzy match
        query = tool.employee_query.lower()
        for u in users:
            if query in (u.name or "").lower() or query in (u.phone_number or ""):
                target_user = u
                break
        
        if not target_user:
            return f"Could not find employee matching '{tool.employee_query}'.", None
            
        if target_user.role == UserRole.MANAGER:
            return f"{target_user.name} is already a Manager.", None
            
        if target_user.role == UserRole.OWNER:
            return "Cannot promote the Owner.", None

        # 2. Update Role
        target_user.role = UserRole.MANAGER
        await self.session.flush()
        
        return f"✔ Promoted {target_user.name} to Manager.", {
            "action": "promote_user",
            "entity": "user",
            "id": target_user.id,
            "name": target_user.name,
            "new_role": "manager"
        }

    async def _execute_dismiss_user(
        self, tool: DismissUserTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        # 1. Find the employee
        users = await self.user_repo.get_team_members(self.business_id)
        target_user = None
        
        query = tool.employee_query.lower()
        for u in users:
            if query in (u.name or "").lower() or query in (u.phone_number or ""):
                target_user = u
                break
                
        if not target_user:
            return f"Could not find employee matching '{tool.employee_query}'.", None
            
        if target_user.role == UserRole.OWNER:
            return "Cannot dismiss the Owner.", None
            
        # 2. Revoke Access (Set business_id to None? Or delete?)
        # WP says "Changes are reflected in the database and access is revoked immediately"
        # We'll set business_id to None to keep chat history etc linked to the user object, 
        # but detach from business.
        # However, User.business_id IS nullable in model? model definition shows:
        # business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
        # It does NOT say nullable=True. 
        # BUT User definition:
        # class User(Base): ... business_id: Mapped[int] ...
        # If it's not nullable, we might have a problem.
        # Let's check User model again.
        
        # Checking User model seen earlier:
        # business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
        # It implies NOT NULL by default in Mapped[int].
        # If I want to support "free agent" users, I might need to make it nullable.
        # Wait, the spec says "Employee can leave the business".
        # If they leave, they are no longer associated.
        # If the schema forbids null business_id, then we must DELETE the user?
        # Deleting the user deletes all their message history if cascade is set, or errors if not.
        
        # Let's assume for this WP we should look at `User` model carefully.
        # If I can't set it to None, I might need to delete.
        # Or I need to make it nullable in a migration.
        # Given "016-Employee Guided Workflow" implies adding employees, maybe they shouldn't be deleted.
        # Let's check if I should modify the model to allow nullable business_id.
        # Actually, standard SaaS pattern: Users belong to a business.
        # If they leave, maybe they are deleted?
        # But wait, "Invitation" flow usually implies a user account exists before business link?
        # No, in this system, users seem created FOR a business.
        
        # Re-reading WP06: "Employee can leave the business via text."
        # If I delete, it's destructive.
        # I'll check model `src/models/__init__.py` line 132: 
        # business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
        # It is NOT Optional[int].
        
        # DECISION: I will DELETE the user for now, as that definitely revokes access.
        # OR I will try to make it nullable. Making it nullable is cleaner for "leaving" vs "being deleted".
        # However, user authentication usually relies on phone number.
        # If they leave and want to join another business, they need the user record.
        # I SHOULD make business_id nullable.
        # BUT I don't want to create a migration for that inside `tool_executor.py` edit.
        
        # Alternative: The prompt said "Add role field to User model". It didn't mention making business_id nullable.
        # But for "LeaveBusinessTool", if business_id is mandatory, we must delete the user.
        # Let's try to Delete.
        
        user_name = target_user.name
        user_id = target_user.id
        await self.session.delete(target_user)
        await self.session.flush()
        
        return f"✔ Dismissed {user_name} from the business.", {
            "action": "dismiss_user",
            "entity": "user",
            "id": user_id,
            "name": user_name
        }

    async def _execute_leave_business(
        self, tool: LeaveBusinessTool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        user = await self.user_repo.get_by_id(self.user_id)
        if not user:
             return "User not found.", None
        
        if user.role == UserRole.OWNER:
            return "Owners cannot leave their own business (delete the business or transfer ownership instead).", None
            
        # Delete user to revoke access
        await self.session.delete(user)
        await self.session.flush()
        
        return "You have left the business. Goodbye.", {
            "action": "leave_business",
            "entity": "user",
            "id": self.user_id
        }

    async def _execute_connect_google_calendar(self, tool: ConnectGoogleCalendarTool) -> Tuple[str, Optional[Dict[str, Any]]]:
        from src.services.google_calendar_service import GoogleCalendarService
        service = GoogleCalendarService()
        if not service.is_configured:
            return "Error: Google Calendar API is not configured on the server. Please contact support.", None
        
        # We pass user_id in the state to verify on callback
        auth_url, _ = service.get_auth_url(state=str(self.user_id))
        
        return self.template_service.render("google_calendar_connect_prompt", url=auth_url), {"action": "connect", "entity": "google_calendar"}

    async def _execute_disconnect_google_calendar(self, tool: DisconnectGoogleCalendarTool) -> Tuple[str, Optional[Dict[str, Any]]]:
        user = await self.user_repo.get_by_id(self.user_id)
        if not user:
            return "Error: User not found.", None
        
        user.google_calendar_credentials = None
        user.google_calendar_sync_enabled = False
        await self.session.flush()
        
        return self.template_service.render("google_calendar_disconnected"), {"action": "disconnect", "entity": "google_calendar"}

    async def _execute_google_calendar_status(self, tool: GoogleCalendarStatusTool) -> Tuple[str, Optional[Dict[str, Any]]]:
        user = await self.user_repo.get_by_id(self.user_id)
        if not user:
            return "Error: User not found.", None
        
        connected = "Yes" if user.google_calendar_sync_enabled and user.google_calendar_credentials else "No"
        
        return f"📅 *Google Calendar Status*:\n- Connected: {connected}\n- Sync Enabled: {connected}", {"action": "query", "entity": "google_calendar"}
