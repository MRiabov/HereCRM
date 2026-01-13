from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import ConversationState, ConversationStatus, User, Business
from src.repositories import (
    ConversationStateRepository,
    UserRepository,
    BusinessRepository,
)
from src.llm_client import LLMParser
from src.tool_executor import ToolExecutor


class WhatsappService:
    def __init__(self, session: AsyncSession, parser: LLMParser):
        self.session = session
        self.parser = parser
        self.state_repo = ConversationStateRepository(session)
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)

    async def handle_message(self, user_phone: str, message_text: str) -> str:
        # 1. Identify User/Business (Placeholder for WP04 logic)
        user = await self.user_repo.get_by_phone(user_phone)
        if not user:
            # For now, let's auto-onboard a default business if user doesn't exist
            # This will be replaced by robust logic in WP04
            business = Business(name="New Business")
            self.session.add(business)
            await self.session.flush()
            user = User(phone_number=user_phone, business_id=business.id, role="owner")
            self.user_repo.add(user)
            await self.session.flush()

        # 2. Fetch Conversation State
        state_record = await self.state_repo.get_by_phone(user_phone)
        if not state_record:
            state_record = ConversationState(
                phone_number=user_phone, state=ConversationStatus.IDLE
            )
            self.state_repo.add(state_record)
            await self.session.flush()

        # 3. State Machine Logic
        if state_record.state == ConversationStatus.WAITING_CONFIRM:
            return await self._handle_waiting_confirm(user, state_record, message_text)
        else:
            return await self._handle_idle(user, state_record, message_text)

    async def _handle_idle(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        # Handle Undo
        if lower_text == "undo":
            return await self._handle_undo(user, state_record)

        # Parse with LLM
        tool_call = await self.parser.parse(text)

        if tool_call:
            # Store draft and transition to WAITING_CONFIRM
            # tool_call is a Pydantic model, need to serialize it
            state_record.draft_data = {
                "tool_name": tool_call.__class__.__name__,
                "arguments": tool_call.model_dump(),
            }
            state_record.state = ConversationStatus.WAITING_CONFIRM

            # Simple summary for confirmation
            summary = self._generate_summary(tool_call)
            return (
                f"Please confirm: {summary}\n(Reply 'Yes' to confirm, 'No' to cancel)"
            )

        # If no tool call, maybe it's just a greeting or unclear
        return "I'm not sure how to help with that. Try saying 'Add job: ...' or 'Show all jobs'."

    async def _handle_waiting_confirm(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        if lower_text in ["yes", "y", "confirm"]:
            return await self._execute_draft(user, state_record)

        elif lower_text in ["no", "n", "cancel"]:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return "Action cancelled."

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
            return "No draft to execute."

        # Reconstruct tool call from draft_data
        draft = state_record.draft_data
        tool_name = draft["tool_name"]
        arguments = draft["arguments"]

        # Import tools for reconstruction (could be improved)
        from src.uimodels import (
            AddJobTool,
            ScheduleJobTool,
            StoreRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
        )

        model_map = {
            "AddJobTool": AddJobTool,
            "ScheduleJobTool": ScheduleJobTool,
            "StoreRequestTool": StoreRequestTool,
            "SearchTool": SearchTool,
            "UpdateSettingsTool": UpdateSettingsTool,
            "ConvertRequestTool": ConvertRequestTool,
        }

        tool_cls = model_map.get(tool_name)
        if not tool_cls:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return "Error: Unknown tool in draft."

        tool_call = tool_cls(**arguments)

        # Execute
        executor = ToolExecutor(self.session, user.business_id)
        result, metadata = await executor.execute(tool_call)

        # Track for Undo
        if metadata:
            state_record.last_action_metadata = metadata

        # Reset state
        state_record.state = ConversationStatus.IDLE
        state_record.draft_data = None

        return f"{result}\n(Reply 'undo' to revert)"

    async def _handle_undo(self, user: User, state_record: ConversationState) -> str:
        metadata = state_record.last_action_metadata
        if not metadata:
            return "Nothing to undo."

        action = metadata.get("action")
        entity_type = metadata.get("entity")
        entity_id = metadata.get("id")

        if action == "create":
            # Compensating action: delete
            from src.repositories import JobRepository, RequestRepository

            repo_map = {"job": JobRepository, "request": RequestRepository}
            repo_cls = repo_map.get(entity_type)
            if repo_cls:
                repo = repo_cls(self.session)
                entity = await repo.get_by_id(entity_id, user.business_id)
                if entity:
                    await self.session.delete(entity)
                    state_record.last_action_metadata = None
                    return f"Undone: Deleted {entity_type}."

        elif action == "update":
            # Compensating action: revert status (simplified)
            if entity_type == "job":
                from src.repositories import JobRepository

                repo = JobRepository(self.session)
                job = await repo.get_by_id(entity_id, user.business_id)
                if job:
                    job.status = metadata.get("old_status", "pending")
                    state_record.last_action_metadata = None
                    return "Undone: Job status reverted."

        return "Could not perform undo for this action."

    def _generate_summary(self, tool_call: Any) -> str:
        # Basic summary generator
        name = tool_call.__class__.__name__.replace("Tool", "")
        if hasattr(tool_call, "description"):
            return f"{name}: {tool_call.description}"
        elif hasattr(tool_call, "content"):
            return f"{name}: {tool_call.content[:50]}"
        elif hasattr(tool_call, "query"):
            return f"{name}: {tool_call.query}"
        return f"{name} operation"
