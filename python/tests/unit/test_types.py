from pyeve.types import (
    Message, ToolDefinition, AgentConfig, TokenEvent, ToolCallEvent,
    ToolResultEvent, DoneEvent, ErrorEvent, StreamEvent,
)
from pyeve.adapters.mock import MockAdapter


def test_message_fields():
    m = Message(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"
    assert m.tool_call_id is None
    assert m.tool_name is None


def test_tool_definition():
    td = ToolDefinition(
        name="get_weather",
        description="Get weather",
        input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
    )
    assert td.name == "get_weather"


def test_stream_events():
    assert TokenEvent(text="hi").type == "token"
    assert ToolCallEvent(id="1", name="get_weather", input={"city": "Berlin"}).type == "tool_call"
    assert ToolResultEvent(id="1", result={"temp": 72}).type == "tool_result"
    assert DoneEvent(text="done").type == "done"
    assert ErrorEvent(message="oops").type == "error"


def test_mock_adapter_satisfies_protocol():
    from pyeve.types import ModelAdapter
    adapter = MockAdapter(responses=["hello"])
    assert isinstance(adapter, ModelAdapter)
