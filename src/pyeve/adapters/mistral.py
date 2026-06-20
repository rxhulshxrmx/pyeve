from __future__ import annotations

import json
from typing import AsyncIterator

from pyeve.types import (
    AgentConfig, DoneEvent, ErrorEvent, Message, StreamEvent,
    ToolCallEvent, ToolDefinition, TokenEvent,
)

_UNSET_TYPE_NAME = "Unset"


def _to_mistral_messages(messages: list[Message]) -> list[dict]:
    result: list[dict] = []
    for m in messages:
        if m.role in ("user", "system"):
            result.append({"role": m.role, "content": m.content})
        elif m.role == "assistant":
            msg: dict = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in m.tool_calls
                ]
            result.append(msg)
        elif m.role == "tool":
            result.append({
                "role": "tool",
                "content": m.content,
                "tool_call_id": m.tool_call_id,
                "name": m.tool_name,
            })
    return result


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
        kwargs: dict = {
            "model": config.model,
            "messages": _to_mistral_messages(messages),
        }
        if tools:
            kwargs["tools"] = [
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
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature

        client = self._client

        async def _stream() -> AsyncIterator[StreamEvent]:
            try:
                full_text = ""
                tool_calls_accumulator: dict[int, dict] = {}

                # stream_async is a coroutine returning an AsyncGenerator — await it.
                stream = await client.chat.stream_async(**kwargs)
                async for chunk in stream:
                    delta = chunk.data.choices[0].delta if chunk.data.choices else None
                    if delta is None:
                        continue

                    content = delta.content
                    if content and isinstance(content, str):
                        full_text += content
                        yield TokenEvent(text=content)

                    tc_list = delta.tool_calls
                    if tc_list is None or type(tc_list).__name__ == _UNSET_TYPE_NAME:
                        continue
                    if not isinstance(tc_list, list):
                        continue

                    for tc in tc_list:
                        idx = getattr(tc, "index", 0)
                        fn = getattr(tc, "function", None)
                        if idx not in tool_calls_accumulator:
                            tool_calls_accumulator[idx] = {
                                "id": getattr(tc, "id", "") or "",
                                "name": (fn.name or "") if fn else "",
                                "arguments": "",
                            }
                        if fn and fn.arguments:
                            tool_calls_accumulator[idx]["arguments"] += fn.arguments

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
