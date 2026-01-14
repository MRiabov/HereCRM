from typing import Any, cast
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import ConversationState, ConversationStatus, User, Request
from src.repositories import (
    ConversationStateRepository,
    UserRepository,
    BusinessRepository,
)
from src.llm_client import LLMParser
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService
from src.uimodels import AddJobTool


class WhatsappService:
    def __init__(
        self,
        session: AsyncSession,
        parser: LLMParser,
        template_service: TemplateService,
    ):
        self.session = session
        self.parser = parser
        self.template_service = template_service
        self.state_repo = ConversationStateRepository(session)
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)

    async def handle_message(self, user_phone: str, message_text: str) -> str:
        # 1. Identify User/Business (Placeholder for WP04 logic)
        user = await self.user_repo.get_by_phone(user_phone)
        if not user:
            return self.template_service.render("error_user_required")

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

        # Handle Edit Last
        if lower_text == "edit last":
            return await self._handle_edit_last(user, state_record)

        # Parse with LLM
        from datetime import datetime, timezone

        system_time = datetime.now(timezone.utc).isoformat()
        tool_call = await self.parser.parse(text, system_time=system_time)

        if tool_call:
            # Handle HelpTool separately (skip confirmation)
            from src.uimodels import HelpTool

            if isinstance(tool_call, HelpTool):
                return self._generate_help_message()

            # Store draft and transition to WAITING_CONFIRM
            state_record.draft_data = {
                "tool_name": tool_call.__class__.__name__,
                "arguments": tool_call.dict(),
            }
            state_record.state = ConversationStatus.WAITING_CONFIRM

            # Simple summary for confirmation
            summary = self._generate_summary(tool_call)
            return self.template_service.render("confirm_prompt", summary=summary)

        # If no tool call, maybe it's just a greeting or unclear
        return self.template_service.render("error_unclear_input")

    async def _handle_waiting_confirm(
        self, user: User, state_record: ConversationState, text: str
    ) -> str:
        lower_text = text.lower().strip()

        if lower_text in ["yes", "y", "confirm"]:
            return await self._execute_draft(user, state_record)

        elif lower_text in ["no", "n", "cancel"]:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return self.template_service.render("action_cancelled")

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
            return self.template_service.render("error_no_draft")

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
            HelpTool,
        )

        model_map = {
            "AddJobTool": AddJobTool,
            "ScheduleJobTool": ScheduleJobTool,
            "StoreRequestTool": StoreRequestTool,
            "SearchTool": SearchTool,
            "UpdateSettingsTool": UpdateSettingsTool,
            "ConvertRequestTool": ConvertRequestTool,
            "HelpTool": HelpTool,
        }

        tool_cls = model_map.get(tool_name)
        if not tool_cls:
            state_record.state = ConversationStatus.IDLE
            state_record.draft_data = None
            return self.template_service.render("error_unknown_tool")

        tool_call = tool_cls(**arguments)

        # Execute
        executor = ToolExecutor(
            self.session, user.business_id, user.phone_number, self.template_service
        )
        result, metadata = await executor.execute(tool_call)

        # Track for Undo
        if metadata:
            state_record.last_action_metadata = metadata

        # Reset state
        state_record.state = ConversationStatus.IDLE
        state_record.draft_data = None

        return f"{result}"

    async def _handle_undo(self, user: User, state_record: ConversationState) -> str:
        metadata = state_record.last_action_metadata
        if not metadata:
            return self.template_service.render("error_undo_nothing")

        action = metadata.get("action")
        entity_type = cast(str, metadata.get("entity", ""))
        entity_id = metadata.get("id")

        if action == "create":
            # Compensating action: delete
            from src.repositories import JobRepository, RequestRepository

            repo_map = {"job": JobRepository, "request": RequestRepository}
            repo_cls = repo_map.get(entity_type)
            if repo_cls and isinstance(entity_id, int):
                repo = repo_cls(self.session)
                entity = await repo.get_by_id(entity_id, user.business_id)
                if entity:
                    await self.session.delete(entity)
                    state_record.last_action_metadata = None
                    return self.template_service.render(
                        "undo_deleted", entity_type=entity_type
                    )

        elif action == "update":
            # Compensating action: revert status (simplified)
            if entity_type == "job" and isinstance(entity_id, int):
                from src.repositories import JobRepository

                repo = JobRepository(self.session)
                job = await repo.get_by_id(entity_id, user.business_id)
                if job:
                    job.status = cast(str, metadata.get("old_status", "pending"))
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_job_reverted")
            elif entity_type == "request" and isinstance(entity_id, int):
                from src.repositories import RequestRepository

                repo = RequestRepository(self.session)
                req = await repo.get_by_id(entity_id, user.business_id)
                if req:
                    req.status = cast(str, metadata.get("old_status", "pending"))
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_request_reverted")

        elif action == "promote":
            # Compensating action: Re-create Request, Delete Job
            if entity_type == "job" and isinstance(entity_id, int):
                from src.repositories import JobRepository, RequestRepository

                job_repo = JobRepository(self.session)
                job = await job_repo.get_by_id(entity_id, user.business_id)
                if job:
                    # Re-create the request
                    old_content = metadata.get("old_request_content")
                    if old_content:
                        req = Request(
                            business_id=user.business_id,
                            content=cast(str, old_content),
                            status="pending",
                        )
                        self.session.add(req)

                    # Delete the job
                    await self.session.delete(job)
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_promotion_reverted")

        elif action == "update_settings":
            from src.repositories import UserRepository

            repo = UserRepository(self.session)
            old_value = metadata.get("old_value")
            key = cast(str, metadata.get("setting_key", ""))
            phone = cast(str, metadata.get("phone", ""))

            if key and phone:
                # Revert to old value
                await repo.update_preferences(phone, key, old_value)
                state_record.last_action_metadata = None
                return self.template_service.render("undo_setting_reverted", key=key)

        return self.template_service.render("error_undo_failed")

    async def _handle_edit_last(
        self, user: User, state_record: ConversationState
    ) -> str:
        metadata = state_record.last_action_metadata
        if not metadata:
            return self.template_service.render("error_edit_nothing")

        entity_type = cast(str, metadata.get("entity", "item"))
        # Construct summary from metadata
        details_list = []
        if name := metadata.get("customer_name"):
            details_list.append(name)
        if price := metadata.get("price"):
            # Format price for display
            if isinstance(price, (int, float)):
                price_str = f"{int(price)}$" if price == int(price) else f"{price:.2f}$"
            else:
                price_str = str(price)
            details_list.append(price_str)
        if location := metadata.get("location"):
            details_list.append(location)
        if description := metadata.get("description"):
            details_list.append(description)
        if content := metadata.get("content"):
            details_list.append(content[:50])

        details = ", ".join(details_list) if details_list else "no details"
        return self.template_service.render(
            "edit_last_prompt",
            category=metadata.get("category", entity_type).capitalize(),
            details=details,
        )

    def _generate_summary(self, tool_call: Any) -> str:
        # Map tool class names to friendly display names
        friendly_names = {
            "AddJobTool": "Add Job",
            "ScheduleJobTool": "Schedule",
            "StoreRequestTool": "Request",
            "SearchTool": "Search",
            "UpdateSettingsTool": "Settings",
            "ConvertRequestTool": "Convert",
            "HelpTool": "Help",
        }
        model_name = tool_call.__class__.__name__
        name = friendly_names.get(model_name, model_name.replace("Tool", ""))

        # Use category if available (e.g. for AddJobTool)
        if hasattr(tool_call, "category") and tool_call.category:
            name = f"Add {tool_call.category.capitalize()}"

        if isinstance(tool_call, AddJobTool):
            price_val = "Not supplied"
            if tool_call.price is not None:
                if tool_call.price == int(tool_call.price):
                    price_val = f"{int(tool_call.price)}$"
                else:
                    price_val = f"{tool_call.price:.2f}$"

            return self.template_service.render(
                "job_summary",
                category=tool_call.category.capitalize()
                if tool_call.category
                else "Job",
                name=tool_call.customer_name or "Not supplied",
                address=tool_call.location or "Not supplied",
                price=price_val,
                description=tool_call.description or "Not supplied",
            )

        if hasattr(tool_call, "description") and tool_call.description:
            return f"{name}: {tool_call.description}"
        elif hasattr(tool_call, "customer_query") and tool_call.customer_query:
            return f"{name}: {tool_call.customer_query}"
        elif hasattr(tool_call, "customer_name") and tool_call.customer_name:
            return f"{name}: {tool_call.customer_name}"
        elif hasattr(tool_call, "content"):
            return f"{name}: {tool_call.content[:50]}"
        elif hasattr(tool_call, "query"):
            return f"{name}: {tool_call.query}"
        return f"{name} operation"

    def _generate_help_message(self) -> str:
        return self.template_service.render("help_message")
