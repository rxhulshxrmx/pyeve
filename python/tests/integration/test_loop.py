import pytest
from pyeve.loop import run_agent_loop
from pyeve.session import Session
from pyeve.types import (
    AgentConfig, DoneEvent, ErrorEvent, ToolCallEvent,
    ToolDefinition, TokenEvent, ToolResultEvent,
)
from pyeve.adapters.mock import MockAdapter


def _make_config(adapter) -> AgentConfig:
    return AgentConfig(model="mock", adapter=adapter)


def _make_tools():
    td = ToolDefinition(
        name="get_weather",
        description="Get weather",
        input_schema={"properties": {"city": {"type": "string"}}},
    )

    async def execute(city: str) -> dict:
        return {"city": city, "condition": "Sunny"}

    return {"get_weather": (td, execute)}


async def test_simple_response():
    adapter = MockAdapter(responses=["The weather is sunny."])
    session = Session(session_id="s1")
    config = _make_config(adapter)

    events = []
    async for event in run_agent_loop(
        user_message="What's the weather?",
        session=session,
        instructions="You are a weather bot.",
        tools={},
        adapter=adapter,
        config=config,
    ):
        events.append(event)

    assert any(isinstance(e, TokenEvent) for e in events)
    assert any(isinstance(e, DoneEvent) for e in events)
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.text == "The weather is sunny."


async def test_user_message_appended_to_history():
    adapter = MockAdapter(responses=["hi"])
    session = Session(session_id="s2")
    config = _make_config(adapter)

    async for _ in run_agent_loop(
        user_message="hello",
        session=session,
        instructions="",
        tools={},
        adapter=adapter,
        config=config,
    ):
        pass

    assert session.history[0].role == "user"
    assert session.history[0].content == "hello"
    assert session.history[1].role == "assistant"
    assert session.history[1].content == "hi"


async def test_tool_call_executes_and_loops():
    """Adapter first returns a tool call, then a final response."""
    call_count = 0

    class TwoTurnAdapter:
        async def complete(self, messages, tools, config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async def _first():
                    yield ToolCallEvent(id="c1", name="get_weather", input={"city": "Berlin"})
                    yield DoneEvent(text="")
                return _first()
            else:
                async def _second():
                    yield TokenEvent(text="It's sunny in Berlin.")
                    yield DoneEvent(text="It's sunny in Berlin.")
                return _second()

    session = Session(session_id="s3")
    adapter = TwoTurnAdapter()
    config = AgentConfig(model="mock", adapter=adapter)

    events = []
    async for event in run_agent_loop(
        user_message="Weather in Berlin?",
        session=session,
        instructions="",
        tools=_make_tools(),
        adapter=adapter,
        config=config,
    ):
        events.append(event)

    assert call_count == 2
    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].result["city"] == "Berlin"

    done = next(e for e in events if isinstance(e, DoneEvent))
    assert "sunny" in done.text.lower()


async def test_unknown_tool_yields_error():
    class BadToolAdapter:
        async def complete(self, messages, tools, config):
            async def _stream():
                yield ToolCallEvent(id="c1", name="nonexistent", input={})
                yield DoneEvent(text="")
            return _stream()

    session = Session(session_id="s4")
    adapter = BadToolAdapter()
    config = AgentConfig(model="mock", adapter=adapter)

    events = []
    async for event in run_agent_loop(
        user_message="test",
        session=session,
        instructions="",
        tools={},
        adapter=adapter,
        config=config,
    ):
        events.append(event)

    assert any(isinstance(e, ErrorEvent) for e in events)
    error = next(e for e in events if isinstance(e, ErrorEvent))
    assert "nonexistent" in error.message
