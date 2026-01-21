import logging
import json
import os
from typing import Union, Optional, Any
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
    SendStatusTool,
    GetBillingStatusTool,
    RequestUpgradeTool,
    CreateQuoteInput,
)
from src.tools.invoice_tools import SendInvoiceTool
from src.tools.employee_management import ShowScheduleTool, AssignJobTool
from src.services.template_service import TemplateService
from src.config.loader import get_channel_config_loader


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
        self.system_instruction = self.prompts_service.render("system_instruction")

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
            {
                "type": "function",
                "function": {
                    "name": "GetBillingStatusTool",
                    "description": tool_desc.get("GetBillingStatusTool", "Check the current subscription status, limits, and usage."),
                    "parameters": GetBillingStatusTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "RequestUpgradeTool",
                    "description": tool_desc.get("RequestUpgradeTool", "Request an upgrade for seats or addons."),
                    "parameters": RequestUpgradeTool.schema(),
                },
            },
        ]

        self.tools.append({
            "type": "function",
            "function": {
                "name": "CreateQuoteTool",
                "description": tool_desc.get("CreateQuoteTool", "Create and send a quote to a customer"),
                "parameters": CreateQuoteInput.schema(),
            },
        })

        self.tools.append({
            "type": "function",
            "function": {
                "name": "SendStatusTool",
                "description": tool_desc.get("SendStatusTool", ""),
                "parameters": SendStatusTool.schema(),
            },
        })

        self.tools.append({
            "type": "function",
            "function": {
                "name": "SendInvoiceTool",
                "description": "Send a professional PDF invoice to a customer for their last job.",
                "parameters": SendInvoiceTool.schema(),
            },
        })
        self.tools.append({
            "type": "function",
            "function": {
                "name": "ShowScheduleTool",
                "description": "Show the schedule for all employees for today. Use when user wants to see team status.",
                "parameters": ShowScheduleTool.schema(),
            },
        })
        self.tools.append({
            "type": "function",
            "function": {
                "name": "AssignJobTool",
                "description": "Assign a specific job to an employee by name.",
                "parameters": AssignJobTool.schema(),
            },
        })

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
            {
                "type": "function",
                "function": {
                    "name": "UpdateSettingsTool",
                    "description": tool_desc.get("UpdateSettingsTool", ""),
                    "parameters": UpdateSettingsTool.schema(),
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

    async def _chat_with_retry(
        self, messages: list[dict], tools: list[dict], model_map: dict[str, Any]
    ) -> Optional[Any]:
        """
        Executes a chat completion with retry logic for missing tool calls, 
        JSON parsing errors, and Pydantic validation errors.
        """
        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    extra_body={
                        "provider": {
                            "sort": "throughput",
                        }
                    },
                )

                message = response.choices[0].message
                
                # Case 1: No tool calls produced
                if not message.tool_calls:
                    if attempt == 0:
                        self.logger.info("LLM failed to produce tool call, retrying...")
                        # Append the assistant's content (if any) and the retry instruction
                        messages.append({"role": "assistant", "content": message.content or "[no tool call produced]"})
                        messages.append({"role": "user", "content": self.prompts_service.render("retry_instruction")})
                        continue
                    else:
                        # Return None if final attempt failed, so the caller can handle it as an error/help message
                        return None

                # Process the first tool call
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                
                # Check for JSON errors
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    if attempt == 0:
                        self.logger.warning(f"JSON Decode Error: {e}")
                        # We must append the message properly so the API accepts the history
                        messages.append(message)
                        error_msg = f"JSON Decode Error: {str(e)}"
                        messages.append({
                            "role": "user", 
                            "content": self.prompts_service.render("retry_error_instruction", error=error_msg)
                        })
                        continue
                    else:
                        self.logger.error(f"JSON Decode Error on retry: {e}")
                        return None

                # Check for Validation errors
                model_cls = model_map.get(function_name)
                if model_cls:
                    try:
                        return model_cls(**arguments)
                    except ValidationError as e:
                        if attempt == 0:
                            self.logger.warning(f"Validation Error: {e}")
                            messages.append(message)
                            error_msg = f"Validation Error: {str(e)}"
                            messages.append({
                                "role": "user", 
                                "content": self.prompts_service.render("retry_error_instruction", error=error_msg)
                            })
                            continue
                        else:
                            self.logger.error(f"Validation Error on retry: {e}")
                            return None
                else:
                    self.logger.warning(f"Unknown tool called: {function_name}")
                    if attempt == 0:
                         messages.append(message)
                         messages.append({
                             "role": "user",
                             "content": self.prompts_service.render("retry_error_instruction", error=f"Unknown tool '{function_name}'. Please use one of the provided tools.")
                         })
                         continue
                    return None

            except Exception as e:
                self.logger.error(f"LLM Parse Error (attempt {attempt+1}): {e}", exc_info=True)
                if attempt == 1:
                    return None
        
        return None

    async def chat_completion(
        self, messages: list[dict], model: Optional[str] = None
    ) -> str:
        """
        Generates a direct text response from the LLM without tool calling.
        """
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            extra_body={
                "provider": {
                    "sort": "throughput",
                }
            },
        )
        return response.choices[0].message.content or ""

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

        model_map = {
            "ExportQueryTool": ExportQueryTool,
            "ExitDataManagementTool": ExitDataManagementTool,
        }

        return await self._chat_with_retry(messages, self.datamgmt_tools, model_map)

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

        model_map = {
            "AddServiceTool": AddServiceTool,
            "EditServiceTool": EditServiceTool,
            "DeleteServiceTool": DeleteServiceTool,
            "ListServicesTool": ListServicesTool,
            "ExitSettingsTool": ExitSettingsTool,
            "UpdateSettingsTool": UpdateSettingsTool,
        }
        
        return await self._chat_with_retry(messages, self.settings_tools, model_map)

    async def parse(
        self, 
        text: str, 
        system_time: Optional[str] = None, 
        service_catalog: Optional[str] = None,
        channel_name: str = "whatsapp"
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
            SendStatusTool,
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

        # 3. Channel constraints
        config_loader = get_channel_config_loader()
        channel_config = config_loader.get_channel_config(channel_name)
        max_length = channel_config.get("max_length", 4096)
        
        # If max_length is restrictive (e.g. SMS), add instruction
        if max_length < 200:
             system_instruction += f"\nIMPORTANT: The user is on a character-limited channel (max {max_length} chars). Keep your response Extremely concise. No fluff."

        messages = [{"role": "system", "content": system_instruction}]

        user_prompt = text
        if system_time:
            user_prompt = self.prompts_service.render(
                "user_time_prompt", system_time=system_time, text=text
            )

        messages.append({"role": "user", "content": user_prompt})

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
            "SendStatusTool": SendStatusTool,
            "GetBillingStatusTool": GetBillingStatusTool,
            "RequestUpgradeTool": RequestUpgradeTool,
            "ShowScheduleTool": ShowScheduleTool,
            "AssignJobTool": AssignJobTool,
            "CreateQuoteTool": CreateQuoteInput,
        }

        return await self._chat_with_retry(messages, self.tools, model_map)



# Singleton instance
parser = LLMParser()
