from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal, Protocol, runtime_checkable


@dataclass
class Message:
    role: Literal["user", "assistant", "tool", "system"]
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict


@dataclass
class AgentConfig:
    model: str
    adapter: ModelAdapter
    max_tokens: int = 4096
    temperature: float | None = None


@dataclass
class TokenEvent:
    text: str
    type: Literal["token"] = field(default="token", init=False)


@dataclass
class ToolCallEvent:
    id: str
    name: str
    input: dict
    type: Literal["tool_call"] = field(default="tool_call", init=False)


@dataclass
class ToolResultEvent:
    id: str
    result: Any
    type: Literal["tool_result"] = field(default="tool_result", init=False)


@dataclass
class DoneEvent:
    text: str
    type: Literal["done"] = field(default="done", init=False)


@dataclass
class ErrorEvent:
    message: str
    type: Literal["error"] = field(default="error", init=False)


StreamEvent = TokenEvent | ToolCallEvent | ToolResultEvent | DoneEvent | ErrorEvent


@runtime_checkable
class ModelAdapter(Protocol):
    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: AgentConfig,
    ) -> AsyncIterator[StreamEvent]: ...
