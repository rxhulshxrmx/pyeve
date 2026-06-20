from __future__ import annotations

import json
from typing import AsyncIterator

from pyeve.types import (
    AgentConfig, DoneEvent, ErrorEvent, Message, StreamEvent,
    ToolCallEvent, ToolDefinition, TokenEvent,
)


def _to_openai_messages(messages: list[Message]) -> list[dict]:
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
            })
    return result


class SAPAICoreAdapter:
    """
    Adapter for SAP AI Core (pip install pyeve[sap]).

    Credentials from env vars:
        AICORE_CLIENT_ID, AICORE_CLIENT_SECRET, AICORE_AUTH_URL, AICORE_BASE_URL
    Or from ~/.aicore/config.json (aicore_sdk convention).

    Args:
        resource_group: SAP AI Core resource group (default: "default")
    """

    def __init__(self, resource_group: str = "default") -> None:
        self._resource_group = resource_group
        try:
            from gen_ai_hub.proxy.native.openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        except ImportError:
            raise ImportError(
                "SAPAICoreAdapter requires generative-ai-hub-sdk. "
                "Install it with: pip install pyeve[sap]"
            )

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: AgentConfig,
    ) -> AsyncIterator[StreamEvent]:
        kwargs: dict = {
            "model_name": config.model,
            "messages": _to_openai_messages(messages),
            "stream": True,
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
        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature

        client = self._client

        async def _stream() -> AsyncIterator[StreamEvent]:
            try:
                full_text = ""
                tool_calls_accumulator: dict[int, dict] = {}

                async for chunk in await client.chat.completions.create(**kwargs):
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    if delta.content:
                        full_text += delta.content
                        yield TokenEvent(text=delta.content)

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            fn = tc.function
                            if idx not in tool_calls_accumulator:
                                tool_calls_accumulator[idx] = {
                                    "id": tc.id or "",
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
