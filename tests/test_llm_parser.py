import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from src.llm_client import LLMParser
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
    ExportQueryTool,
)


@pytest.fixture
def mock_parser():
    with patch("src.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        parser = LLMParser()
        yield parser, mock_client


@pytest.mark.asyncio
async def test_parse_add_job(mock_parser):
    parser, mock_client = mock_parser

    # Setup OpenAI response mock
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "AddJobTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "customer_name": "John Doe",
            "description": "Fix the leaky faucet",
            "price": 50.0,
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse(
        "Add a job for John Doe to fix the leaky faucet for $50"
    )

    assert isinstance(result, AddJobTool)
    assert result.customer_name == "John Doe"
    assert result.description == "Fix the leaky faucet"
    assert result.price == 50.0


@pytest.mark.asyncio
async def test_parse_add_lead(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "AddLeadTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "name": "John Doe",
            "phone": "086123123",
            "details": "Interested in quote",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("add lead: john, 086123123")
    assert isinstance(result, AddLeadTool)
    assert result.name == "John Doe"
    assert result.details == "Interested in quote"


@pytest.mark.asyncio
async def test_parse_add_request_explicit(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "AddRequestTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "description": "john wanted his windows cleaned tomorrow, 12 windows",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse(
        "add request: john wanted his windows cleaned tomorrow, 12 windows"
    )
    assert isinstance(result, AddRequestTool)
    assert "windows cleaned" in result.description


@pytest.mark.asyncio
async def test_parse_schedule_with_time(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "ScheduleJobTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "customer_query": "John",
            "time": "tomorrow at 2pm",
            "iso_time": "2026-01-14T14:00:00Z",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse(
        "Schedule John for tomorrow at 2pm", system_time="2026-01-13T10:00:00Z"
    )

    assert isinstance(result, ScheduleJobTool)
    assert result.customer_query == "John"
    assert result.time == "tomorrow at 2pm"
    assert result.iso_time == "2026-01-14T14:00:00Z"


@pytest.mark.asyncio
async def test_parse_search(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "SearchTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "query": "John",
            "entity_type": "job",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("find jobs for John")
    assert isinstance(result, SearchTool)
    assert result.query == "John"
    assert result.entity_type == "job"


@pytest.mark.asyncio
async def test_parse_edit_customer(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "EditCustomerTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "query": "John",
            "phone": "0860000000",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("update phone for John to 0860000000")
    assert isinstance(result, EditCustomerTool)
    assert result.query == "John"
    assert result.phone == "0860000000"


@pytest.mark.asyncio
async def test_parse_update_settings(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "UpdateSettingsTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "setting_key": "language",
            "setting_value": "Spanish",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("change language to Spanish")
    assert isinstance(result, UpdateSettingsTool)
    assert result.setting_key == "language"
    assert result.setting_value == "Spanish"


@pytest.mark.asyncio
async def test_parse_convert_request(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "ConvertRequestTool"
    mock_tool_call.function.arguments = json.dumps(
        {
            "query": "John",
            "action": "complete",
        }
    )

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("mark John as completed")
    assert isinstance(result, ConvertRequestTool)
    assert result.query == "John"
    assert result.action == "complete"


@pytest.mark.asyncio
async def test_parse_undo_cancel(mock_parser):
    parser, _ = mock_parser
    assert await parser.parse("Undo") is None
    assert await parser.parse("CANCEL") is None


@pytest.mark.asyncio
async def test_parse_help(mock_parser):
    parser, _ = mock_parser
    assert isinstance(await parser.parse("help"), HelpTool)


@pytest.mark.asyncio
async def test_parse_no_tool_call(mock_parser):
    parser, mock_client = mock_parser
    mock_message = MagicMock(tool_calls=None)
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    assert await parser.parse("Hello") is None


@pytest.mark.asyncio
async def test_parse_get_pipeline(mock_parser):
    parser, mock_client = mock_parser

    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "GetPipelineTool"
    mock_tool_call.function.arguments = "{}"

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await parser.parse("how is our pipeline doing?")
    assert isinstance(result, GetPipelineTool)


@pytest.mark.asyncio
async def test_parse_retry_success(mock_parser):
    parser, mock_client = mock_parser

    # First call returns no tool calls
    mock_message_1 = MagicMock(tool_calls=None, content="I'm not sure what you mean.")
    mock_response_1 = MagicMock(choices=[MagicMock(message=mock_message_1)])

    # Second call returns a tool call
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "AddJobTool"
    mock_tool_call.function.arguments = json.dumps(
        {"customer_name": "Retry John", "description": "Fix faucet", "price": 50.0}
    )
    mock_message_2 = MagicMock(tool_calls=[mock_tool_call])
    mock_response_2 = MagicMock(choices=[MagicMock(message=mock_message_2)])

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    result = await parser.parse("fix faucet for John $50")
    
    # Verify it retried
    assert mock_client.chat.completions.create.call_count == 2
    assert isinstance(result, AddJobTool)
    assert result.customer_name == "Retry John"


@pytest.mark.asyncio
async def test_parse_retry_failure_returns_none(mock_parser):
    parser, mock_client = mock_parser

    # Both calls return no tool calls
    mock_message_1 = MagicMock(tool_calls=None, content="Initial response.")
    mock_response_1 = MagicMock(choices=[MagicMock(message=mock_message_1)])

    mock_message_2 = MagicMock(tool_calls=None, content="Still no idea.")
    mock_response_2 = MagicMock(choices=[MagicMock(message=mock_message_2)])

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    result = await parser.parse("something vague")
    
    assert mock_client.chat.completions.create.call_count == 2
    assert result is None


@pytest.mark.asyncio
async def test_parse_settings_retry_success(mock_parser):
    parser, mock_client = mock_parser

    # First call returns no tool calls
    mock_message_1 = MagicMock(tool_calls=None, content="What settings?")
    mock_response_1 = MagicMock(choices=[MagicMock(message=mock_message_1)])

    # Second call returns a tool call
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "AddServiceTool"
    mock_tool_call.function.arguments = json.dumps(
        {"name": "New Service", "price": 100.0}
    )
    mock_message_2 = MagicMock(tool_calls=[mock_tool_call])
    mock_response_2 = MagicMock(choices=[MagicMock(message=mock_message_2)])

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    result = await parser.parse_settings("add service new service 100")
    
    assert mock_client.chat.completions.create.call_count == 2
    assert isinstance(result, AddServiceTool)
    assert result.name == "New Service"


@pytest.mark.asyncio
async def test_parse_retry_json_error(mock_parser):
    parser, mock_client = mock_parser

    # First call returns invalid JSON
    mock_tool_call_bad = MagicMock()
    mock_tool_call_bad.function.name = "AddJobTool"
    mock_tool_call_bad.function.arguments = "{ invalid json }"
    
    mock_message_1 = MagicMock()
    mock_message_1.tool_calls = [mock_tool_call_bad]
    mock_message_1.content = "Some content"
    mock_response_1 = MagicMock(choices=[MagicMock(message=mock_message_1)])

    # Second call returns valid tool call
    mock_tool_call_good = MagicMock()
    mock_tool_call_good.function.name = "AddJobTool"
    mock_tool_call_good.function.arguments = json.dumps(
        {"customer_name": "Retry John", "description": "Fix faucet", "price": 50.0}
    )
    mock_message_2 = MagicMock(tool_calls=[mock_tool_call_good])
    mock_response_2 = MagicMock(choices=[MagicMock(message=mock_message_2)])

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    result = await parser.parse("fix faucet for John $50")
    
    assert mock_client.chat.completions.create.call_count == 2
    assert isinstance(result, AddJobTool)
    assert result.customer_name == "Retry John"


@pytest.mark.asyncio
async def test_parse_retry_validation_error(mock_parser):
    parser, mock_client = mock_parser

    # First call returns invalid Pydantic model
    mock_tool_call_bad = MagicMock()
    mock_tool_call_bad.function.name = "AddJobTool"
    mock_tool_call_bad.function.arguments = json.dumps(
        {"customer_name": "John", "price": "not a number"} # price expects float
    )
    
    mock_message_1 = MagicMock()
    mock_message_1.tool_calls = [mock_tool_call_bad]
    mock_message_1.content = None
    mock_response_1 = MagicMock(choices=[MagicMock(message=mock_message_1)])

    # Second call returns valid tool call
    mock_tool_call_good = MagicMock()
    mock_tool_call_good.function.name = "AddJobTool"
    mock_tool_call_good.function.arguments = json.dumps(
        {"customer_name": "John", "price": 50.0}
    )
    mock_message_2 = MagicMock(tool_calls=[mock_tool_call_good])
    mock_response_2 = MagicMock(choices=[MagicMock(message=mock_message_2)])

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    result = await parser.parse("fix faucet for John $50")
    
    assert mock_client.chat.completions.create.call_count == 2
    assert isinstance(result, AddJobTool)
    assert result.price == 50.0


@pytest.mark.asyncio
async def test_parse_data_management_retry(mock_parser):
    parser, mock_client = mock_parser

    # First call returns no tool calls
    mock_message_1 = MagicMock(tool_calls=None, content="I'm not sure.")
    mock_response_1 = MagicMock(choices=[MagicMock(message=mock_message_1)])

    # Second call returns valid export tool
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "ExportQueryTool"
    mock_tool_call.function.arguments = json.dumps(
        {"query": "all customers"}
    )
    mock_message_2 = MagicMock(tool_calls=[mock_tool_call])
    mock_response_2 = MagicMock(choices=[MagicMock(message=mock_message_2)])

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    result = await parser.parse_data_management("export everything")
    
    assert mock_client.chat.completions.create.call_count == 2
    assert isinstance(result, ExportQueryTool)
    assert result.query == "all customers"
