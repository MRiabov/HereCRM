import google.generativeai as genai
from typing import Union, Optional

from src.config import settings
from src.uimodels import (
    AddJobTool,
    ScheduleJobTool,
    StoreRequestTool,
    SearchTool,
    UpdateSettingsTool,
    ConvertRequestTool,
)


class LLMParser:
    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.tools = [
            AddJobTool,
            ScheduleJobTool,
            StoreRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
        ]
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model, tools=self.tools
        )

    async def parse(
        self, text: str
    ) -> Optional[
        Union[
            AddJobTool,
            ScheduleJobTool,
            StoreRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
        ]
    ]:
        """
        Parses user text into one of the known tool models.
        Returns None if no clear tool is identified or if keyword like "Undo" is requested.
        """
        # 1. Keyword pre-filtering for Undo/Cancel
        lower_text = text.lower().strip()
        if lower_text in ["undo", "cancel"]:
            return None

        # 2. Use the model to generate a tool call
        chat = self.model.start_chat()

        try:
            # Use async call as per review feedback
            response = await chat.send_message_async(text)
        except Exception:
            # Log error if possible, but for now return None on model/network failure
            return None

        # 3. Robust candidate and part access
        if not response.candidates or not response.candidates[0].content.parts:
            return None

        part = response.candidates[0].content.parts[0]

        if fn := part.function_call:
            # Map function name to Pydantic model
            model_map = {m.__name__: m for m in self.tools}
            model_cls = model_map.get(fn.name)

            if model_cls:
                # Convert the function call arguments (dict-like) to the Pydantic model
                return model_cls(**fn.args)

        return None


# Singleton instance
parser = LLMParser()
