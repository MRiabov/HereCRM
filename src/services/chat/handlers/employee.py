from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.llm_client import LLMParser
from src.services.template_service import TemplateService
from src.services.invitation import InvitationService
from src.tools.employee_management import ExitEmployeeManagementTool, InviteUserTool
from src.services.chat.handlers.base import ChatHandler
import logging

class EmployeeHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        parser: LLMParser,
        template_service: TemplateService,
        invitation_service: InvitationService
    ):
        self.session = session
        self.parser = parser
        self.template_service = template_service
        self.invitation_service = invitation_service
        self.logger = logging.getLogger(__name__)

    async def handle(self, user: User, state_record: ConversationState, message_text: str) -> str:
        # Check manual exit just in case parser fails or as fast path
        if message_text.lower().strip() in ["exit", "quit", "back", "done"]:
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")

        tool_call = await self.parser.parse_employee_management(message_text)

        if not tool_call:
            return "I didn't understand. You can 'Invite +123456789'. Type 'exit' to quit."

        if isinstance(tool_call, ExitEmployeeManagementTool):
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")

        if isinstance(tool_call, InviteUserTool):
            # Execute Invite logic
            try:
                await self.invitation_service.create_invitation(
                    user.business_id, user.id, tool_call.identifier
                )
                return f"Invitation sent to {tool_call.identifier}."
            except Exception as e:
                self.logger.error(f"Invite failed: {e}")
                return f"Failed to send invitation: {e}"

        return "Tool not implemented yet."
