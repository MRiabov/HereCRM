from abc import ABC, abstractmethod
from src.models import User, ConversationState

class ChatHandler(ABC):
    @abstractmethod
    async def handle(
        self,
        user: User,
        state_record: ConversationState,
        message_text: str
    ) -> str:
        pass
