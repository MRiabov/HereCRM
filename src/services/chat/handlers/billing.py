from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.services.template_service import TemplateService
from src.tool_executor import ToolExecutor
from src.uimodels import GetBillingStatusTool, RequestUpgradeTool
from src.services.chat.handlers.base import ChatHandler
import logging
import re


class BillingHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        template_service: TemplateService,
        summary_generator,
    ):
        self.session = session
        self.template_service = template_service
        self.summary_generator = summary_generator
        self.logger = logging.getLogger(__name__)

    async def handle(
        self, user: User, state_record: ConversationState, message_text: str
    ) -> str:
        lower_text = message_text.lower().strip()

        if lower_text in ["exit", "back", "cancel", "return"]:
            state_record.state = ConversationStatus.IDLE
            return self.template_service.render("welcome_back")

        # Check if user says "status" explicitly
        if lower_text in ["status", "check", "info"]:
            executor = ToolExecutor(
                self.session,
                user.business_id,
                user.id,
                user.phone_number or "",
                self.template_service,
            )
            res, _ = await executor.execute(GetBillingStatusTool())
            return res

        # Simple regex/logic for now as per "Conversational Tools" requirement
        if "seat" in lower_text:
            # Assume 1 seat unless number specified
            qty = 1
            numbers = re.findall(r"\d+", lower_text)
            if numbers:
                qty = int(numbers[0])

            tool = RequestUpgradeTool(item_type="seat", quantity=qty)
            state_record.draft_data = {
                "tool_name": "RequestUpgradeTool",
                "arguments": tool.dict(),
            }
            # Go to confirmation
            state_record.state = ConversationStatus.WAITING_CONFIRM
            summary = await self.summary_generator.generate_summary(tool, user)
            return self.template_service.render("confirm_prompt", summary=summary)

        # Allow addons
        if "addon" in lower_text or "campaign" in lower_text:
            addon_id = (
                "campaign_manager" if "campaign" in lower_text else "unknown_addon"
            )
            tool = RequestUpgradeTool(item_type="addon", item_id=addon_id, quantity=1)

            state_record.draft_data = {
                "tool_name": "RequestUpgradeTool",
                "arguments": tool.dict(),
            }
            state_record.state = ConversationStatus.WAITING_CONFIRM
            summary = await self.summary_generator.generate_summary(tool, user)
            return self.template_service.render("confirm_prompt", summary=summary)

        return "Unknown command. Try 'status', 'buy seat', or 'back'."
