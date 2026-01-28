from typing import cast, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, ConversationState, Request
from src.repositories import JobRepository, RequestRepository, UserRepository
from src.services.template_service import TemplateService

class UndoHandler:
    def __init__(self, session: AsyncSession, template_service: TemplateService):
        self.session = session
        self.template_service = template_service

    async def handle_undo(self, user: User, state_record: ConversationState) -> str:
        metadata = state_record.last_action_metadata
        if not metadata:
            return self.template_service.render("error_undo_nothing")

        action = metadata.get("action")
        entity_type = cast(str, metadata.get("entity", ""))
        entity_id = metadata.get("id")

        if action == "create":
            # Compensating action: delete
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
                repo = JobRepository(self.session)
                job = await repo.get_by_id(entity_id, user.business_id)
                if job:
                    job.status = cast(str, metadata.get("old_status", "PENDING"))
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_job_reverted")
            elif entity_type == "request" and isinstance(entity_id, int):
                repo = RequestRepository(self.session)
                req = await repo.get_by_id(entity_id, user.business_id)
                if req:
                    req.status = cast(str, metadata.get("old_status", "PENDING"))
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_request_reverted")

        elif action == "promote":
            # Compensating action: Re-create Request, Delete Job
            if entity_type == "job" and isinstance(entity_id, int):
                job_repo = JobRepository(self.session)
                job = await job_repo.get_by_id(entity_id, user.business_id)
                if job:
                    # Re-create the request
                    old_description = metadata.get("old_request_description")
                    if old_description:
                        req = Request(
                            business_id=user.business_id,
                            description=cast(str, old_description),
                            status="PENDING",
                        )
                        self.session.add(req)

                    # Delete the job
                    await self.session.delete(job)
                    state_record.last_action_metadata = None
                    return self.template_service.render("undo_promotion_reverted")

        elif action == "update_settings":
            repo = UserRepository(self.session)
            old_value = metadata.get("old_value")
            key = cast(str, metadata.get("setting_key", ""))
            user_id = cast(Optional[int], metadata.get("user_id"))

            if user_id and key:
                # Revert to old value
                await repo.update_preferences(user_id, key, old_value)
                state_record.last_action_metadata = None
                return self.template_service.render("undo_setting_reverted", key=key)

        return self.template_service.render("error_undo_failed")

    async def handle_edit_last(self, user: User, state_record: ConversationState) -> str:
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

        details = ", ".join(details_list) if details_list else "no details"
        return self.template_service.render(
            "edit_last_prompt",
            category=metadata.get("category", entity_type).capitalize(),
            details=details,
        )
