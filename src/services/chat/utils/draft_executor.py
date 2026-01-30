import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, ConversationStatus
from src.services.template_service import TemplateService
from src.tool_executor import ToolExecutor
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
    CreateQuoteTool,
    RequestUpgradeTool,
    GetBillingStatusTool,
    LocateEmployeeTool,
    CheckETATool,
    SendStatusTool,
    ListServicesTool,
)
from src.tools.invoice_tools import SendInvoiceTool
from src.tools.employee_management import InviteUserTool, ExitEmployeeManagementTool


class DraftExecutor:
    def __init__(self, session: AsyncSession, template_service: TemplateService):
        self.session = session
        self.template_service = template_service
        self.logger = logging.getLogger(__name__)

    async def execute_draft(self, user: User, state_record: ConversationState) -> str:
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
            "CreateQuoteTool": CreateQuoteTool,
            "SendStatusTool": SendStatusTool,
            "LocateEmployeeTool": LocateEmployeeTool,
            "CheckETATool": CheckETATool,
            "InviteUserTool": InviteUserTool,
            "ExitEmployeeManagementTool": ExitEmployeeManagementTool,
            "ListServicesTool": ListServicesTool,
        }

        tool_cls = model_map.get(tool_name)
        if not tool_cls:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return self.template_service.render("error_unknown_tool")

        tool_call = tool_cls(**arguments)

        # Execute
        executor = ToolExecutor(
            self.session,
            user.business_id,
            user.id,
            user.phone_number or "",
            self.template_service,
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
