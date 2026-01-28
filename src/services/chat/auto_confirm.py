import asyncio
import logging
from datetime import datetime, timezone
from src.database import AsyncSessionLocal
from src.repositories import ConversationStateRepository, UserRepository
from src.models import Message, MessageRole, ConversationStatus
from src.services.chat.utils.draft_executor import DraftExecutor
from src.services.template_service import TemplateService

logger = logging.getLogger(__name__)

class AutoConfirmService:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    def schedule_auto_confirm(self, user_id: int, timeout: int):
        asyncio.create_task(self._auto_confirm_task(user_id, timeout))

    async def _auto_confirm_task(self, user_id: int, timeout: int):
        try:
            await asyncio.sleep(timeout)

            async with self.session_factory() as session:
                state_repo = ConversationStateRepository(session)
                user_repo = UserRepository(session)

                state_record = await state_repo.get_by_user_id(user_id)
                user = await user_repo.get_by_id(user_id)

                if not state_record or not user:
                    return

                if state_record.state == ConversationStatus.PENDING_AUTO_CONFIRM:
                    now = datetime.now(timezone.utc)
                    if state_record.pending_action_timestamp and now >= state_record.pending_action_timestamp:

                        template_service = TemplateService()
                        draft_executor = DraftExecutor(session, template_service)

                        result = await draft_executor.execute_draft(user, state_record)

                        active_channel = state_record.active_channel or "whatsapp"
                        recipient = user.phone_number if active_channel == "sms" else (user.email or user.phone_number)

                        if active_channel == "sms" and user.phone_number:
                            from src.services.sms_factory import get_sms_service
                            svc = get_sms_service()
                            await svc.send_sms(user.phone_number, result)
                        elif active_channel == "email" and (user.email or user.phone_number):
                             from src.services.postmark_service import PostmarkService
                             to_email = user.email or user.phone_number or ""
                             if to_email:
                                 await PostmarkService().send_email(
                                     to_email=to_email,
                                     subject="Action Confirmed",
                                     body=result
                                 )

                        sys_msg = Message(
                            business_id=user.business_id,
                            user_id=user.id,
                            from_number="system",
                            to_number=recipient or "unknown",
                            body=result,
                            role=MessageRole.ASSISTANT,
                            channel_type=active_channel
                        )
                        session.add(sys_msg)
                        await session.commit()

        except Exception as e:
            logger.error(f"Auto-confirm task failed for user {user_id}: {e}")
