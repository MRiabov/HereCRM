import json
import logging
from typing import List, Optional, Any, Dict

logger = logging.getLogger(__name__)


class MockFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    def __init__(self, id: str, function: MockFunction):
        self.id = id
        self.function = function
        self.type = "function"


class MockMessage:
    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[MockToolCall]] = None,
        reasoning: Optional[str] = None,
    ):
        self.content = content
        self.tool_calls = tool_calls
        self.role = "assistant"
        self.reasoning = reasoning

    def dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
            if self.tool_calls
            else None,
        }


class MockChoice:
    def __init__(self, message: MockMessage, finish_reason: str = "stop"):
        self.message = message
        self.finish_reason = finish_reason


class MockUsage:
    def __init__(self):
        self.prompt_tokens = 10
        self.completion_tokens = 10
        self.total_tokens = 20


class MockResponse:
    def __init__(self, choices: List[MockChoice]):
        self.choices = choices
        self.usage = MockUsage()
        self.id = "mock-response-id"


class MockCompletions:
    async def create(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> MockResponse:
        last_message = messages[-1]["content"].lower()
        logger.info(f"[MOCK_LLM] Received request: {last_message}")

        # Deterministic Responses Registry
        if "add a job" in last_message or "create a job" in last_message:
            tool_call = MockToolCall(
                id="call_mock_add_job",
                function=MockFunction(
                    name="AddJobTool",
                    arguments=json.dumps(
                        {
                            "description": "New Job",
                            "customer_name": "Test Customer",
                            "status": "PENDING",
                        }
                    ),
                ),
            )
            return MockResponse([MockChoice(MockMessage(tool_calls=[tool_call]))])

        elif "schedule" in last_message:
            tool_call = MockToolCall(
                id="call_mock_schedule",
                function=MockFunction(
                    name="ScheduleJobTool",
                    arguments=json.dumps(
                        {
                            "job_id": 1,
                            "employee_id": 1,
                            "start_time": "2024-01-01T09:00:00",
                        }
                    ),
                ),
            )
            return MockResponse([MockChoice(MockMessage(tool_calls=[tool_call]))])

        elif "add a lead" in last_message:
            tool_call = MockToolCall(
                id="call_mock_add_lead",
                function=MockFunction(
                    name="AddLeadTool",
                    arguments=json.dumps({"name": "New Lead", "phone": "555-0199"}),
                ),
            )
            return MockResponse([MockChoice(MockMessage(tool_calls=[tool_call]))])

        # Default fallback response
        return MockResponse(
            [
                MockChoice(
                    MockMessage(
                        content="I am a mock AI. I didn't understand that command in my registry."
                    )
                )
            ]
        )


class MockChat:
    def __init__(self):
        self.completions = MockCompletions()


class MockOpenAIClient:
    def __init__(
        self, base_url: str = "", api_key: str = "", posthog_client: Any = None
    ):
        self.chat = MockChat()
        logger.info("[MOCK_LLM] Initialized MockOpenAIClient")
