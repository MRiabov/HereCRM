import logging
from typing import Any, cast, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories import (
    ConversationStateRepository,
    UserRepository,
    BusinessRepository,
    ServiceRepository,
)
from src.models import ConversationState, ConversationStatus, User, Request, Message, MessageRole
from src.services.chat_utils import format_service_list, format_line_items
from src.llm_client import LLMParser
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService
from src.services.data_management import DataManagementService
from src.services.location_service import LocationService
from src.services.billing_service import BillingService
from src.services.invitation import InvitationService

from src.config.loader import get_channel_config_loader
from src.database import AsyncSessionLocal
import asyncio
from datetime import datetime, timedelta, timezone
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
    ListServicesTool,
    ExitSettingsTool,
    ExportQueryTool,
    ExitDataManagementTool,
    GetBillingStatusTool,
    RequestUpgradeTool,
    CreateQuoteInput,
    SendStatusTool,
    LocateEmployeeTool,
    CheckETATool,
    CheckETATool,
)
from src.tools.invoice_tools import SendInvoiceTool
from src.tools.employee_management import (
    InviteUserTool,
    JoinBusinessTool,
    ExitEmployeeManagementTool,
)



class WhatsappService:
    def __init__(
        self,
        session: AsyncSession,
        parser: LLMParser,
        template_service: TemplateService,
        billing_service: Optional[BillingService] = None,
    ):
        self.session = session
        self.parser = parser
        self.parser = parser
        self.template_service = template_service
        self.billing_service = billing_service or BillingService(session)
        self.logger = logging.getLogger(__name__)
        self.state_repo = ConversationStateRepository(session)
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)
        self.business_repo = BusinessRepository(session)
        self._current_metadata = {}
        self.data_service = DataManagementService(session)
        self.invitation_service = InvitationService(session)

    async def handle_message(
        self,
        message_text: str,
        user_id: Optional[int] = None,
        user_phone: Optional[str] = None,
        channel: str = "whatsapp",
        is_new_user: bool = False,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> str:
        print(f"DEBUG: handle_message entered. user_id={user_id}, user_phone={user_phone}, channel={channel}")
        # 1. Identify User
        if user_id:
            user = await self.user_repo.get_by_id(user_id)
        elif user_phone:
            user = await self.user_repo.get_by_phone(user_phone)
        else:
            return self.template_service.render("error_user_required")

        if not user:
            # Handle "Join" for new users
            if message_text.strip().lower().startswith("join"):
                active_identity = user_phone or "unknown"
                success, msg, new_user = await self.invitation_service.process_join(active_identity)
                if success and new_user:
                    # User created, let's proceed to log the message and set up state
                    user = new_user
                    is_new_user = True
                    reply = msg # The process_join returns the welcome message
                    # We continue down to log the message properly linked to this new user
                else:
                    return self.template_service.render("error_user_required")
            else:
                return self.template_service.render("error_user_required")

        # Use the identity they chose for this message as the "from_number" 
        # (could be their email if via generic webhook)
        active_identity = user_phone or user.phone_number or user.email or "unknown"

        # Log User Message
        user_msg = Message(
            business_id=user.business_id,
            user_id=user.id,
            from_number=active_identity,
            body=message_text,
            role=MessageRole.USER,
            channel_type=channel
        )
        self.session.add(user_msg)
        await self.session.flush()

        # 2. Fetch Conversation State
        state_record = await self.state_repo.get_by_user_id(user.id)
        if not state_record:
            state_record = ConversationState(
                user_id=user.id, state=ConversationStatus.IDLE, active_channel=channel
            )
            self.state_repo.add(state_record)
            await self.session.flush()

        # Update active channel
        state_record.active_channel = channel

        # 3. State Machine Logic
        reply = ""

        # Priority: Location Update (WhatsApp Location or SMS Map Link)
        location_coords = None
        if media_type == "location":
            # Direct location message (usually text contains lat,lng or we parse it)
            location_coords = LocationService.parse_location_from_text(message_text)
            # If parse failed but it's explicitly a location message, we might need a fallback
            # assuming message_text IS "lat,lng"
            if not location_coords and "," in message_text:
                try:
                    parts = message_text.split(",")
                    lat = float(parts[0].strip())
                    lng = float(parts[1].strip())
                    location_coords = (lat, lng)
                except ValueError:
                    pass
        
        # Fallback: Check text for map links (WhatsApp or SMS)
        if not location_coords:
             location_coords = LocationService.parse_location_from_text(message_text)

        if location_coords:
            lat, lng = location_coords
            await LocationService.update_location(self.session, user.id, lat, lng)
            self.logger.info(f"Updated location for user {user.id}: {lat}, {lng}")
            return "Thanks, your location has been updated and tracking is active."

        if is_new_user:
            self.logger.info(f"New user onboarding for {active_identity}")
            reply = self.template_service.render("welcome_message")
        
        # If reply is already set (e.g. welcome message), skip state check
        if not reply:
            if state_record.state == ConversationStatus.WAITING_CONFIRM:
                self.logger.info(f"User {user.id} in WAITING_CONFIRM mode")
                reply = await self._handle_waiting_confirm(user, state_record, message_text)
            elif state_record.state == ConversationStatus.SETTINGS:
                self.logger.info(f"User {user.id} in SETTINGS mode")
                reply = await self._handle_settings(user, state_record, message_text)
            elif state_record.state == ConversationStatus.DATA_MANAGEMENT:
                self.logger.info(f"User {user.id} in DATA_MANAGEMENT mode")
                reply = await self._handle_data_management(
                    user, state_record, message_text, media_url, media_type
                )
            elif state_record.state == ConversationStatus.PENDING_AUTO_CONFIRM:
                self.logger.info(f"User {user.id} in PENDING_AUTO_CONFIRM mode")
                reply = await self._handle_pending_auto_confirm(user, state_record, message_text)
            elif state_record.state == ConversationStatus.BILLING:
                self.logger.info(f"User {user.id} in BILLING mode")
                reply = await self._handle_billing(user, state_record, message_text)
            elif state_record.state == ConversationStatus.EMPLOYEE_MANAGEMENT:
                self.logger.info(f"User {user.id} in EMPLOYEE_MANAGEMENT mode")
                reply = await self._handle_employee_management(user, state_record, message_text)
            else:
                reply = await self._handle_idle(user, state_record, message_text)

        # Log Assistant Reply
        assistant_msg = Message(
            business_id=user.business_id,
            user_id=user.id,
            from_number="system",
            to_number=active_identity,
            body=reply,
            role=MessageRole.ASSISTANT,
            channel_type=channel,
            log_metadata=self._current_metadata if self._current_metadata else None
        )
        self.session.add(assistant_msg)
        
        # T023 - Usage-Based Billing: Count assistant reply
        if self.billing_service:
            await self.billing_service.track_message_sent(user.business_id)

        
        # Dispatch SMS if channel is SMS or user identity suggests SMS
        # In multi-channel mode, we should respect the active_channel if it's set
        effective_channel = state_record.active_channel or channel
        
        if effective_channel == "sms" and user.phone_number:
            try:
                from src.services.twilio_service import TwilioService
                await TwilioService().send_sms(user.phone_number, reply)
            except Exception as e:
                self.logger.error(f"Failed to send SMS reply to {user.id}: {e}")

        return reply


    async def _handle_idle(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        # Handle Greetings
        if lower_text in ["hi", "hello", "hey", "greetings"]:
            return self.template_service.render("welcome_back")

        # Handle Undo
        if lower_text == "undo":
            return await self._handle_undo(user, state_record)

        # Handle Edit Last
        if lower_text == "edit last":
            return await self._handle_edit_last(user, state_record)

        # Handle Settings Entry
        if lower_text in ["settings", "update settings", "config"]:
            state_record.state = ConversationStatus.SETTINGS
            return self.template_service.render("settings_menu")

        # Handle Data Management Entry
        if lower_text in ["manage data", "import", "export", "import export", "data"]:
            state_record.state = ConversationStatus.DATA_MANAGEMENT
            return "You are now in Data Management mode. You can upload files (CSV, Excel) to import data, or describe what you want to export. Type 'exit' to return to the main menu."

        # Handle Billing Entry
        if lower_text in ["billing", "subscription", "upgrade", "my plan", "limits"]:
            state_record.state = ConversationStatus.BILLING
            # We explicitly execute GetBillingStatusTool immediately to show current status as entry point
            # This is a nice UX touch - user says "Billing" and gets the status immediately.
            executor = ToolExecutor(
                self.session, user.business_id, user.id, user.phone_number or "", self.template_service
            )
            try:
                result, _ = await executor.execute(GetBillingStatusTool())
                return result + "\n\n(Type 'upgrade seat' or 'buy addon' to purchase extras, or 'back' to exit)"
            except Exception as e:
                self.logger.error(f"Failed to auto-show billing status: {e}")
                return "You are now in Billing mode. Type 'status', 'upgrade', or 'back' to exit."

        # Handle Employee Management Entry
        if lower_text in ["employee management", "manage employees", "employees"]:
            # Basic RBAC check (Owner/Manager only)
            if user.role not in ["owner", "manager"]:
                 return "Access denied: Employee Management is restricted to authorized roles."
            
            state_record.state = ConversationStatus.EMPLOYEE_MANAGEMENT
            return "You are now in Employee Management mode. You can 'Invite <phone>'. Type 'exit' to return."

        # Handle Join (for existing users)
        if lower_text.startswith("join"):
             success, msg, _ = await self.invitation_service.process_join(user.phone_number or "")
             return msg

        # Parse with LLM
        from datetime import datetime, timezone

        # Fetch Service Catalog to helper parser
        service_repo = ServiceRepository(self.session)
        services = await service_repo.get_all_for_business(user.business_id)
        
        # Simple format for LLM context (lighter than the UI format)
        service_catalog_str = "\n".join(
            [f"- ID {s.id}: {s.name} (${s.default_price})" for s in services]
        ) if services else None

        # 1. Channel config for parsing
        channel_name = state_record.active_channel or "whatsapp"
        
        system_time = datetime.now(timezone.utc).isoformat()
        tool_call = await self.parser.parse(
            text, 
            system_time=system_time, 
            service_catalog=service_catalog_str,
            channel_name=channel_name
        )
        
        if tool_call:
            # Capture tool call metadata
            if not isinstance(tool_call, str):
                self._current_metadata["tool_call"] = {
                    "name": tool_call.__class__.__name__,
                    "arguments": tool_call.dict()
                }

            # Handle string response (reasoning/clarification)
            if isinstance(tool_call, str):
                return tool_call
                
            # Handle HelpTool separately (skip confirmation)
            if isinstance(tool_call, HelpTool):
                from src.services.help_service import HelpService
                help_service = HelpService(self.session, self.parser)
                return await help_service.generate_help_response(
                    user_query=text,
                    business_id=user.business_id,
                    phone_number=user.phone_number,
                    channel="whatsapp"
                )

            # Prepare state record
            state_record.draft_data = {
                "tool_name": tool_call.__class__.__name__,
                "arguments": tool_call.dict(),
            }
            
            # Check Auto-Confirm Config
            config_loader = get_channel_config_loader()
            channel_config = config_loader.get_channel_config(channel_name)
            auto_confirm = channel_config.get("auto_confirm", False)
            timeout = channel_config.get("auto_confirm_timeout", 45)

            # Generate Summary
            summary = self._generate_summary(tool_call)
            
            if auto_confirm and not isinstance(tool_call, (EditCustomerTool, UpdateSettingsTool)): 
                # Note: We might want to EXCLUDE destructive tools from auto-confirm if needed.
                # For now, following spec: "when a tool call is proposed... if auto_confirm is true"
                
                state_record.state = ConversationStatus.PENDING_AUTO_CONFIRM
                # Store timestamp in UTC
                execution_time = datetime.now(timezone.utc) + timedelta(seconds=timeout)
                state_record.pending_action_timestamp = execution_time
                
                # Spawn background task
                asyncio.create_task(self._auto_confirm_task(user.id, timeout))
                
                return f"Prepared: {summary}. Auto-confirming in {timeout}s. Reply NO to cancel."
            else:
                state_record.state = ConversationStatus.WAITING_CONFIRM
                prompt_key = (
                    "confirm_edit_prompt"
                    if isinstance(tool_call, EditCustomerTool)
                    else "confirm_prompt"
                )
                return self.template_service.render(prompt_key, summary=summary)

        # If truly unclear
        return self.template_service.render("error_unclear_input")

    async def _handle_waiting_confirm(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        if lower_text in ["yes", "y", "confirm"]:
            return await self._execute_draft(user, state_record)

        elif lower_text in ["no", "n", "cancel"]:
            self.logger.info(f"User {user.phone_number} cancelled action")
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return self.template_service.render("action_cancelled")

        else:
            # Handle edge case: new command while waiting for confirm
            confirm_by_default = user.preferences.get("confirm_by_default", False)
            if confirm_by_default:
                # Auto-execute previous draft, then process new message
                await self._execute_draft(user, state_record)
                return await self._handle_idle(user, state_record, text)
            else:
                # Discard draft, notify, and process new message
                state_record.state = ConversationStatus.IDLE
                state_record.draft_data = None
                initial_msg = "Previous draft discarded. "
                new_msg = await self._handle_idle(user, state_record, text)
                return f"{initial_msg}{new_msg}"

    async def _execute_draft(self, user: User, state_record: ConversationState) -> str:
        if not state_record.draft_data:
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("error_no_draft")

        # Reconstruct tool call from draft_data
        draft = state_record.draft_data
        tool_name = draft["tool_name"]
        arguments = draft["arguments"]

        model_map = {
            "AddJobTool": AddJobTool,
            "AddLeadTool": AddLeadTool,
            "EditCustomerTool": EditCustomerTool,
            "ScheduleJobTool": ScheduleJobTool,
            "AddRequestTool": AddRequestTool,
            "SearchTool": SearchTool,
            "UpdateSettingsTool": UpdateSettingsTool,
            "ConvertRequestTool": ConvertRequestTool,
            "HelpTool": HelpTool,
            "GetPipelineTool": GetPipelineTool,
            "UpdateCustomerStageTool": UpdateCustomerStageTool,
            "SendInvoiceTool": SendInvoiceTool,
            "GetBillingStatusTool": GetBillingStatusTool,
            "RequestUpgradeTool": RequestUpgradeTool,
            "CreateQuoteTool": CreateQuoteInput,
            "SendStatusTool": SendStatusTool,
            "LocateEmployeeTool": LocateEmployeeTool,
            "CheckETATool": CheckETATool,
        }

        tool_cls = model_map.get(tool_name)
        if not tool_cls:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return self.template_service.render("error_unknown_tool")

        tool_call = tool_cls(**arguments)

        # Execute
        executor = ToolExecutor(
            self.session, user.business_id, user.id, user.phone_number or "", self.template_service
        )
        try:
            result, metadata = await executor.execute(tool_call)
        except Exception as e:
            self.logger.exception(f"Tool execution failed: {e}")
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return f"Error during execution: {e}"

        # Track for Undo
        if metadata:
            state_record.last_action_metadata = metadata

        # Reset state
        state_record.state = ConversationStatus.IDLE
        state_record.draft_data = None

        return f"{result}"

    async def _handle_undo(self, user: User, state_record: ConversationState) -> str:
        metadata = state_record.last_action_metadata
        if not metadata:
            return self.template_service.render("error_undo_nothing")

        action = metadata.get("action")
        entity_type = cast(str, metadata.get("entity", ""))
        entity_id = metadata.get("id")

        if action == "create":
            # Compensating action: delete
            from src.repositories import JobRepository, RequestRepository

            repo_map = {"job": JobRepository, "request": RequestRepository}
            repo_cls = repo_map.get(entity_type)
            if repo_cls and isinstance(entity_id, int):
                repo = repo_cls(self.session)
                entity = await repo.get_by_id(entity_id, user.business_id)
                if entity:
                    await self.session.delete(entity)
                    state_record.last_action_metadata = None
                    return self.template_service.render(
                        "undo_deleted", entity_type=entity_type
                    )

        elif action == "update":
            # Compensating action: revert status (simplified)
            if entity_type == "job" and isinstance(entity_id, int):
                from src.repositories import JobRepository

                repo = JobRepository(self.session)
                job = await repo.get_by_id(entity_id, user.business_id)
                if job:
                    job.status = cast(str, metadata.get("old_status", "pending"))
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_job_reverted")
            elif entity_type == "request" and isinstance(entity_id, int):
                from src.repositories import RequestRepository

                repo = RequestRepository(self.session)
                req = await repo.get_by_id(entity_id, user.business_id)
                if req:
                    req.status = cast(str, metadata.get("old_status", "pending"))
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_request_reverted")

        elif action == "promote":
            # Compensating action: Re-create Request, Delete Job
            if entity_type == "job" and isinstance(entity_id, int):
                from src.repositories import JobRepository, RequestRepository

                job_repo = JobRepository(self.session)
                job = await job_repo.get_by_id(entity_id, user.business_id)
                if job:
                    # Re-create the request
                    old_content = metadata.get("old_request_content")
                    if old_content:
                        req = Request(
                            business_id=user.business_id,
                            content=cast(str, old_content),
                            status="pending",
                        )
                        self.session.add(req)

                    # Delete the job
                    await self.session.delete(job)
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_promotion_reverted")

        elif action == "update_settings":
            from src.repositories import UserRepository

            repo = UserRepository(self.session)
            old_value = metadata.get("old_value")
            key = cast(str, metadata.get("setting_key", ""))
            user_id = cast(Optional[int], metadata.get("user_id"))

            if user_id and key:
                # Revert to old value
                await repo.update_preferences(user_id, key, old_value)
                state_record.last_action_metadata = None
                return self.template_service.render("undo_setting_reverted", key=key)

        return self.template_service.render("error_undo_failed")

    async def _handle_edit_last(
        self, user: User, state_record: ConversationState
    ) -> str:
        metadata = state_record.last_action_metadata
        if not metadata:
            return self.template_service.render("error_edit_nothing")

        entity_type = cast(str, metadata.get("entity", "item"))
        # Construct summary from metadata
        details_list = []
        if name := metadata.get("customer_name"):
            details_list.append(name)
        if price := metadata.get("price"):
            # Format price for display
            if isinstance(price, (int, float)):
                price_str = f"{int(price)}$" if price == int(price) else f"{price:.2f}$"
            else:
                price_str = str(price)
            details_list.append(price_str)
        if location := metadata.get("location"):
            details_list.append(location)
        if description := metadata.get("description"):
            details_list.append(description)
        if content := metadata.get("content"):
            details_list.append(content[:50])

        details = ", ".join(details_list) if details_list else "no details"
        return self.template_service.render(
            "edit_last_prompt",
            category=metadata.get("category", entity_type).capitalize(),
            details=details,
        )

    def _generate_summary(self, tool_call: Any) -> str:
        # Map tool class names to friendly display names
        friendly_names = {
            "AddJobTool": "Job",
            "AddLeadTool": "Add Lead",
            "EditCustomerTool": "Update",
            "ScheduleJobTool": "Schedule",
            "AddRequestTool": "Request",
            "SearchTool": "Search",
            "UpdateSettingsTool": "Settings",
            "ConvertRequestTool": "Convert",
            "HelpTool": "Help",
            "GetPipelineTool": "Pipeline",
            "UpdateCustomerStageTool": "Pipeline Stage Update",
            "SendInvoiceTool": "Send Invoice",
            "GetBillingStatusTool": "Billing Status",
            "RequestUpgradeTool": "Request Upgrade",
            "LocateEmployeeTool": "Locate",
            "CheckETATool": "ETA",
        }
        model_name = tool_call.__class__.__name__
        name = friendly_names.get(model_name, model_name.replace("Tool", ""))

        # Use category if available (e.g. for AddJobTool)
        if hasattr(tool_call, "category") and tool_call.category:
            name = f"Add {tool_call.category.capitalize()}"

        if isinstance(tool_call, AddJobTool):
            price_val = "Not supplied"
            if tool_call.price is not None:
                if tool_call.price == int(tool_call.price):
                    price_val = f"{int(tool_call.price)}$"
                else:
                    price_val = f"{tool_call.price:.2f}$"

            client_details = self.template_service.render(
                "client_details",
                name=tool_call.customer_name or "Not supplied",
                phone=tool_call.customer_phone or "Not supplied",
                address=tool_call.location or "Not supplied",
            )

            line_items_detail = ""
            if hasattr(tool_call, "line_items") and tool_call.line_items:
                line_items_detail = f"\n{format_line_items(tool_call.line_items)}"

            return self.template_service.render(
                "job_summary",
                category="Job",  # AddJobTool is now strictly jobs
                client_details=client_details,
                price=price_val,
                description=tool_call.description or "Not supplied",
                status=tool_call.status.capitalize()
                if tool_call.status
                else "Pending confirmation",
                line_items=line_items_detail,
            )

        if isinstance(tool_call, AddLeadTool):
            client_details = self.template_service.render(
                "client_details",
                name=tool_call.name,
                phone=tool_call.phone or "Not supplied",
                address=tool_call.location or "Not supplied",
            )
            return self.template_service.render(
                "lead_summary",
                client_details=client_details,
                description=tool_call.details or "Not supplied",
            )

        if isinstance(tool_call, EditCustomerTool):
            changes = []
            if tool_call.name:
                changes.append(f"Name to '{tool_call.name}'")
            if tool_call.phone:
                changes.append(f"Phone to '{tool_call.phone}'")
            if tool_call.location:
                changes.append(f"Address to '{tool_call.location}'")
            if tool_call.details:
                changes.append(f"Notes to '{tool_call.details}'")

            change_summary = ", ".join(changes) if changes else "no changes"
            return f"Updating {tool_call.query}: {change_summary}"

        if isinstance(tool_call, ScheduleJobTool):
            client_details = self.template_service.render(
                "client_details",
                name=tool_call.customer_query or "Unknown",
                phone="Not supplied",
                address="Not supplied",
            )
            return self.template_service.render(
                "schedule_summary",
                client_details=client_details,
                time=tool_call.time,
            )

        if isinstance(tool_call, AddRequestTool):
            client_details = self.template_service.render(
                "client_details",
                name=tool_call.customer_name or "Not supplied",
                phone=tool_call.customer_phone or "Not supplied",
                address="Not supplied",
            )
            return self.template_service.render(
                "request_summary",
                client_details=client_details,
                time=tool_call.time,
                content=tool_call.content,
            )

        if isinstance(tool_call, GetPipelineTool):
            return "display customers by pipeline stage"

        if isinstance(tool_call, UpdateCustomerStageTool):
            return f"update {tool_call.query}'s stage to {tool_call.stage.replace('_', ' ').title()}"

        if isinstance(tool_call, SendInvoiceTool):
            return f"generate and send invoice to {tool_call.query}"

        if isinstance(tool_call, GetBillingStatusTool):
            return "check billing status"

        if isinstance(tool_call, RequestUpgradeTool):
            item = tool_call.item_id or tool_call.item_type
            return f"request upgrade for {tool_call.quantity} x {item}"

        if isinstance(tool_call, ConvertRequestTool):
            action_map = {
                "schedule": "Schedule",
                "complete": "Complete",
                "log": "Log",
                "quote": "Quote"
            }
            act = action_map.get(tool_call.action, tool_call.action).capitalize()
            return f"Convert to {act}: {tool_call.query}"

        if hasattr(tool_call, "description") and tool_call.description:
            return f"{name}: {tool_call.description}"
        elif hasattr(tool_call, "customer_query") and tool_call.customer_query:
            return f"{name}: {tool_call.customer_query}"
        elif hasattr(tool_call, "customer_name") and tool_call.customer_name:
            return f"{name}: {tool_call.customer_name}"
        elif hasattr(tool_call, "content"):
            return f"{name}: {tool_call.content[:50]}"
        elif hasattr(tool_call, "query"):
            return f"{name}: {tool_call.query}"
        return f"{name} operation"

    def _generate_help_message(self) -> str:
        return self.template_service.render("help_message")

    async def _handle_settings(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        service_repo = ServiceRepository(self.session)

        # Fetch Service Catalog for context AND listing
        services = await service_repo.get_all_for_business(user.business_id)
        
        # Simple format for LLM context (names and prices)
        service_catalog_str = "\n".join(
            [f"- {s.name} ({s.default_price})" for s in services]
        ) if services else "No services yet."

        # Parse with specialized settings parser
        tool_call = await self.parser.parse_settings(text, service_context=service_catalog_str)

        if tool_call and not isinstance(tool_call, str):
            self._current_metadata["tool_call"] = {
                "name": tool_call.__class__.__name__,
                "arguments": tool_call.dict()
            }

        if not tool_call:
            # Fallback to help menu if unclear
            return self.template_service.render("settings_menu")

        # Handle Navigation/View tools locally
        if isinstance(tool_call, ExitSettingsTool):
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")

        if isinstance(tool_call, ListServicesTool):
            formatted = format_service_list(services)
            return self.template_service.render("service_list", services=formatted)

        # Execute Modification Tools
        executor = ToolExecutor(
            self.session, user.business_id, user.id, user.phone_number or "", self.template_service
        )
        try:
            result, _ = await executor.execute(tool_call)
            return result
        except Exception as e:
            self.logger.exception(f"Settings execution failed: {e}")
            return f"Error updating settings: {e}"

    async def _handle_data_management(
        self,
        user: User,
        state_record: ConversationState,
        text: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> str:
        # Handle file upload for import
        if media_url:
            if not media_type:
                 # Infer from text if it looks like a filename, or default?
                 # Assuming webhook provides it, but if not we might check extension in url
                 pass

            # Trigger Import
            try:
                import_job = await self.data_service.import_data(
                    user.business_id, media_url, media_type or "unknown"
                )
                return f"Import started. Status: {import_job.status}. {import_job.record_count} records processed. Errors: {len(import_job.error_log) if import_job.error_log else 0}"
            except Exception as e:
                self.logger.exception(f"Import error: {e}")
                return f"Import failed: {e}"

        # Handle text commands (Export or Exit)
        tool_call = await self.parser.parse_data_management(text)

        if isinstance(tool_call, ExitDataManagementTool):
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")

        if isinstance(tool_call, ExportQueryTool):
            try:
                filters = {
                    "entity_type": tool_call.entity_type,
                    "status": tool_call.status,
                    "min_date": tool_call.min_date,
                    "max_date": tool_call.max_date
                }
                filters = {k: v for k, v in filters.items() if v is not None}
                
                export_req = await self.data_service.export_data(
                    user.business_id, tool_call.query, tool_call.format, filters=filters
                )
                if export_req.status == "completed":
                    # In a real app, public_url would be a downloadable link.
                    # Since we are local, we return the path.
                    return f"Export completed! You can download it here: {export_req.public_url}"
                else:
                    return f"Export processing... (Status: {export_req.status})"
            except Exception as e:
                self.logger.exception("Export failed")
                return f"Export failed: {str(e)}"

        return "I didn't understand that command. You can upload a file to import, or say 'Export customers in Dublin' to export data. Type 'exit' to leave."

    async def _handle_billing(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        if lower_text in ["exit", "back", "cancel", "return"]:
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")
        
        # We can implement a simple parser or just keyword matching for now,
        # but better to use the LLM if complex inputs are allowed.
        # Since T013 defined tools, let's try to parse user intent into those tools.
        
        # Check if user says "status" explicitly
        if lower_text in ["status", "check", "info"]:
            executor = ToolExecutor(
                self.session, user.business_id, user.id, user.phone_number or "", self.template_service
            )
            res, _ = await executor.execute(GetBillingStatusTool())
            return res

        # For everything else, we might need a mini-parser or rely on general tool parsing?
        # The general parser `self.parser.parse()` is designed for IDLE state mostly.
        # But we can reuse it if we tell it what tools are available, OR we construct tools manually.
        
        # Simple regex/logic for now as per "Conversational Tools" requirement
        if "seat" in lower_text:
             # Assume 1 seat unless number specified
            import re
            qty = 1
            numbers = re.findall(r'\d+', lower_text)
            if numbers:
                qty = int(numbers[0])
            
            tool = RequestUpgradeTool(item_type="seat", quantity=qty)
            state_record.draft_data = {
                "tool_name": "RequestUpgradeTool",
                "arguments": tool.dict()
            }
            # Go to confirmation
            state_record.state = ConversationStatus.WAITING_CONFIRM
            summary = self._generate_summary(tool)
            return self.template_service.render("confirm_prompt", summary=summary)

        # Allow addons
        if "addon" in lower_text or "campaign" in lower_text:
            # This is tricky without knowing addon IDs. 
            # We should probably list them or assume a generic one?
            # Let's map "campaign" to "campaign_manager" (an example ID)
            addon_id = "campaign_manager" if "campaign" in lower_text else "unknown_addon"
            tool = RequestUpgradeTool(item_type="addon", item_id=addon_id, quantity=1)
            
            state_record.draft_data = {
                "tool_name": "RequestUpgradeTool",
                "arguments": tool.dict()
            }
            state_record.state = ConversationStatus.WAITING_CONFIRM
            summary = self._generate_summary(tool)
            return self.template_service.render("confirm_prompt", summary=summary)

        return "Unknown command. Try 'status', 'buy seat', or 'back'."

    async def _handle_employee_management(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        # Check manual exit just in case parser fails or as fast path
        if text.lower().strip() in ["exit", "quit", "back", "done"]:
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")

        tool_call = await self.parser.parse_employee_management(text)
        
        if not tool_call:
            return "I didn't understand. You can 'Invite +123456789'. Type 'exit' to quit."
            
        if isinstance(tool_call, ExitEmployeeManagementTool):
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")
            
        if isinstance(tool_call, InviteUserTool):
            # Execute Invite logic
            try:
                # Basic context check again? already in state.
                invitation = await self.invitation_service.create_invitation(
                    user.business_id, user.id, tool_call.identifier
                )
                return f"Invitation sent to {tool_call.identifier}."
            except Exception as e:
                self.logger.error(f"Invite failed: {e}")
                return f"Failed to send invitation: {e}"
                
        return "Tool not implemented yet."

    async def _handle_pending_auto_confirm(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        """
        User interrupted the auto-confirm countdown.
        """
        lower_text = text.lower().strip()
        
        # Explicit confirmation
        if lower_text in ["yes", "y", "confirm", "ok", "okay"]:
            return await self._execute_draft(user, state_record)
            
        # Explicit cancellation
        if lower_text in ["no", "n", "cancel", "stop", "wait"]:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            state_record.pending_action_timestamp = None
            return self.template_service.render("action_cancelled")
            
        # Any other input acts as an interrupt and new command
        state_record.state = ConversationStatus.IDLE
        state_record.draft_data = None
        state_record.pending_action_timestamp = None
        
        # Process as new idle message
        prefix = "Auto-confirm cancelled. "
        response = await self._handle_idle(user, state_record, text)
        return prefix + response

    async def _auto_confirm_task(self, user_id: int, timeout: int):
        """
        Background task to execute draft if still pending.
        """
        try:
            await asyncio.sleep(timeout)
            
            # Create a new session for the background operation
            async with AsyncSessionLocal() as session:
                # Re-fetch state
                state_repo = ConversationStateRepository(session)
                user_repo = UserRepository(session)
                
                state_record = await state_repo.get_by_user_id(user_id)
                user = await user_repo.get_by_id(user_id)
                
                if not state_record or not user:
                    return

                # Check if still in PENDING_AUTO_CONFIRM
                if state_record.state == ConversationStatus.PENDING_AUTO_CONFIRM:
                    # Double check timestamp to be sure
                    now = datetime.now(timezone.utc)
                    if state_record.pending_action_timestamp and now >= state_record.pending_action_timestamp:
                        
                        # Execute!
                        # We need a temporary service instance
                        # Note: We need a template service and parser, but execute_draft mainly needs ToolExecutor
                        # We can instantiate a minimal WhatsappService or just copy the logic.
                        # Copying logic is safer to avoid circular deps or complex setups.
                        
                        # Reconstruct tool
                        draft = state_record.draft_data
                        if not draft:
                            return
                            
                        # ... (Simplified execution logic) ...
                        # Ideally _execute_draft should be static or separate, but it uses self.template_service
                        # I'll create a new service instance
                        
                        from src.services.template_service import TemplateService
                        from src.llm_client import parser # Use singleton
                        
                        tmp_service = WhatsappService(session, parser, TemplateService())
                        
                        result = await tmp_service._execute_draft(user, state_record)
                        
                        # Send result to user via channel
                        active_channel = state_record.active_channel or "whatsapp"
                        recipient = user.phone_number if active_channel == "sms" else (user.email or user.phone_number)
                        
                        if active_channel == "sms" and user.phone_number:
                            from src.services.twilio_service import TwilioService
                            await TwilioService().send_sms(user.phone_number, result)
                        elif active_channel == "email" and (user.email or user.phone_number): # Support email sending
                             from src.services.postmark_service import PostmarkService
                             # We need basic subject
                             to_email = user.email or user.phone_number or ""
                             if to_email:
                                 await PostmarkService().send_email(
                                     to_email=to_email,
                                     subject="Action Confirmed",
                                     body=result
                                 )
                        
                        # Log the system message
                        sys_msg = Message(
                            business_id=user.business_id,
                            user_id=user.id,
                            from_number="system",
                            to_number=recipient or "unknown",
                            body=result,
                            role=MessageRole.ASSISTANT,
                            channel_type=active_channel
                        )
                        session.add(sys_msg)
                        await session.commit()
                        
        except Exception as e:
            logging.error(f"Auto-confirm task failed for user {user_id}: {e}")

