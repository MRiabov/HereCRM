from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.llm_client import LLMParser
from src.services.template_service import TemplateService
from src.services.data_management import DataManagementService
from src.uimodels import ExitDataManagementTool, ExportQueryTool
from src.services.chat.handlers.base import ChatHandler
import logging

class DataManagementHandler(ChatHandler):
    def __init__(
        self,
        session: AsyncSession,
        parser: LLMParser,
        template_service: TemplateService,
        data_service: DataManagementService
    ):
        self.session = session
        self.parser = parser
        self.template_service = template_service
        self.data_service = data_service
        self.logger = logging.getLogger(__name__)

    async def handle(
        self,
        user: User,
        state_record: ConversationState,
        message_text: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> str:
        # Handle file upload for import
        if media_url:
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
        tool_call = await self.parser.parse_data_management(message_text)

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
                if export_req.status == ExportStatus.COMPLETED:
                    # In a real app, public_url would be a downloadable link.
                    return f"Export completed! You can download it here: {export_req.public_url}"
                else:
                    return f"Export processing... (Status: {export_req.status})"
            except Exception as e:
                self.logger.exception("Export failed")
                return f"Export failed: {str(e)}"

        return "I didn't understand that command. You can upload a file to import, or say 'Export customers in Dublin' to export data. Type 'exit' to leave."
