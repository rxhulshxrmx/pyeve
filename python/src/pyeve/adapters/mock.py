from __future__ import annotations

from typing import AsyncIterator

from pyeve.types import AgentConfig, DoneEvent, Message, ModelAdapter, StreamEvent, ToolDefinition, TokenEvent


class MockAdapter:
    """Plays back scripted responses in order. No real model calls."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: AgentConfig,
    ) -> AsyncIterator[StreamEvent]:
        if self._index >= len(self._responses):
            raise ValueError(
                f"MockAdapter exhausted: called {self._index + 1} times but only "
                f"{len(self._responses)} response(s) provided"
            )
        text = self._responses[self._index]
        self._index += 1

        async def _stream():
            yield TokenEvent(text=text)
            yield DoneEvent(text=text)

        return _stream()
