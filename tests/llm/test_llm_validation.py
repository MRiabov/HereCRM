import pytest
import json
import os
import asyncio
from unittest.mock import MagicMock
from src.llm_client import LLMParser
from scripts.validate_schemas import DATA_FILE


# Load test cases
def load_test_cases():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


test_cases = load_test_cases()


@pytest.mark.llm_validation
@pytest.mark.asyncio
async def test_llm_parsing():
    """
    Runs all LLM validation test cases in parallel using asyncio.
    Uses a semaphore to limit concurrent requests to avoid rate limits.
    Aggregates failures into a single report.
    """
    cases = load_test_cases()
    if not cases:
        pytest.skip("No test cases found in data file.")

    # Shared parser instance
    parser = LLMParser()

    # Semaphore to limit concurrency (e.g. 5 concurrent requests)
    # Adjust this based on your API rate limits
    concurrency_limit = 5
    sem = asyncio.Semaphore(concurrency_limit)

    async def sem_task(case):
        async with sem:
            return await validate_case(case, parser)

    # Run all cases
    results = await asyncio.gather(
        *[sem_task(c) for c in cases], return_exceptions=True
    )

    failures = []
    for i, res in enumerate(results):
        case_id = cases[i].get("id", f"index-{i}")
        if isinstance(res, Exception):
            failures.append(f"Case {case_id} crashed: {str(res)}")
        elif res:  # validate_case returns an error string on failure, None on success
            failures.append(f"Case {case_id} failed: {res}")

    if failures:
        pytest.fail("\n".join(failures))


async def validate_case(case, parser):
    """
    Validates a single test case.
    Returns None if success, or an error string if failure.
    """
    user_input = case["user_input"]
    expected_logic = case.get("expected_logic", {})
    user_context = case.get("user_context", {})
    service_catalog = case.get("service_catalog")
    system_time = case.get("system_time")

    # Extract channel from user_context (defaults to WHATSAPP for backward compat)
    channel_name = (
        user_context.pop("channel", "WHATSAPP")
        if "channel" in user_context
        else "WHATSAPP"
    )

    try:
        # Execute parsing with all context variables
        result = await parser.parse(
            user_input,
            system_time=system_time,
            service_catalog=service_catalog,
            channel_name=channel_name,
            user_context=user_context,
        )
    except Exception as e:
        return f"Parser raised exception: {str(e)}"

    expected_tool = expected_logic.get("tool_called")
    expected_args = expected_logic.get("expected_args", {})
    required_substring = expected_logic.get("required_response_substring")

    if expected_tool:
        if result is None:
            return f"Expected tool {expected_tool}, but got None"

        actual_tool = result.__class__.__name__
        if actual_tool != expected_tool:
            return f"Tool mismatch. Expected {expected_tool}, got {actual_tool}"

        # Verify arguments
        actual_args = result.dict(exclude_none=True)
        for key, val in expected_args.items():
            if val == "__ANY__":
                continue

            if key not in actual_args:
                return f"Missing expected argument '{key}' in {actual_tool}"

            # Special handling for floats/rounding
            if isinstance(val, float) and isinstance(actual_args[key], float):
                # Using simple approximation check since pytest.approx is not easily used here manually
                # or we can use it inside try-except
                if abs(actual_args[key] - val) > 1e-6:
                    return f"Argument '{key}' mismatch. Expected {val}, got {actual_args[key]}"

            # Special handling for line_items (list of dicts)
            elif key == "line_items" and isinstance(val, list):
                if err := _verify_line_items(val, actual_args[key]):
                    return err
            # Special handling for items (CreateQuoteTool)
            elif key == "items" and isinstance(val, list):
                if err := _verify_line_items(val, actual_args[key]):
                    return err
            else:
                actual = actual_args[key]
                # Handle Enum members by extracting their value
                if hasattr(actual, "value"):
                    actual = actual.value

                # Check for equality. If mismatch, try string comparison as fallback
                if actual != val:
                    # Allow permissive substring matching for strings (case-insensitive)
                    if isinstance(val, str) and isinstance(actual, str):
                        if (
                            val.lower() not in actual.lower()
                            and actual.lower() not in val.lower()
                        ):
                            return f"Argument '{key}' mismatch. Expected '{val}', got '{actual_args[key]}'"
                    elif str(actual) != str(val):
                        return f"Argument '{key}' mismatch. Expected {val}, got {actual_args[key]}"

    # If required_substring is provided check logic (placeholder based on original code)
    if required_substring:
        pass

    return None


def _verify_line_items(expected_items: list, actual_items: list):
    """
    Verify that line items match expected values.
    Returns None on success, error message string on failure.
    """
    if len(actual_items) < len(expected_items):
        return f"Expected at least {len(expected_items)} line items, got {len(actual_items)}"

    for i, expected_item in enumerate(expected_items):
        actual_item = actual_items[i] if i < len(actual_items) else {}

        for field, expected_val in expected_item.items():
            if field not in actual_item:
                return f"Line item {i}: Missing field '{field}'. Actual: {actual_item}"

            actual_val = actual_item[field]

            # Description matching: case-insensitive contains check for flexibility
            if field == "description":
                if (
                    expected_val.lower() not in actual_val.lower()
                    and actual_val.lower() not in expected_val.lower()
                ):
                    return f"Line item {i}: Description mismatch. Expected '{expected_val}', got '{actual_val}'"
            # Float comparison with tolerance
            elif isinstance(expected_val, float) and isinstance(
                actual_val, (int, float)
            ):
                if abs(float(actual_val) - expected_val) > 1e-6:
                    return f"Line item {i}: Field '{field}' mismatch. Expected {expected_val}, got {actual_val}"
            else:
                if actual_val != expected_val:
                    return f"Line item {i}: Field '{field}' mismatch. Expected {expected_val}, got {actual_val}"
    return None


@pytest.fixture(scope="session", autouse=True)
def run_schema_validation():
    """Ensure schemas are valid before running tests."""
    from scripts.validate_schemas import validate

    validate()


@pytest.fixture(autouse=True)
def mock_analytics(monkeypatch):
    """
    Mock analytics to prevent PostHog from trying to upload events during tests.
    This avoids 'I/O operation on closed file' and connection errors.
    """
    mock = MagicMock()
    # Mock the singleton instance in src.services.analytics
    monkeypatch.setattr("src.services.analytics.analytics.client", mock)
    # Also mock usage in llm_client if necessary (though it uses the singleton)
    return mock
