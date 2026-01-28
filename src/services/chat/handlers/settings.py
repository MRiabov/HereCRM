from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.repositories import ServiceRepository
from src.llm_client import LLMParser
from src.services.template_service import TemplateService
from src.tool_executor import ToolExecutor
from src.services.chat_utils import format_service_list
from src.uimodels import ExitSettingsTool, ListServicesTool
from src.services.chat.handlers.base import ChatHandler
import logging

class SettingsHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        parser: LLMParser,
        template_service: TemplateService
    ):
        self.session = session
        self.parser = parser
        self.template_service = template_service
        self.logger = logging.getLogger(__name__)

    async def handle(self, user: User, state_record: ConversationState, message_text: str) -> str:
        service_repo = ServiceRepository(self.session)

        # Fetch Service Catalog for context AND listing
        services = await service_repo.get_all_for_business(user.business_id)

        # Simple format for LLM context (names and prices)
        service_catalog_str = "\n".join(
            [f"- {s.name} ({s.default_price})" for s in services]
        ) if services else "No services yet."

        # Parse with specialized settings parser
        tool_call = await self.parser.parse_settings(message_text, service_context=service_catalog_str)

        # Note: Metadata tracking for tool calls needs to be handled by the caller or passed in.
        # For now, we assume the Orchestrator handles metadata persistence if it captures the tool call object.
        # But here we execute immediately.

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
