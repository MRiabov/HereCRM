from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User
from src.repositories import CustomerRepository
from src.services.template_service import TemplateService
from src.services.chat_utils import format_line_items
from src.uimodels import (
    AddJobTool,
    AddLeadTool,
    EditCustomerTool,
    ScheduleJobTool,
    AddRequestTool,
    ConvertRequestTool,
    GetPipelineTool,
    UpdateCustomerStageTool,
    CreateQuoteTool,
    RequestUpgradeTool,
    GetBillingStatusTool,
)
from src.tools.invoice_tools import SendInvoiceTool


class SummaryGenerator:
    def __init__(self, session: AsyncSession, template_service: TemplateService):
        self.session = session
        self.template_service = template_service

    async def generate_summary(self, tool_call: Any, user: User) -> str:
        customer_repo = CustomerRepository(self.session)
        # Map tool class names to friendly display names
        friendly_names = {
            "AddJobTool": "Job",
            "AddLeadTool": "Add Lead",
            "EditCustomerTool": "Update",
            "ScheduleJobTool": "Schedule",
            "AddRequestTool": "Request",
            "SearchTool": "Search",
            "UpdateSettingsTool": "Settings",
            "ConvertRequestTool": "Convert",
            "HelpTool": "Help",
            "GetPipelineTool": "Pipeline",
            "UpdateCustomerStageTool": "Pipeline Stage Update",
            "SendInvoiceTool": "Send Invoice",
            "GetBillingStatusTool": "Billing Status",
            "RequestUpgradeTool": "Request Upgrade",
            "LocateEmployeeTool": "Locate",
            "CheckETATool": "ETA",
            "CreateQuoteTool": "Quote",
            "SendStatusTool": "Send Status",
        }
        model_name = tool_call.__class__.__name__
        name = friendly_names.get(model_name, model_name.replace("Tool", ""))

        # Use category if available (e.g. for AddJobTool)
        if isinstance(tool_call, CreateQuoteTool):
            customers = await customer_repo.search(
                tool_call.customer_identifier, user.business_id
            )
            customer = customers[0] if customers and len(customers) == 1 else None

            client_details = self.template_service.render(
                "client_details",
                name=customer.name if customer else tool_call.customer_identifier,
                phone=customer.phone if customer else "Not supplied",
                address=customer.street
                if customer
                else "Not supplied",  # Assuming street for address
            )

            line_items_detail = ""
            total_amount = 0.0
            if tool_call.items:
                line_items_detail = "\nItems:"
                for item in tool_call.items:
                    line_items_detail += (
                        f"\n- {item.description}: {item.quantity} x ${item.price:.2f}"
                    )
                    total_amount += item.quantity * item.price

            summary = self.template_service.render(
                "quote_summary",
                client_details=client_details,
                description=f"{len(tool_call.items)} items",
                total=f"${total_amount:.2f}",
                line_items=line_items_detail,
            )

            # Check for contact details
            if customer and not (customer.phone or customer.email):
                warning = self.template_service.render(
                    "warning_no_contact_details", type="quote"
                )
                summary = f"{summary}\n\n{warning}"

            return summary

        if isinstance(tool_call, AddJobTool):
            price_val = "Not supplied"
            if tool_call.price is not None:
                if tool_call.price == int(tool_call.price):
                    price_val = f"{int(tool_call.price)}$"
                else:
                    price_val = f"{tool_call.price:.2f}$"

            client_details = self.template_service.render(
                "client_details",
                name=tool_call.customer_name or "Not supplied",
                phone=tool_call.customer_phone or "Not supplied",
                address=tool_call.location or "Not supplied",
            )

            line_items_detail = ""
            if hasattr(tool_call, "line_items") and tool_call.line_items:
                line_items_detail = f"\n{format_line_items(tool_call.line_items)}"

            return self.template_service.render(
                "job_summary",
                category="Job",  # AddJobTool is now strictly jobs
                client_details=client_details,
                price=price_val,
                description=tool_call.description or "Not supplied",
                status=tool_call.status.capitalize()
                if tool_call.status
                else "Pending confirmation",
                line_items=line_items_detail,
            )

        if isinstance(tool_call, AddLeadTool):
            client_details = self.template_service.render(
                "client_details",
                name=tool_call.name,
                phone=tool_call.phone or "Not supplied",
                address=tool_call.location or "Not supplied",
            )
            return self.template_service.render(
                "lead_summary",
                client_details=client_details,
                description=tool_call.details or "Not supplied",
            )

        if isinstance(tool_call, EditCustomerTool):
            changes = []
            if tool_call.name:
                changes.append(f"Name to '{tool_call.name}'")
            if tool_call.phone:
                changes.append(f"Phone to '{tool_call.phone}'")
            if tool_call.location:
                changes.append(f"Address to '{tool_call.location}'")
            if tool_call.details:
                changes.append(f"Notes to '{tool_call.details}'")

            change_summary = ", ".join(changes) if changes else "no changes"
            return f"Updating {tool_call.query}: {change_summary}"

        if isinstance(tool_call, ScheduleJobTool):
            customers = (
                await customer_repo.search(tool_call.customer_query, user.business_id)
                if tool_call.customer_query
                else []
            )
            customer = customers[0] if customers and len(customers) == 1 else None

            client_details = self.template_service.render(
                "client_details",
                name=customer.name
                if customer
                else (tool_call.customer_query or "Unknown"),
                phone=customer.phone if customer else "Not supplied",
                address=customer.street if customer else "Not supplied",
            )
            return self.template_service.render(
                "schedule_summary",
                client_details=client_details,
                time=tool_call.time,
            )

        if isinstance(tool_call, AddRequestTool):
            customers = (
                await customer_repo.search(tool_call.customer_name, user.business_id)
                if tool_call.customer_name
                else []
            )
            customer = customers[0] if customers and len(customers) == 1 else None

            client_details = self.template_service.render(
                "client_details",
                name=customer.name
                if customer
                else (tool_call.customer_name or "Not supplied"),
                phone=customer.phone
                if customer
                else (tool_call.customer_phone or "Not supplied"),
                address=customer.street if customer else "Not supplied",
            )
            line_items_detail = ""
            if hasattr(tool_call, "line_items") and tool_call.line_items:
                line_items_detail = f"\n{format_line_items(tool_call.line_items)}"

            return self.template_service.render(
                "request_summary",
                client_details=client_details,
                time=tool_call.time,
                description=tool_call.description,
                line_items=line_items_detail,
            )

        if isinstance(tool_call, GetPipelineTool):
            return "display customers by pipeline stage"

        if isinstance(tool_call, UpdateCustomerStageTool):
            return f"update {tool_call.query}'s stage to {tool_call.stage.replace('_', ' ').title()}"

        if isinstance(tool_call, SendInvoiceTool):
            customers = await customer_repo.search(tool_call.query, user.business_id)
            customer = customers[0] if customers and len(customers) == 1 else None

            client_details = self.template_service.render(
                "client_details",
                name=customer.name if customer else tool_call.query,
                phone=customer.phone if customer else "Not supplied",
                address=customer.street if customer else "Not supplied",
            )
            summary = f"Generate and send invoice to {customer.name if customer else tool_call.query}\n{client_details}"

            if customer and not (customer.phone or customer.email):
                warning = self.template_service.render(
                    "warning_no_contact_details", type="invoice"
                )
                summary = f"{summary}\n\n{warning}"

            return summary

        if isinstance(tool_call, GetBillingStatusTool):
            return "check billing status"

        if isinstance(tool_call, RequestUpgradeTool):
            item = tool_call.item_id or tool_call.item_type
            return f"request upgrade for {tool_call.quantity} x {item}"

        if isinstance(tool_call, ConvertRequestTool):
            action_map = {
                "schedule": "Schedule",
                "complete": "Complete",
                "log": "Log",
                "quote": "Quote",
            }
            act = action_map.get(tool_call.action, tool_call.action).capitalize()
            return f"Convert to {act}: {tool_call.query}"

        if hasattr(tool_call, "description") and tool_call.description:
            return f"{name}: {tool_call.description}"
        elif hasattr(tool_call, "customer_query") and tool_call.customer_query:
            return f"{name}: {tool_call.customer_query}"
        elif hasattr(tool_call, "customer_name") and tool_call.customer_name:
            return f"{name}: {tool_call.customer_name}"
        elif hasattr(tool_call, "content"):
            return f"{name}: {tool_call.content[:50]}"
        elif hasattr(tool_call, "query"):
            return f"{name}: {tool_call.query}"
        return f"{name} operation"
