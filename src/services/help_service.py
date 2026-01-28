import os
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.models import Message, MessageRole, MessageType
from src.config import channels_config
from src.llm_client import LLMParser
import logging

class HelpService:
    def __init__(self, db_session: AsyncSession, llm_client: LLMParser):
        self.db_session = db_session
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        self._manual_cache: Optional[str] = None

    def _load_manual(self) -> str:
        """
        Load the manual content from assets/manual.md.
        """
        if self._manual_cache:
            return self._manual_cache
            
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manual_path = os.path.join(current_dir, "assets", "manual.md")
        
        if not os.path.exists(manual_path):
            self.logger.warning(f"Manual file not found at {manual_path}")
            return "No manual available."
            
        try:
            with open(manual_path, "r") as f:
                self._manual_cache = f.read()
            return self._manual_cache
        except Exception as e:
            self.logger.error(f"Error loading manual: {e}")
            return "Error loading manual."

    async def get_chat_history(self, business_id: int, user_id: int, limit: int = 5) -> List[Message]:
        """
        Fetch the last X messages for a given user and business.
        Order by created_at DESC, take limit, then reverse to chronological order.
        """
        stmt = (
            select(Message)
            .where(Message.business_id == business_id)
            .where(Message.user_id == user_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        
        result = await self.db_session.execute(stmt)
        messages = result.scalars().all()
        # Convert to list and reverse to get chronological order
        return list(reversed(list(messages)))

    def construct_help_prompt(self, history: List[Message], channel: MessageType | str) -> List[dict]:
        """
        Construct a list of messages for the LLM including system instructions,
        manual content, and conversation history.
        """
        manual_text = self._load_manual()
        
        # Get channel restrictions from config
        channel_name = channel.value if isinstance(channel, MessageType) else channel
        channel_settings = channels_config.channels.get(channel_name)
        restrictions = "Be helpful and concise."
        if channel_settings:
            restrictions = f"Max length: {channel_settings.max_length} characters. Style: {channel_settings.style}."
        
        system_content = (
            "You are a helpful CRM assistant.\n"
            "Use the following manual to answer the user's question.\n"
            f"Channel restrictions: {restrictions}\n\n"
            "**MANUAL CONTENT**:\n"
            f"{manual_text}"
        )
        
        messages = [{"role": "system", "content": system_content}]
        
        for msg in history:
            role = "USER" if msg.role == MessageRole.USER else "ASSISTANT"
            content = msg.body
            
            # If assistant message has error or tool call context in log_metadata, include it
            if msg.role == MessageRole.ASSISTANT and msg.log_metadata:
                error = msg.log_metadata.get("error")
                tool_call = msg.log_metadata.get("tool_call")
                
                if tool_call:
                    tool_name = tool_call.get("name") if isinstance(tool_call, dict) else str(tool_call)
                    content += f"\n[System Note: Assistant attempted tool: {tool_name}]"
                
                if error:
                    content += f"\n[System Note: The previous attempt resulted in an error: {error}]"
            
            messages.append({"role": role, "content": content})
            
        return messages

    async def generate_help_response(self, user_query: str, business_id: int, user_id: int, channel: MessageType = MessageType.WHATSAPP) -> str:
        """
        Main entry point for generating a help response:
        1. Fetch history
        2. Construct prompt
        3. Call LLM
        """
        history = await self.get_chat_history(business_id, user_id)
        
        # Ensure the current user_query is the last message if not already in history
        # (Compare by body to avoid redundancy)
        if not history or history[-1].body != user_query:
            # We don't want to mutate the history from DB, so we'll just handle it in prompt construction
            pass

        prompt_messages = self.construct_help_prompt(history, channel)
        
        # If the last message in prompt_messages is not the user_query, append it
        if prompt_messages[-1]["role"] != "USER" or prompt_messages[-1]["content"] != user_query:
             prompt_messages.append({"role": "USER", "content": user_query})

        return await self.llm_client.chat_completion(prompt_messages)
