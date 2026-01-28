from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.services.template_service import TemplateService
from src.services.invitation import InvitationService
from src.services.chat.handlers.base import ChatHandler
import logging

class OnboardingHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        template_service: TemplateService,
        invitation_service: InvitationService
    ):
        self.session = session
        self.template_service = template_service
        self.invitation_service = invitation_service
        self.logger = logging.getLogger(__name__)

    async def handle(self, user: User, state_record: ConversationState, message_text: str) -> str:
        lower_text = message_text.lower().strip()

        # State 0: Initial choice (1 or 2)
        if not state_record.draft_data:
            if lower_text in ["1", "create", "new"]:
                # user already has a default business created by auth_service
                # so we just confirm and move to idle
                state_record.state = ConversationStatus.IDLE
                return self.template_service.render("onboarding_create_success")
            elif lower_text in ["2", "join", "existing"]:
                state_record.draft_data = {"step": "joining"}
                return self.template_service.render("onboarding_join_prompt")
            else:
                return self.template_service.render("onboarding_invalid_choice")

        # State 1: Joining (processing invitation/code)
        draft = state_record.draft_data
        if draft.get("step") == "joining":
            success, msg, _ = await self.invitation_service.process_join(user.phone_number or user.email or "", code=message_text)
            if success:
                state_record.state = ConversationStatus.IDLE
                state_record.draft_data = None
                return msg
            else:
                # If failed, maybe they want to go back?
                if lower_text in ["back", "1", "create"]:
                    state_record.state = ConversationStatus.IDLE
                    state_record.draft_data = None
                    return self.template_service.render("onboarding_create_success")
                return f"{msg}\n\nType '1' to just create your own business instead, or try another code."

        return self.template_service.render("onboarding_invalid_choice")
