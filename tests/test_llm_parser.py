import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.llm_client import LLMParser
from src.uimodels import AddJobTool, ConvertRequestTool

@pytest.fixture
def mock_parser():
    with patch("google.generativeai.configure"):
        with patch("google.generativeai.GenerativeModel") as MockModel:
            parser = LLMParser()
            yield parser, MockModel.return_value

@pytest.mark.asyncio
async def test_parse_add_job(mock_parser):
    parser, mock_model = mock_parser
    
    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    
    mock_part.function_call.name = "AddJobTool"
    mock_part.function_call.args = {
        "customer_name": "John Doe",
        "description": "Fix the leaky faucet",
        "price": 50.0
    }
    
    # Mocking hierarchy for response.candidates[0].content.parts[0]
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    
    mock_chat = MagicMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)
    mock_model.start_chat.return_value = mock_chat
    
    result = await parser.parse("Add a job for John Doe to fix the leaky faucet for $50")
    
    assert isinstance(result, AddJobTool)
    assert result.customer_name == "John Doe"
    assert result.description == "Fix the leaky faucet"
    assert result.price == 50.0

@pytest.mark.asyncio
async def test_parse_undo_cancel(mock_parser):
    parser, _ = mock_parser
    
    # Pre-filtering should catch these before any LLM call
    assert await parser.parse("Undo") is None
    assert await parser.parse("  CANCEL  ") is None

@pytest.mark.asyncio
async def test_parse_empty_candidates(mock_parser):
    parser, mock_model = mock_parser
    
    mock_response = MagicMock()
    mock_response.candidates = [] # Empty candidates (e.g. safety filter)
    
    mock_chat = MagicMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)
    mock_model.start_chat.return_value = mock_chat
    
    result = await parser.parse("Something that triggers safety filter")
    assert result is None

@pytest.mark.asyncio
async def test_parse_no_tool_call(mock_parser):
    parser, mock_model = mock_parser
    
    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None # No function call
    mock_part.text = "Hello, how can I help you?"
    
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    
    mock_chat = MagicMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)
    mock_model.start_chat.return_value = mock_chat
    
    result = await parser.parse("Hello")
    assert result is None

@pytest.mark.asyncio
async def test_parse_convert_request(mock_parser):
    parser, mock_model = mock_parser
    
    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    
    mock_part.function_call.name = "ConvertRequestTool"
    mock_part.function_call.args = {
        "query": "John",
        "action": "schedule",
        "time": "tomorrow"
    }
    
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    
    mock_chat = MagicMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)
    mock_model.start_chat.return_value = mock_chat
    
    result = await parser.parse("Schedule John for tomorrow")
    
    assert isinstance(result, ConvertRequestTool)
    assert result.query == "John"
    assert result.action == "schedule"
    assert result.time == "tomorrow"
