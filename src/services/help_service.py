import os
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from src.models import Message, MessageRole
from src.config import channels_config
from src.llm_client import parser

class HelpService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._manual_cache: Optional[str] = None
        self._channels_config = channels_config

    def _load_manual(self) -> str:
        if self._manual_cache:
            return self._manual_cache
        
        # Get the directory of the current file and go up one level to src/
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manual_path = os.path.join(current_dir, "assets", "manual.md")
        
        if not os.path.exists(manual_path):
            return "Product manual is currently unavailable."
            
        with open(manual_path, "r") as f:
            self._manual_cache = f.read()
            
        return self._manual_cache

    def _get_channel_settings(self, channel: str):
        return self._channels_config.channels.get(channel)

    async def get_chat_history(self, business_id: int, phone_number: str, limit: int = 5) -> List[Message]:
        """
        Retrieves the last N messages for a given user/business to provide context.
        """
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.business_id == business_id,
                    or_(
                        Message.from_number == phone_number,
                        Message.to_number == phone_number
                    )
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        return messages[::-1]  # Return in chronological order

    def construct_help_prompt(self, history: List[Message], channel: str) -> List[dict]:
        """
        Combines the product manual and chat history into a structured prompt for the LLM.
        """
        manual_text = self._load_manual()
        settings = self._get_channel_settings(channel)
        
        style_guide = ""
        if settings:
            style_guide = f"Response style: {settings.style}. Max length: {settings.max_length} characters."

        system_prompt = (
            "You are a helpful CRM assistant for HereCRM.\n"
            "Use the following product manual to answer the user's question or provide guidance.\n"
            f"{style_guide}\n\n"
            "**PRODUCT MANUAL**:\n"
            f"{manual_text}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in history:
            role = "user" if msg.role == MessageRole.USER else "assistant"
            content = msg.body
            
            # Include metadata context if available (e.g., tool call info or errors)
            if msg.log_metadata:
                content += f"\n[Technical Context: {msg.log_metadata}]"
                
            messages.append({"role": role, "content": content})
            
        return messages

    async def generate_help_response(
        self, 
        business_id: int, 
        phone_number: str, 
        channel: str = "whatsapp"
    ) -> str:
        """
        Orchestrates the help response generation: fetches history, builds prompt, and calls LLM.
        """
        history = await self.get_chat_history(business_id, phone_number)
        messages = self.construct_help_prompt(history, channel)
        
        response_text = await parser.chat_completion(messages)
        return response_text
