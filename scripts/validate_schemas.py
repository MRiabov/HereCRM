import json
import sys
import os
from pydantic.v1 import ValidationError

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all tool modules
import src.uimodels as uimodels
import src.tools.employee_management as employee_management
import src.tools.invoice_tools as invoice_tools

DATA_FILE = "tests/data/llm_validation.json"


def validate():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        sys.exit(1)

    with open(DATA_FILE, "r") as f:
        test_cases = json.load(f)

    errors = []

    # Collect all tool classes
    all_tools = {}
    for module in [uimodels, employee_management, invoice_tools]:
        for name in dir(module):
            attr = getattr(module, name)
            if isinstance(attr, type) and name.endswith("Tool"):
                all_tools[name] = attr

    print(f"Discovered {len(all_tools)} tool classes.")

    for case in test_cases:
        case_id = case.get("id", "unknown")
        logic = case.get("expected_logic", {})
        tool_name = logic.get("tool_called")

        if not tool_name:
            continue

        if tool_name not in all_tools:
            errors.append(f"Case {case_id}: Tool '{tool_name}' not found in codebase.")
            continue

        tool_cls = all_tools[tool_name]
        expected_args = logic.get("expected_args", {})

        try:
            # Try to instantiate the tool with expected args to validate schema
            # We use construct() or just tool_cls(**expected_args)
            # tool_cls(**expected_args) is better as it triggers validation
            tool_cls(**expected_args)
        except ValidationError as e:
            errors.append(
                f"Case {case_id}: Schema mismatch for {tool_name}. Errors: {e.errors()}"
            )
        except Exception as e:
            errors.append(f"Case {case_id}: Error validating {tool_name}: {str(e)}")

    if errors:
        print(f"❌ Schema validation failed with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"✅ All {len(test_cases)} test case schemas are valid.")


if __name__ == "__main__":
    validate()
