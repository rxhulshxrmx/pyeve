from __future__ import annotations

import json
from typing import AsyncIterator

from pyeve.types import (
    AgentConfig, DoneEvent, ErrorEvent, Message, StreamEvent,
    ToolCallEvent, ToolDefinition, TokenEvent,
)


class MistralAdapter:
    """Adapter for the Mistral SDK (pip install pyeve[mistral])."""

    def __init__(self) -> None:
        try:
            from mistralai import Mistral
            self._client = Mistral()
        except ImportError:
            raise ImportError(
                "MistralAdapter requires the mistralai package. "
                "Install it with: pip install pyeve[mistral]"
            )

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: AgentConfig,
    ) -> AsyncIterator[StreamEvent]:
        mistral_messages = [{"role": m.role, "content": m.content} for m in messages]
        mistral_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

        kwargs: dict = {
            "model": config.model,
            "messages": mistral_messages,
        }
        if mistral_tools:
            kwargs["tools"] = mistral_tools
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature

        async def _stream() -> AsyncIterator[StreamEvent]:
            try:
                full_text = ""
                tool_calls_accumulator: dict[int, dict] = {}

                async with self._client.chat.stream_async(**kwargs) as stream:
                    async for chunk in stream:
                        delta = chunk.data.choices[0].delta if chunk.data.choices else None
                        if delta is None:
                            continue
                        if delta.content:
                            full_text += delta.content
                            yield TokenEvent(text=delta.content)
                        if delta.tool_calls:
                            for idx, tc in enumerate(delta.tool_calls):
                                real_idx = getattr(tc, "index", idx)
                                if real_idx not in tool_calls_accumulator:
                                    tool_calls_accumulator[real_idx] = {
                                        "id": tc.id or "",
                                        "name": tc.function.name or "" if tc.function else "",
                                        "arguments": "",
                                    }
                                if tc.function and tc.function.arguments:
                                    tool_calls_accumulator[real_idx]["arguments"] += tc.function.arguments

                for tc in tool_calls_accumulator.values():
                    yield ToolCallEvent(
                        id=tc["id"],
                        name=tc["name"],
                        input=json.loads(tc["arguments"] or "{}"),
                    )

                yield DoneEvent(text=full_text)
            except Exception as e:
                yield ErrorEvent(message=str(e))

        return _stream()
