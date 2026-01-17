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
    ExportQueryTool,
    ExitDataManagementTool,
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
        tool_desc = self.prompts_service.templates.get("tool_descriptions", {})

        # Define tools using OpenAI schema
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "AddJobTool",
                    "description": tool_desc.get("AddJobTool", ""),
                    "parameters": AddJobTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "AddLeadTool",
                    "description": tool_desc.get("AddLeadTool", ""),
                    "parameters": AddLeadTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "EditCustomerTool",
                    "description": tool_desc.get("EditCustomerTool", ""),
                    "parameters": EditCustomerTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ScheduleJobTool",
                    "description": tool_desc.get("ScheduleJobTool", ""),
                    "parameters": ScheduleJobTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "AddRequestTool",
                    "description": tool_desc.get("AddRequestTool", ""),
                    "parameters": AddRequestTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "SearchTool",
                    "description": tool_desc.get("SearchTool", ""),
                    "parameters": SearchTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "UpdateSettingsTool",
                    "description": tool_desc.get("UpdateSettingsTool", ""),
                    "parameters": UpdateSettingsTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ConvertRequestTool",
                    "description": tool_desc.get("ConvertRequestTool", ""),
                    "parameters": ConvertRequestTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "HelpTool",
                    "description": tool_desc.get("HelpTool", ""),
                    "parameters": HelpTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "GetPipelineTool",
                    "description": tool_desc.get("GetPipelineTool", ""),
                    "parameters": GetPipelineTool.schema(),
                },
            },
        ]

        self.settings_tools = [
            {
                "type": "function",
                "function": {
                    "name": "AddServiceTool",
                    "description": tool_desc.get("AddServiceTool", ""),
                    "parameters": AddServiceTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "EditServiceTool",
                    "description": tool_desc.get("EditServiceTool", ""),
                    "parameters": EditServiceTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "DeleteServiceTool",
                    "description": tool_desc.get("DeleteServiceTool", ""),
                    "parameters": DeleteServiceTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ListServicesTool",
                    "description": tool_desc.get("ListServicesTool", ""),
                    "parameters": ListServicesTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ExitSettingsTool",
                    "description": tool_desc.get("ExitSettingsTool", ""),
                    "parameters": ExitSettingsTool.schema(),
                },
            },
        ]

        self.datamgmt_tools = [
            {
                "type": "function",
                "function": {
                    "name": "ExportQueryTool",
                    "description": "Export data based on a natural language query.",
                    "parameters": ExportQueryTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ExitDataManagementTool",
                    "description": "Exit the data management mode.",
                    "parameters": ExitDataManagementTool.schema(),
                },
            },
        ]

    async def parse_data_management(
        self, text: str
    ) -> Optional[Union[ExportQueryTool, ExitDataManagementTool]]:
        lower_text = text.lower().strip()
        if lower_text in ["exit", "quit", "back", "done"]:
            return ExitDataManagementTool()

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant for a CRM data management system. "
                "The user will ask to export data or perform data operations. "
                "Map their request to the appropriate tool. "
                "If they ask to export, use ExportQueryTool. "
                "If they want to leave, use ExitDataManagementTool.",
            },
            {"role": "user", "content": text},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.datamgmt_tools,
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

                if function_name == "ExportQueryTool":
                    return ExportQueryTool(**arguments)
                elif function_name == "ExitDataManagementTool":
                    return ExitDataManagementTool(**arguments)

            return None

        except Exception as e:
            self.logger.error(f"LLM Parse Error (DataMgmt): {e}", exc_info=True)
            return None

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
            system_instruction += self.prompts_service.render(
                "settings_current_services", service_context=service_context
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
            system_instruction += self.prompts_service.render(
                "service_catalog_matching", service_catalog=service_catalog
            )

        messages = [{"role": "system", "content": system_instruction}]

        user_prompt = text
        if system_time:
            user_prompt = self.prompts_service.render(
                "user_time_prompt", system_time=system_time, text=text
            )

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
