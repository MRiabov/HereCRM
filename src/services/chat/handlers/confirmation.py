from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.services.template_service import TemplateService
from src.services.chat.handlers.base import ChatHandler
from src.services.chat.utils.draft_executor import DraftExecutor
import logging


class ConfirmationHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        template_service: TemplateService,
        draft_executor: DraftExecutor,
        idle_handler,  # We need idle handler for fallback
    ):
        self.session = session
        self.template_service = template_service
        self.draft_executor = draft_executor
        self.idle_handler = idle_handler
        self.logger = logging.getLogger(__name__)

    async def handle(
        self, user: User, state_record: ConversationState, message_text: str
    ) -> str:
        if state_record.state == ConversationStatus.WAITING_CONFIRM:
            return await self._handle_waiting_confirm(user, state_record, message_text)
        elif state_record.state == ConversationStatus.PENDING_AUTO_CONFIRM:
            return await self._handle_pending_auto_confirm(
                user, state_record, message_text
            )
        else:
            return "Error: Invalid state for ConfirmationHandler"

    async def _handle_waiting_confirm(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        if lower_text in ["yes", "y", "confirm"]:
            return await self.draft_executor.execute_draft(user, state_record)

        elif lower_text in ["no", "n", "cancel"]:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return self.template_service.render("action_cancelled")

        else:
            # Handle edge case: new command while waiting for confirm
            confirm_by_default = user.preferences.get("confirm_by_default", False)
            if confirm_by_default:
                # Auto-execute previous draft, then process new message
                await self.draft_executor.execute_draft(user, state_record)
                return await self.idle_handler.handle(user, state_record, text)
            else:
                # Discard draft, notify, and process new message
                state_record.state = ConversationStatus.IDLE
                state_record.draft_data = None
                initial_msg = "Previous draft discarded. "
                new_msg = await self.idle_handler.handle(user, state_record, text)
                return f"{initial_msg}{new_msg}"

    async def _handle_pending_auto_confirm(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        """
        User interrupted the auto-confirm countdown.
        """
        lower_text = text.lower().strip()

        # Explicit confirmation
        if lower_text in ["yes", "y", "confirm", "ok", "okay"]:
            return await self.draft_executor.execute_draft(user, state_record)

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
        response = await self.idle_handler.handle(user, state_record, text)
        return prefix + response
