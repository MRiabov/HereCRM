from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus, Business
from src.llm_client import LLMParser
from src.services.template_service import TemplateService
from src.services.geocoding import GeocodingService
from src.services.invitation import InvitationService
from src.services.help_service import HelpService
from src.services.chat.handlers.base import ChatHandler
from src.services.chat.utils.summary_generator import SummaryGenerator
from src.services.chat.utils.undo_handler import UndoHandler
from src.repositories import ServiceRepository
from src.config.loader import get_channel_config_loader
from src.tool_executor import ToolExecutor
from src.uimodels import (
    AddJobTool,
    AddLeadTool,
    EditCustomerTool,
    UpdateSettingsTool,
    HelpTool,
    GetBillingStatusTool,
)
import logging
from datetime import datetime, timezone, timedelta

class IdleHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        parser: LLMParser,
        template_service: TemplateService,
        summary_generator: SummaryGenerator,
        undo_handler: UndoHandler,
        geocoding_service: GeocodingService,
        invitation_service: InvitationService,
        auto_confirm_service
    ):
        self.session = session
        self.parser = parser
        self.template_service = template_service
        self.summary_generator = summary_generator
        self.undo_handler = undo_handler
        self.geocoding_service = geocoding_service
        self.invitation_service = invitation_service
        self.auto_confirm_service = auto_confirm_service
        self.logger = logging.getLogger(__name__)
        self._current_metadata = {}

    async def handle(self, user: User, state_record: ConversationState, message_text: str) -> str:
        self._current_metadata = {} # Reset metadata
        lower_text = message_text.lower().strip()

        # Handle Greetings
        if lower_text in ["hi", "hello", "hey", "greetings"]:
            return self.template_service.render("welcome_back")

        # Handle Undo
        if lower_text == "undo":
            return await self.undo_handler.handle_undo(user, state_record)

        # Handle Edit Last
        if lower_text == "edit last":
            return await self.undo_handler.handle_edit_last(user, state_record)

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
            if user.role not in ["OWNER", "MANAGER"]:
                 return "Access denied: Employee Management is restricted to authorized roles."

            state_record.state = ConversationStatus.EMPLOYEE_MANAGEMENT
            return "You are now in Employee Management mode. You can 'Invite <phone>'. Type 'exit' to return."

        # Handle Join (for existing users)
        if lower_text.startswith("join"):
             success, msg, _ = await self.invitation_service.process_join(user.phone_number or "")
             return msg

        # Parse with LLM
        service_repo = ServiceRepository(self.session)
        services = await service_repo.get_all_for_business(user.business_id)

        service_catalog_str = "\n".join(
            [f"- ID {s.id}: {s.name} (${s.default_price})" for s in services]
        ) if services else None

        channel_name = state_record.active_channel or "WHATSAPP"

        system_time = datetime.now(timezone.utc).isoformat()
        user_context = {
            "role": user.role,
            "name": user.name,
            "business_id": user.business_id,
            "phone_number": user.phone_number,
            "clerk_id": user.clerk_id
        }

        feedback = None
        tool_call = None

        for attempt in range(2): # Up to 2 attempts
            tool_call = await self.parser.parse(
                message_text,
                system_time=system_time,
                service_catalog=service_catalog_str,
                channel_name=channel_name,
                user_context=user_context,
                feedback=feedback
            )

            if not tool_call:
                break

            # Handle HelpTool separately
            if isinstance(tool_call, HelpTool):
                help_service = HelpService(self.session, self.parser)
                return await help_service.generate_help_response(
                    user_query=message_text,
                    business_id=user.business_id,
                    user_id=user.id,
                    channel=channel_name
                )

            # Geocode
            if isinstance(tool_call, (AddJobTool, AddLeadTool)) and tool_call.location:
                business = await self.session.get(Business, user.business_id)
                prefs = user.preferences or {}

                default_city = (business.default_city if business else None) or prefs.get("default_city")
                default_country = (business.default_country if business else None) or prefs.get("default_country")

                safeguard_enabled = prefs.get("geocoding_safeguard_enabled", False)
                if isinstance(safeguard_enabled, str):
                    safeguard_enabled = safeguard_enabled.lower() in ["true", "yes", "on", "1"]

                max_dist = prefs.get("geocoding_max_distance_km", 100.0)
                try:
                    max_dist = float(max_dist)
                except (ValueError, TypeError):
                    max_dist = 100.0

                phone = getattr(tool_call, "customer_phone", None) or getattr(tool_call, "phone", None)
                if not default_country and phone:
                    if phone.startswith("+353") or phone.startswith("08"):
                        default_country = "Ireland"
                    elif phone.startswith("+1"):
                        default_country = "USA"

                lat, lon, street, city, country, postal_code, full_address = await self.geocoding_service.geocode(
                    tool_call.location,
                    default_city=getattr(tool_call, "city", None) or default_city,
                    default_country=getattr(tool_call, "country", None) or default_country,
                    safeguard_enabled=safeguard_enabled,
                    max_distance_km=max_dist
                )

                if safeguard_enabled and default_city and not lat:
                    if attempt == 0:
                        self.logger.info(f"Geocoding rejected by safeguard for '{tool_call.location}', retrying with feedback...")
                        feedback = f"The location '{tool_call.location}' is too far from {default_city} or not found. Please try to infer a more accurate address or city."
                        continue
                    else:
                        return f"Sorry, the location '{tool_call.location}' seems too far from your default city ({default_city}) or could not be found. Please provide a more specific address or update your default city."

                if full_address:
                    tool_call.location = full_address
                if city and hasattr(tool_call, "city"):
                    tool_call.city = city
                if country and hasattr(tool_call, "country"):
                    tool_call.country = country

                if lat is not None:
                    tool_call.latitude = lat
                if lon is not None:
                    tool_call.longitude = lon

                if isinstance(tool_call, AddLeadTool) and street:
                    tool_call.street = street

            break

        if tool_call:
            # Capture tool call metadata
            if not isinstance(tool_call, str):
                self._current_metadata["tool_call"] = {
                    "name": tool_call.__class__.__name__,
                    "arguments": tool_call.dict()
                }

            if isinstance(tool_call, str):
                return tool_call

            if "tool_call" in self._current_metadata and not isinstance(tool_call, str):
                self._current_metadata["tool_call"]["arguments"] = tool_call.dict()

            state_record.draft_data = {
                "tool_name": tool_call.__class__.__name__,
                "arguments": tool_call.dict(),
            }

            config_loader = get_channel_config_loader()
            channel_config = config_loader.get_channel_config(channel_name)
            auto_confirm = channel_config.get("auto_confirm", False)
            timeout = channel_config.get("auto_confirm_timeout", 45)

            summary = await self.summary_generator.generate_summary(tool_call, user)

            if auto_confirm and not isinstance(tool_call, (EditCustomerTool, UpdateSettingsTool)):
                state_record.state = ConversationStatus.PENDING_AUTO_CONFIRM
                execution_time = datetime.now(timezone.utc) + timedelta(seconds=timeout)
                state_record.pending_action_timestamp = execution_time

                # Spawn background task
                self.auto_confirm_service.schedule_auto_confirm(user.id, timeout)

                return f"Prepared: {summary}. Auto-confirming in {timeout}s. Reply NO to cancel."
            else:
                state_record.state = ConversationStatus.WAITING_CONFIRM
                prompt_key = (
                    "confirm_edit_prompt"
                    if isinstance(tool_call, EditCustomerTool)
                    else "confirm_prompt"
                )
                return self.template_service.render(prompt_key, summary=summary)

        return self.template_service.render("error_unclear_input")

    def get_last_metadata(self):
        return self._current_metadata
