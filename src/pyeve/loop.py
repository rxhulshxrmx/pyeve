from __future__ import annotations

from typing import AsyncIterator, Callable

from pyeve.session import Session
from pyeve.types import (
    AgentConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    ModelAdapter,
    StreamEvent,
    TokenEvent,
    ToolCallEvent,
    ToolDefinition,
    ToolResultEvent,
)


async def run_agent_loop(
    *,
    user_message: str,
    session: Session,
    instructions: str,
    tools: dict[str, tuple[ToolDefinition, Callable]],
    adapter: ModelAdapter,
    config: AgentConfig,
) -> AsyncIterator[StreamEvent]:
    session.history.append(Message(role="user", content=user_message))
    tool_defs = [td for td, _ in tools.values()]

    while True:
        full_text = ""
        tool_calls: list[ToolCallEvent] = []

        system_message = Message(role="system", content=instructions)
        messages = [system_message, *session.history] if instructions else list(session.history)

        async for event in await adapter.complete(messages, tool_defs, config):
            if isinstance(event, TokenEvent):
                full_text += event.text
                yield event
            elif isinstance(event, ToolCallEvent):
                tool_calls.append(event)
                yield event
            elif isinstance(event, DoneEvent):
                break
            elif isinstance(event, ErrorEvent):
                yield event
                return

        session.history.append(Message(role="assistant", content=full_text))

        if not tool_calls:
            yield DoneEvent(text=full_text)
            return

        for call in tool_calls:
            if call.name not in tools:
                yield ErrorEvent(message=f"Unknown tool: {call.name}")
                return

            _, execute_fn = tools[call.name]
            result = await execute_fn(**call.input)

            yield ToolResultEvent(id=call.id, result=result)

            session.history.append(
                Message(
                    role="tool",
                    content=str(result),
                    tool_call_id=call.id,
                    tool_name=call.name,
                )
            )
