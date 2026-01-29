import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.analytics import analytics
from src.llm_client import LLMParser


async def test_llm_tracing():
    print("Starting LLM Tracing Verification...")

    # 1. Mock PostHog Client
    mock_ph = MagicMock()
    analytics.client = mock_ph
    analytics.enabled = True

    # 2. Mock OpenAI Response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    # Simulate a tool call response with reasoning
    mock_message.content = "I will add a job for John. <thought>The user wants to add a job for John with price $50. I should use AddJobTool.</thought>"
    mock_message.tool_calls = [
        MagicMock(
            function=MagicMock(
                name="AddJobTool",
                arguments='{"customer_name": "John", "price": 50.0, "description": "test job"}',
            )
        )
    ]
    mock_message.dict.return_value = {
        "role": "assistant",
        "content": mock_message.content,
    }

    # Modern models might have .reasoning
    mock_message.reasoning = "This is explicit reasoning."

    mock_choice.message = mock_message
    mock_choice.finish_reason = "tool_calls"
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    # 3. Initialize LLMParser and mock the client's create method
    # Since we are using the PostHog wrapper, we need to mock it carefully
    parser = LLMParser()
    parser.client.chat.completions.create = AsyncMock(return_value=mock_response)

    # 4. Execute a call
    print("Executing mock chat_with_retry...")
    from src.uimodels import AddJobTool as AddJobToolModel

    result = await parser._chat_with_retry(
        messages=[{"role": "user", "content": "Add job for John $50"}],
        tools=[],
        model_map={"AddJobTool": AddJobToolModel},
        distinct_id="test_user_123",
        original_query="Add job for John $50",
    )

    print(f"Result: {result}")

    # 5. Verify PostHog calls
    # The wrapper should call capture, and our manual capture_llm_query should also call it.
    print(f"PostHog capture calls: {mock_ph.capture.call_count}")

    # Print the arguments of the capture calls to see if reasoning is present
    for i, call in enumerate(mock_ph.capture.call_args_list):
        args, kwargs = call
        event = args[1] if len(args) > 1 else kwargs.get("event")
        props = args[2] if len(args) > 2 else kwargs.get("properties", {})

        print(f"Call {i} event: {event}")
        if props and isinstance(props, dict) and props.get("$ai_thought"):
            print(f"  Found $ai_thought: {props['$ai_thought'][:50]}...")
        if props and isinstance(props, dict) and props.get("original_query"):
            print(f"  Found original_query: {props['original_query']}")

    assert mock_ph.capture.call_count >= 2, (
        "Should have at least 2 capture calls (one from wrapper, one from manual fallback)"
    )
    print("Verification Successful!")


if __name__ == "__main__":
    asyncio.run(test_llm_tracing())
