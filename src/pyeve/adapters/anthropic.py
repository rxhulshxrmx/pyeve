from __future__ import annotations

from typing import AsyncIterator

from pyeve.types import (
    AgentConfig, DoneEvent, ErrorEvent, Message, StreamEvent,
    ToolCallEvent, ToolDefinition, TokenEvent,
)


class AnthropicAdapter:
    """Adapter for the Anthropic SDK (pip install pyeve[anthropic])."""

    def __init__(self) -> None:
        try:
            import anthropic as _anthropic
            self._client = _anthropic.AsyncAnthropic()
        except ImportError:
            raise ImportError(
                "AnthropicAdapter requires the anthropic package. "
                "Install it with: pip install pyeve[anthropic]"
            )

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: AgentConfig,
    ) -> AsyncIterator[StreamEvent]:
        anthropic_messages = _to_anthropic_messages(messages)
        anthropic_tools = [_to_anthropic_tool(t) for t in tools]

        kwargs: dict = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "messages": anthropic_messages,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature

        async def _stream() -> AsyncIterator[StreamEvent]:
            try:
                async with self._client.messages.stream(**kwargs) as stream:
                    full_text = ""
                    async for chunk in stream:
                        if hasattr(chunk, "type"):
                            if chunk.type == "content_block_delta":
                                delta = chunk.delta
                                if hasattr(delta, "text"):
                                    full_text += delta.text
                                    yield TokenEvent(text=delta.text)
                            elif chunk.type == "message_stop":
                                break

                    final = await stream.get_final_message()
                    for block in final.content:
                        if block.type == "tool_use":
                            yield ToolCallEvent(
                                id=block.id,
                                name=block.name,
                                input=block.input,
                            )

                    yield DoneEvent(text=full_text)
            except Exception as e:
                yield ErrorEvent(message=str(e))

        return _stream()


def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
    result = []
    for m in messages:
        if m.role == "system":
            continue
        if m.role == "tool":
            result.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}],
            })
        else:
            result.append({"role": m.role, "content": m.content})
    return result


def _to_anthropic_tool(t: ToolDefinition) -> dict:
    return {
        "name": t.name,
        "description": t.description,
        "input_schema": t.input_schema,
    }
