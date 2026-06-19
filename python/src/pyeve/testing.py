from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pyeve.discover import discover_agent_config, discover_instructions, discover_tools
from pyeve.loop import run_agent_loop
from pyeve.session import DiskSessionStore, Session
from pyeve.types import ModelAdapter, StreamEvent, TokenEvent


@dataclass
class ChatResponse:
    text: str
    events: list[StreamEvent]


class AgentTestClient:
    """Full-stack test client that runs the agent loop without a real HTTP server."""

    def __init__(
        self,
        agent_dir: str = "./agent",
        adapter: ModelAdapter | None = None,
        sessions_dir: Path | None = None,
    ) -> None:
        self._agent_dir = Path(agent_dir)
        self._adapter = adapter
        self._store = DiskSessionStore(base_dir=sessions_dir)

    async def chat(self, message: str, session_id: str | None = None) -> ChatResponse:
        tools = discover_tools(self._agent_dir)
        instructions = discover_instructions(self._agent_dir)
        config = discover_agent_config(self._agent_dir)

        adapter = self._adapter or config.adapter
        sid = session_id or str(uuid.uuid4())
        session = await self._store.load(sid) or Session(session_id=sid)

        events: list[StreamEvent] = []
        text_parts: list[str] = []

        async for event in run_agent_loop(
            user_message=message,
            session=session,
            instructions=instructions,
            tools=tools,
            adapter=adapter,
            config=config,
        ):
            events.append(event)
            if isinstance(event, TokenEvent):
                text_parts.append(event.text)

        await self._store.save(session)
        return ChatResponse(text="".join(text_parts), events=events)


async def run_tool(execute_fn: Callable, **kwargs: Any) -> Any:
    """Call a tool's execute function directly, bypassing the agent loop."""
    return await execute_fn(**kwargs)
