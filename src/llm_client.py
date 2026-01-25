import logging
import json
import os
import time
from typing import Union, Optional, Any
from openai import AsyncOpenAI
from pydantic import ValidationError

from src.config import settings
from src.services.analytics import analytics
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
    CreateQuoteTool,
    LocateEmployeeTool,
    CheckETATool,
    AutorouteTool,
    ConnectGoogleCalendarTool,
    DisconnectGoogleCalendarTool,
    GoogleCalendarStatusTool,
)
from src.tools.invoice_tools import SendInvoiceTool
from src.tools.employee_management import (
    ShowScheduleTool,
    AssignJobTool,
    InviteUserTool,
    ExitEmployeeManagementTool,
)
from src.uimodels import (
    UpdateCustomerStageTool,
    MassEmailTool,
    QuickBooksStatusTool,
    SyncQuickBooksTool,
    UpdateWorkflowSettingsTool,
    ConnectQuickBooksTool,
    DisconnectQuickBooksTool,
)
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
                "parameters": CreateQuoteTool.schema(),
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
                "description": tool_desc.get("ShowScheduleTool", "Show the schedule for all employees for today. Use when user wants to see team status."),
                "parameters": ShowScheduleTool.schema(),
            },
        })
        self.tools.append({
            "type": "function",
            "function": {
                "name": "AssignJobTool",
                "description": tool_desc.get("AssignJobTool", "Assign a specific job to an employee by name."),
                "parameters": AssignJobTool.schema(),
            },
        })
        self.tools.append({
            "type": "function",
            "function": {
                "name": "LocateEmployeeTool",
                "description": tool_desc.get("LocateEmployeeTool", "Locate an employee or list location of all employees."),
                "parameters": LocateEmployeeTool.schema(),
            },
        })
        self.tools.append({
            "type": "function",
            "function": {
                "name": "CheckETATool",
                "description": tool_desc.get("CheckETATool", "Check the estimated time of arrival for a technician to a customer."),
                "parameters": CheckETATool.schema(),
            },
        })
        self.tools.append({
            "type": "function",
            "function": {
                "name": "AutorouteTool",
                "description": tool_desc.get("AutorouteTool", "Preview or execute automatic job routing to minimize distance and maximize jobs."),
                "parameters": AutorouteTool.schema(),
            },
        })

        self.tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "UpdateCustomerStageTool",
                    "description": tool_desc.get("UpdateCustomerStageTool", "Update a customer's pipeline stage (e.g. mark as lost, contacted)."),
                    "parameters": UpdateCustomerStageTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "MassEmailTool",
                    "description": tool_desc.get("MassEmailTool", "Send a broadcast message to many customers at once."),
                    "parameters": MassEmailTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "SyncQuickBooksTool",
                    "description": tool_desc.get("SyncQuickBooksTool", "Manually trigger a sync with QuickBooks accounting."),
                    "parameters": SyncQuickBooksTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "QuickBooksStatusTool",
                    "description": tool_desc.get("QuickBooksStatusTool", "Check the status of QuickBooks integration."),
                    "parameters": QuickBooksStatusTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "UpdateWorkflowSettingsTool",
                    "description": tool_desc.get("UpdateWorkflowSettingsTool", "Update business workflow settings like invoicing/quoting frequency."),
                    "parameters": UpdateWorkflowSettingsTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ExportQueryTool",
                    "description": tool_desc.get("ExportQueryTool", "Export data as CSV based on search query."),
                    "parameters": ExportQueryTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ConnectGoogleCalendarTool",
                    "description": tool_desc.get("ConnectGoogleCalendarTool", "Initiate Google Calendar connection."),
                    "parameters": ConnectGoogleCalendarTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "DisconnectGoogleCalendarTool",
                    "description": tool_desc.get("DisconnectGoogleCalendarTool", "Disconnect Google Calendar."),
                    "parameters": DisconnectGoogleCalendarTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "GoogleCalendarStatusTool",
                    "description": tool_desc.get("GoogleCalendarStatusTool", "Check Google Calendar status."),
                    "parameters": GoogleCalendarStatusTool.schema(),
                },
            }
        ])

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

        self.employee_mgmt_tools = [
            {
                "type": "function",
                "function": {
                    "name": "InviteUserTool",
                    "description": "Invite a new person to join the business as an employee.",
                    "parameters": InviteUserTool.schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ExitEmployeeManagementTool",
                    "description": "Exit the employee management mode.",
                    "parameters": ExitEmployeeManagementTool.schema(),
                },
            },
        ]

    async def _chat_with_retry(
        self, 
        messages: list[dict], 
        tools: list[dict], 
        model_map: dict[str, Any],
        distinct_id: str = "anonymous",
        original_query: str = ""
    ) -> Optional[Any]:
        """
        Executes a chat completion with retry logic for missing tool calls, 
        JSON parsing errors, and Pydantic validation errors.
        """
        for attempt in range(2):
            try:
                start_time = time.perf_counter()
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
                latency = time.perf_counter() - start_time
                usage = response.usage
                input_tokens = usage.prompt_tokens if usage else None
                output_tokens = usage.completion_tokens if usage else None
                
                # Format output choices for PostHog
                output_choices = [
                    {"message": choice.message.dict(), "finish_reason": choice.finish_reason}
                    for choice in response.choices
                ]

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
                        analytics.capture_llm_query(
                            user_id=distinct_id,
                            query=original_query,
                            success=False,
                            attempts=attempt + 1,
                            error_type="no_tool_call",
                            model=self.model,
                            latency=latency,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            input_messages=messages,
                            output_choices=output_choices
                        )
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
                        analytics.capture_llm_query(
                            user_id=distinct_id,
                            query=original_query,
                            success=False,
                            attempts=attempt + 1,
                            error_type="json_decode_error",
                            model=self.model,
                            latency=latency,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            input_messages=messages,
                            output_choices=output_choices
                        )
                        return None

                # Check for Validation errors
                model_cls = model_map.get(function_name)
                if model_cls:
                    try:
                        result = model_cls(**arguments)
                        analytics.capture_llm_query(
                            user_id=distinct_id,
                            query=original_query,
                            success=True,
                            attempts=attempt + 1,
                            tool_called=function_name,
                            model=self.model,
                            latency=latency,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            input_messages=messages,
                            output_choices=output_choices
                        )
                        return result
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
                            analytics.capture_llm_query(
                                user_id=distinct_id,
                                query=original_query,
                                success=False,
                                attempts=attempt + 1,
                                error_type="validation_error",
                                tool_called=function_name,
                                model=self.model,
                                latency=latency,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                input_messages=messages,
                                output_choices=output_choices
                            )
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

        return await self._chat_with_retry(
            messages, 
            self.datamgmt_tools, 
            model_map,
            distinct_id=text, # Defaulting to text if unknown, but better context would be ideal
            original_query=text
        )

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
        
        return await self._chat_with_retry(
            messages, 
            self.settings_tools, 
            model_map,
            distinct_id=text,
            original_query=text
        )

    async def parse_employee_management(
        self, text: str
    ) -> Optional[Union[InviteUserTool, ExitEmployeeManagementTool]]:
        lower_text = text.lower().strip()
        if lower_text in ["exit", "quit", "back", "done"]:
            return ExitEmployeeManagementTool()

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant for Employee Management. "
                "The user wants to invite new employees or manage existing ones. "
                "Map their request to the appropriate tool.",
            },
            {"role": "user", "content": text},
        ]

        model_map = {
            "InviteUserTool": InviteUserTool,
            "ExitEmployeeManagementTool": ExitEmployeeManagementTool,
        }

        return await self._chat_with_retry(
            messages, 
            self.employee_mgmt_tools, 
            model_map,
            distinct_id=text,
            original_query=text
        )

    async def parse(
        self, 
        text: str, 
        system_time: Optional[str] = None, 
        service_catalog: Optional[str] = None,
        channel_name: str = "whatsapp",
        user_context: Optional[dict] = None
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
            UpdateCustomerStageTool,
            MassEmailTool,
            SyncQuickBooksTool,
            QuickBooksStatusTool,
            UpdateWorkflowSettingsTool,
            str,
        ]
    ]:
        # 1. Keyword pre-filtering
        lower_text = text.lower().strip()
        if lower_text == "help":
            return HelpTool()
        if lower_text in ["undo", "cancel"]:
            return None
        
        # We removed strict "help" and "hi" filtering to let the LLM handle 
        # varied intents and context better, especially for PWA chat.

        # 2. Construct Prompt
        system_instruction = self.prompts_service.render("system_instruction")
        if service_catalog:
            system_instruction += self.prompts_service.render(
                "service_catalog_matching", service_catalog=service_catalog
            )
        
        if user_context:
            system_instruction += f"\n\nUSER CONTEXT:\n- Role: {user_context.get('role', 'unknown')}\n"
            if "active_addons" in user_context:
                system_instruction += f"- Active Addons: {user_context['active_addons']}\n"
            for key, val in user_context.items():
                if key not in ["role", "active_addons", "channel"]:
                     system_instruction += f"- {key}: {val}\n"

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
            "CreateQuoteTool": CreateQuoteTool,
            "LocateEmployeeTool": LocateEmployeeTool,
            "CheckETATool": CheckETATool,
            "AutorouteTool": AutorouteTool,
            "UpdateCustomerStageTool": UpdateCustomerStageTool,
            "MassEmailTool": MassEmailTool,
            "SyncQuickBooksTool": SyncQuickBooksTool,
            "QuickBooksStatusTool": QuickBooksStatusTool,
            "UpdateWorkflowSettingsTool": UpdateWorkflowSettingsTool,
            "ExportQueryTool": ExportQueryTool,
            "ConnectQuickBooksTool": ConnectQuickBooksTool,
            "DisconnectQuickBooksTool": DisconnectQuickBooksTool,
            "ConnectGoogleCalendarTool": ConnectGoogleCalendarTool,
            "DisconnectGoogleCalendarTool": DisconnectGoogleCalendarTool,
            "GoogleCalendarStatusTool": GoogleCalendarStatusTool,
        }

        distinct_id = "anonymous"
        if user_context:
            distinct_id = user_context.get("phone_number") or user_context.get("clerk_id") or "anonymous"

        return await self._chat_with_retry(
            messages, 
            self.tools, 
            model_map,
            distinct_id=distinct_id,
            original_query=text
        )



# Singleton instance
parser = LLMParser()
