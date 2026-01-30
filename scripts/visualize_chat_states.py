import os
import json
import asyncio
import sys
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.llm_client import LLMParser
from src.services.template_service import TemplateService


async def main():
    parser = LLMParser()

    # Extract states and their configurations
    states = {}

    # 1. CRM / IDLE
    states["CRM (IDLE)"] = {
        "instruction": parser.system_instruction,
        "tools": parser.tools,
        "description": "General CRM assistant for jobs, customers, and requests.",
    }

    # 2. SETTINGS
    settings_instruction = parser.prompts_service.render("settings_system_instruction")
    states["SETTINGS"] = {
        "instruction": settings_instruction,
        "tools": parser.settings_tools,
        "description": "Assistant for managing business settings and services.",
    }

    # 3. DATA MANAGEMENT
    # Replicating logic from LLMParser.parse_data_management
    data_mgmt_instruction = (
        "You are a helpful assistant for a CRM data management system. "
        "The user will ask to export data or perform data operations. "
        "Map their request to the appropriate tool. "
        "If they ask to export, use ExportQueryTool. "
        "If they want to leave, use ExitDataManagementTool."
    )
    states["DATA MANAGEMENT"] = {
        "instruction": data_mgmt_instruction,
        "tools": parser.datamgmt_tools,
        "description": "Assistant for data export and management.",
    }

    # 4. EMPLOYEE MANAGEMENT
    # Replicating logic from LLMParser.parse_employee_management
    employee_mgmt_instruction = (
        "You are a helpful assistant for Employee Management. "
        "The user wants to invite new employees or manage existing ones. "
        "Map their request to the appropriate tool."
    )
    states["EMPLOYEE MANAGEMENT"] = {
        "instruction": employee_mgmt_instruction,
        "tools": parser.employee_mgmt_tools,
        "description": "Assistant for employee invitations and management.",
    }

    # 5. ACCOUNTING
    accounting_instruction = parser.prompts_service.render(
        "accounting_system_instruction"
    )
    # Identify accounting tools from main tools list for visualization
    accounting_tool_names = ["SyncQuickBooksTool", "QuickBooksStatusTool"]
    accounting_tools = [
        t for t in parser.tools if t["function"]["name"] in accounting_tool_names
    ]
    states["ACCOUNTING"] = {
        "instruction": accounting_instruction,
        "tools": accounting_tools,
        "description": "Assistant for QuickBooks synchronization.",
    }

    # Generate Markdown Output
    output_file = "chat_states_visualization.md"
    with open(output_file, "w") as f:
        f.write("# Chat State Machine Visualization\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("````carousel\n")

        for state_name, config in states.items():
            f.write(f"## State: {state_name}\n\n")
            f.write(f"> {config['description']}\n\n")

            f.write("### System Instruction\n")
            f.write("```markdown\n")
            f.write(config["instruction"])
            f.write("\n```\n\n")

            f.write("### Available Tools\n")
            for tool in config["tools"]:
                name = tool["function"]["name"]
                desc = tool["function"]["description"]
                f.write(f"#### {name}\n")
                f.write(f"{desc}\n\n")
                f.write("```json\n")
                f.write(json.dumps(tool["function"]["parameters"], indent=2))
                f.write("\n```\n\n")

            f.write("<!-- slide -->\n")

        f.write("````\n")

    print(f"Visualization generated: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
