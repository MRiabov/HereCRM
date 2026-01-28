import logging
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories import (
    ConversationStateRepository,
    UserRepository,
    BusinessRepository,
)
from src.models import ConversationState, ConversationStatus, Message, MessageRole, MessageType
from src.llm_client import LLMParser
from src.services.template_service import TemplateService
from src.services.data_management import DataManagementService
from src.services.location_service import LocationService
from src.services.billing_service import BillingService
from src.services.geocoding import GeocodingService
from src.services.invitation import InvitationService
from src.services.chat.utils.summary_generator import SummaryGenerator
from src.services.chat.utils.undo_handler import UndoHandler
from src.services.chat.utils.draft_executor import DraftExecutor
from src.services.chat.auto_confirm import AutoConfirmService
from src.services.chat.handlers.settings import SettingsHandler
from src.services.chat.handlers.data_management import DataManagementHandler
from src.services.chat.handlers.billing import BillingHandler
from src.services.chat.handlers.employee import EmployeeHandler
from src.services.chat.handlers.onboarding import OnboardingHandler
from src.services.chat.handlers.confirmation import ConfirmationHandler
from src.services.chat.handlers.idle import IdleHandler


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
        self.template_service = template_service
        self.billing_service = billing_service or BillingService(session)
        self.geocoding_service = GeocodingService()
        self.logger = logging.getLogger(__name__)
        self.state_repo = ConversationStateRepository(session)
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)
        self._current_metadata = {}
        self.data_service = DataManagementService(session)
        self.invitation_service = InvitationService(session)

        # Utils
        self.summary_generator = SummaryGenerator(session, template_service)
        self.undo_handler = UndoHandler(session, template_service)
        self.draft_executor = DraftExecutor(session, template_service)
        self.auto_confirm_service = AutoConfirmService()

        # Handlers
        self.idle_handler = IdleHandler(
            session,
            parser,
            template_service,
            self.summary_generator,
            self.undo_handler,
            self.geocoding_service,
            self.invitation_service,
            self.auto_confirm_service
        )
        self.settings_handler = SettingsHandler(session, parser, template_service)
        self.data_management_handler = DataManagementHandler(session, parser, template_service, self.data_service)
        self.billing_handler = BillingHandler(session, template_service, self.summary_generator)
        self.employee_handler = EmployeeHandler(session, parser, template_service, self.invitation_service)
        self.onboarding_handler = OnboardingHandler(session, template_service, self.invitation_service)
        self.confirmation_handler = ConfirmationHandler(session, template_service, self.draft_executor, self.idle_handler)

    async def handle_message(
        self,
        message_text: str,
        user_id: Optional[int] = None,
        user_phone: Optional[str] = None,
        channel: MessageType = MessageType.WHATSAPP,
        is_new_user: bool = False,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> str:
        self.logger.debug(f"DEBUG: handle_message entered. user_id={user_id}, user_phone={user_phone}, channel={channel}")
        
        self._current_metadata = {}
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
                else:
                    return self.template_service.render("error_user_required")
            else:
                return self.template_service.render("error_user_required")

        # Use the identity they chose for this message as the "from_number" 
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

        # Priority: Location Update
        location_coords = None
        if media_type == "location":
            location_coords = LocationService.parse_location_from_text(message_text)
            if not location_coords and "," in message_text:
                try:
                    parts = message_text.split(",")
                    lat = float(parts[0].strip())
                    lng = float(parts[1].strip())
                    location_coords = (lat, lng)
                except ValueError:
                    pass
        
        # Fallback: Check text for map links
        if not location_coords:
             location_coords = LocationService.parse_location_from_text(message_text)

        if location_coords:
            lat, lng = location_coords
            await LocationService.update_location(self.session, user.id, lat, lng)
            self.logger.info(f"Updated location for user {user.id}: {lat}, {lng}")
            return "Thanks, your location has been updated and tracking is active."

        if is_new_user:
            self.logger.info(f"New user onboarding for {active_identity}")
            state_record.state = ConversationStatus.ONBOARDING
            reply = self.template_service.render("welcome_message")
        
        # Dispatch to Handlers
        if not reply:
            if state_record.state == ConversationStatus.ONBOARDING:
                self.logger.info(f"User {user.id} in ONBOARDING mode")
                reply = await self.onboarding_handler.handle(user, state_record, message_text)
            elif state_record.state in [ConversationStatus.WAITING_CONFIRM, ConversationStatus.PENDING_AUTO_CONFIRM]:
                self.logger.info(f"User {user.id} in CONFIRMATION mode")
                reply = await self.confirmation_handler.handle(user, state_record, message_text)
            elif state_record.state == ConversationStatus.SETTINGS:
                self.logger.info(f"User {user.id} in SETTINGS mode")
                reply = await self.settings_handler.handle(user, state_record, message_text)
            elif state_record.state == ConversationStatus.DATA_MANAGEMENT:
                self.logger.info(f"User {user.id} in DATA_MANAGEMENT mode")
                reply = await self.data_management_handler.handle(
                    user, state_record, message_text, media_url, media_type
                )
            elif state_record.state == ConversationStatus.BILLING:
                self.logger.info(f"User {user.id} in BILLING mode")
                reply = await self.billing_handler.handle(user, state_record, message_text)
            elif state_record.state == ConversationStatus.EMPLOYEE_MANAGEMENT:
                self.logger.info(f"User {user.id} in EMPLOYEE_MANAGEMENT mode")
                reply = await self.employee_handler.handle(user, state_record, message_text)
            else:
                reply = await self.idle_handler.handle(user, state_record, message_text)
                # Capture metadata from idle handler if available
                if hasattr(self.idle_handler, "get_last_metadata"):
                    self._current_metadata = self.idle_handler.get_last_metadata()

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
        effective_channel = state_record.active_channel or channel
        
        if effective_channel == MessageType.SMS and user.phone_number:
            try:
                from src.services.sms_factory import get_sms_service
                await get_sms_service().send_sms(user.phone_number, reply)
            except Exception as e:
                self.logger.error(f"Failed to send SMS reply to {user.id}: {e}")

        return reply
