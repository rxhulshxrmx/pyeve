from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pyeve.types import Message


@dataclass
class Session:
    session_id: str
    history: list[Message] = field(default_factory=list)


class SessionStore(Protocol):
    async def load(self, session_id: str) -> Session | None: ...
    async def save(self, session: Session) -> None: ...


class DiskSessionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or Path(".pyeve/sessions")

    async def load(self, session_id: str) -> Session | None:
        path = self._base / session_id / "session.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Session(
            session_id=data["session_id"],
            history=[
                Message(
                    role=m["role"],
                    content=m["content"],
                    tool_call_id=m.get("tool_call_id"),
                    tool_name=m.get("tool_name"),
                )
                for m in data["history"]
            ],
        )

    async def save(self, session: Session) -> None:
        session_dir = self._base / session.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / "session.json"
        data = {
            "session_id": session.session_id,
            "history": [
                {
                    "role": m.role,
                    "content": m.content,
                    "tool_call_id": m.tool_call_id,
                    "tool_name": m.tool_name,
                }
                for m in session.history
            ],
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
