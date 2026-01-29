import os

os.environ["OPENROUTER_API_KEY"] = "sk-dummy"
os.environ["WHATSAPP_TOKEN"] = "dummy"

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from src.llm_client import LLMParser
from src.uimodels import AddJobTool


@pytest.fixture
def mock_parser():
    with patch("src.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        parser = LLMParser()
        yield parser, mock_client


@pytest.mark.asyncio
async def test_parse_add_job_with_line_items(mock_parser):
    parser, mock_client = mock_parser

    # Setup OpenAI response mock
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "AddJobTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "customer_name": "John Doe",
            "line_items": [
                {"description": "Window Clean", "total_price": 50.0},
                {"description": "Gutter Clean", "total_price": 30.0},
            ],
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("John Doe, Window Clean $50, Gutter Clean $30")

    assert isinstance(result, AddJobTool)
    assert result.customer_name == "John Doe"
    assert len(result.line_items) == 2
    assert result.line_items[0].description == "Window Clean"
    assert result.line_items[0].total_price == 50.0
    assert result.line_items[1].description == "Gutter Clean"
    assert result.line_items[1].total_price == 30.0
