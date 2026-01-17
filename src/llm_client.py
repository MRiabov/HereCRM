import logging
import json
import os
from typing import Union, Optional
from openai import AsyncOpenAI
from pydantic import ValidationError

from src.config import settings
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
    AddServiceTool,
    EditServiceTool,
    DeleteServiceTool,
    ListServicesTool,
    ExitSettingsTool,
    SendInvoiceTool,
)
from src.services.template_service import TemplateService


class LLMParser:
    def __init__(self, prompts_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        self.model = settings.openrouter_model

        # Load prompts from external YAML
        if prompts_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompts_path = os.path.join(base_dir, "src", "assets", "prompts.yaml")
        
        # We reuse TemplateService as a generic YAML loader for prompts
        self.prompts_service = TemplateService(yaml_path=prompts_path)

        # Define tools using OpenAI schema
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "AddJobTool",
                    "description": "Add a new job with price or task details.",
                    "parameters": AddJobTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "AddLeadTool",
                    "description": "Add a new lead or customer without a job.",
                    "parameters": AddLeadTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "EditCustomerTool",
                    "description": "Update customer details like phone, address, or notes.",
                    "parameters": EditCustomerTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ScheduleJobTool",
                    "description": "Schedule an existing or new job for a specific time.",
                    "parameters": ScheduleJobTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "AddRequestTool",
                    "description": "Store a general request or note.",
                    "parameters": AddRequestTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "SearchTool",
                    "description": "Search for jobs, customers, or requests.",
                    "parameters": SearchTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "UpdateSettingsTool",
                    "description": "Update user preferences or business settings.",
                    "parameters": UpdateSettingsTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ConvertRequestTool",
                    "description": "Convert a general request or a query into a specific action.",
                    "parameters": ConvertRequestTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "HelpTool",
                    "description": "Get help or information about available commands.",
                    "parameters": HelpTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "GetPipelineTool",
                    "description": "Get a summary of the sales pipeline (funnel counts).",
                    "parameters": GetPipelineTool.schema(),
                },
            },
        ]

        self.tools.append({
            "type": "function",
            "function": {
                "name": "SendInvoiceTool",
                "description": "Send a professional PDF invoice to a customer for their last job.",
                "parameters": SendInvoiceTool.schema(),
            },
        })

        self.settings_tools = [
            {
                "type": "function",
                "function": {
                    "name": "AddServiceTool",
                    "description": "Add a new service to the catalog.",
                    "parameters": AddServiceTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "EditServiceTool",
                    "description": "Edit an existing service.",
                    "parameters": EditServiceTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "DeleteServiceTool",
                    "description": "Delete a service from the catalog.",
                    "parameters": DeleteServiceTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ListServicesTool",
                    "description": "List all available services.",
                    "parameters": ListServicesTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ExitSettingsTool",
                    "description": "Exit the settings mode.",
                    "parameters": ExitSettingsTool.schema(),
                },
            },
        ]

    async def parse_settings(
        self, text: str, service_context: Optional[str] = None
    ) -> Optional[
        Union[
            AddServiceTool,
            EditServiceTool,
            DeleteServiceTool,
            ListServicesTool,
            ExitSettingsTool,
        ]
    ]:
        lower_text = text.lower().strip()
        # Fast exit check
        if lower_text in ["exit", "quit", "back", "done"]:
            return ExitSettingsTool()

        system_instruction = self.prompts_service.render("settings_system_instruction")
        if service_context:
            system_instruction += (
                f"\n\nCURRENT SERVICES:\n{service_context}\n"
                "Use these names to help identify which service the user is referring to."
            )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": text},
        ]

        # Retry logic: Try twice if first attempt doesn't result in a tool call
        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.settings_tools,
                    tool_choice="auto",
                )
                
                message = response.choices[0].message
                if message.tool_calls:
                    tool_call = message.tool_calls[0]
                    function_name = tool_call.function.name
                    
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        self.logger.error(
                            f"Failed to parse JSON arguments: {tool_call.function.arguments}"
                        )
                        return None
                    
                    model_map = {
                        "AddServiceTool": AddServiceTool,
                        "EditServiceTool": EditServiceTool,
                        "DeleteServiceTool": DeleteServiceTool,
                        "ListServicesTool": ListServicesTool,
                        "ExitSettingsTool": ExitSettingsTool,
                    }
                    
                    model_cls = model_map.get(function_name)
                    if model_cls:
                        try:
                            return model_cls(**arguments)
                        except ValidationError as e:
                            self.logger.error(f"Validation error for {function_name}: {e}")
                            return None
                
                # If no tool calls and it's our first attempt, try once more with a nudge
                if attempt == 0:
                    messages.append({"role": "assistant", "content": message.content or "[no tool call produced]"})
                    messages.append({"role": "user", "content": self.prompts_service.render("retry_instruction")})
                    self.logger.info(f"LLM failed to produce tool call for settings, retrying...")
                else:
                    return None
                            
            except Exception as e:
                self.logger.error(f"LLM Parse Error (Settings - attempt {attempt+1}): {e}", exc_info=True)
                if attempt == 1:
                    return None
        
        return None


    async def parse(
        self, text: str, system_time: Optional[str] = None, service_catalog: Optional[str] = None
    ) -> Optional[
        Union[
            AddJobTool,
            AddLeadTool,
            ScheduleJobTool,
            AddRequestTool,
            SearchTool,
            UpdateSettingsTool,
            ConvertRequestTool,
            HelpTool,
            GetPipelineTool,
            str,
        ]
    ]:
        # 1. Keyword pre-filtering
        lower_text = text.lower().strip()
        if lower_text in ["undo", "cancel"]:
            return None
        if lower_text in ["hi", "hello", "hey", "greetings"]:
            return None
        if lower_text in ["help", "usage", "commands"]:
            return HelpTool()

        # 2. Construct Prompt
        system_instruction = self.prompts_service.render("system_instruction")
        if service_catalog:
            system_instruction += (
                f"\n\nSERVICE CATALOG MATCHING:\n"
                f"The following services are available (ID: Name - Price):\n"
                f"{service_catalog}\n\n"
                "MATCHING RULES:\n"
                "1. If a line item matches a service in the CATALOG (semantically or strictly):\n"
                "   - Set 'service_id' to the integer ID from the catalog.\n"
                "   - Set 'service_name' to the Name from the catalog.\n"
                "   - Set 'unit_price' to the catalog price (unless user specifies a custom overriding price).\n"
                "   - ALWAYS leave 'total_price' as NULL; the backend will calculate it from quantity and unit price.\n"
                "2. If NO match is found in the catalog, leave 'service_id' and 'service_name' as null and extract details from text."
            )

        messages = [{"role": "system", "content": system_instruction}]

        user_prompt = text
        if system_time:
            user_prompt = f"Current system time: {system_time}\n\nUser input: {text}\n\nIf the user specifies a time, please resolve it to an ISO format string and put it in the 'iso_time' field of the tool call."

        messages.append({"role": "user", "content": user_prompt})

        # Retry logic: Try twice if first attempt doesn't result in a tool call
        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    extra_body={
                        "provider": {
                            "sort": "throughput",
                        }
                    },
                )

                message = response.choices[0].message
                if message.tool_calls:
                    tool_call = message.tool_calls[0]
                    function_name = tool_call.function.name

                    # Parse arguments
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        self.logger.error(
                            f"Failed to parse JSON arguments: {tool_call.function.arguments}"
                        )
                        return None

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
                        "SendInvoiceTool": SendInvoiceTool,
                    }

                    model_cls = model_map.get(function_name)
                    if model_cls:
                        try:
                            return model_cls(**arguments)
                        except ValidationError as e:
                            self.logger.error(f"Validation error for {function_name}: {e}")
                            return None

                # If no tool calls and it's our first attempt, try once more with a nudge
                if attempt == 0:
                    messages.append({"role": "assistant", "content": message.content or "[no tool call produced]"})
                    messages.append({"role": "user", "content": self.prompts_service.render("retry_instruction")})
                    self.logger.info(f"LLM failed to produce tool call, retrying...")
                else:
                    # If second attempt still no tool call, return the text response (for reasoning/clarification)
                    return message.content or None

            except Exception as e:
                self.logger.error(f"LLM Parse Error (attempt {attempt+1}): {e}", exc_info=True)
                if attempt == 1:
                    return None
        
        return None


# Singleton instance
parser = LLMParser()
