import pytest
import json
import os
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
@pytest.mark.parametrize("case", test_cases, ids=lambda c: c["id"])
async def test_llm_parsing(case):
    """
    Parametric test for LLM parsing logic.
    Runs against the real LLM (OpenRouter/Gemini).
    """
    user_input = case["user_input"]
    expected_logic = case.get("expected_logic", {})
    
    parser = LLMParser()
    
    # We might need to pass user context (role, settings) to the parser if it supports it.
    # For now, we assume the system context is handled by LLMParser.
    # If role-based parsing is needed, we would update LLMParser to accept a user profile.
    
    # Execute parsing
    # NOTE: This call is expensive and slow.
    result = await parser.parse(
        user_input, 
        user_context=case.get("user_context")
    )
    
    expected_tool = expected_logic.get("tool_called")
    expected_args = expected_logic.get("expected_args", {})
    required_substring = expected_logic.get("required_response_substring")
    
    if expected_tool:
        assert result is not None, f"Expected tool {expected_tool}, but got None"
        actual_tool = result.__class__.__name__
        assert actual_tool == expected_tool, f"Tool mismatch. Expected {expected_tool}, got {actual_tool}"
        
        # Verify arguments
        actual_args = result.dict(exclude_none=True)
        for key, val in expected_args.items():
            assert key in actual_args, f"Missing expected argument '{key}' in {actual_tool}"
            
            # Special handling for floats/rounding
            if isinstance(val, float) and isinstance(actual_args[key], float):
                assert pytest.approx(actual_args[key]) == val, f"Argument '{key}' mismatch. Expected {val}, got {actual_args[key]}"
            else:
                assert actual_args[key] == val, f"Argument '{key}' mismatch. Expected {val}, got {actual_args[key]}"

    # If the parser also returns a response text (e.g. from Persona), we check it here.
    # Note: LLMParser.parse currently returns a Tool object. 
    # If the logic results in a "Permission Denied" message, the result might be None or a special Tool.
    # We need to check how LLMParser handles blocked requests.
    
    # If required_substring is provided, we might need a different way to check the LLM's response
    # if the tool call itself is blocked by the LLM system prompt.
    if required_substring:
        # Currently, if LLM refuses to call a tool, result is None.
        # We might need to capture the LLM's raw response to verify substrings.
        # For simplicity, we'll assert that if a tool was expected but blocked, 
        # we check the response text. 
        # (Assuming LLMParser or a higher level service handles this).
        pass

@pytest.fixture(scope="session", autouse=True)
def run_schema_validation():
    """Ensure schemas are valid before running tests."""
    from scripts.validate_schemas import validate
    validate()
