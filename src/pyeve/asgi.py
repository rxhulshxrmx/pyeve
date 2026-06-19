from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Callable

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_session_id(session_id: str) -> bool:
    return bool(_SESSION_ID_RE.fullmatch(session_id))

from pyeve.discover import discover_agent_config, discover_instructions, discover_tools
from pyeve.loop import run_agent_loop
from pyeve.session import DiskSessionStore, Session
from pyeve.types import DoneEvent, ErrorEvent, TokenEvent, ToolCallEvent, ToolResultEvent


def agent(agent_dir: str = "./agent", sessions_dir: Path | None = None) -> Callable:
    """Return an ASGI callable that serves the agent at the given directory."""
    dir_path = Path(agent_dir).resolve()
    store = DiskSessionStore(base_dir=sessions_dir)

    async def app(scope, receive, send) -> None:
        if scope["type"] != "http":
            return

        method: str = scope["method"]
        path: str = scope["path"]

        if method == "POST" and path == "/chat":
            await _handle_chat(scope, receive, send, dir_path, store)
        elif method == "GET" and path.startswith("/sessions/"):
            session_id = path.removeprefix("/sessions/").strip("/")
            if not _validate_session_id(session_id):
                await _send_response(send, 400, b"Invalid session_id", "text/plain")
                return
            await _handle_get_session(send, session_id, store)
        elif method == "DELETE" and path.startswith("/sessions/"):
            session_id = path.removeprefix("/sessions/").strip("/")
            if not _validate_session_id(session_id):
                await _send_response(send, 400, b"Invalid session_id", "text/plain")
                return
            await _handle_delete_session(send, session_id, store)
        else:
            await _send_response(send, 404, b"Not found", "text/plain")

    return app


async def _handle_chat(scope, receive, send, agent_dir: Path, store: DiskSessionStore) -> None:
    body = await _read_body(receive)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        await _send_response(send, 400, b"Invalid JSON", "text/plain")
        return

    user_message: str = data.get("message", "")
    raw_session_id = data.get("session_id")
    if raw_session_id is not None and not _validate_session_id(str(raw_session_id)):
        await _send_response(send, 400, b"Invalid session_id", "text/plain")
        return
    session_id: str = raw_session_id or str(uuid.uuid4())

    if not user_message:
        await _send_response(send, 400, b"message is required", "text/plain")
        return

    try:
        tools = discover_tools(agent_dir)
        instructions = discover_instructions(agent_dir)
        config = discover_agent_config(agent_dir)
    except Exception as e:
        await _send_response(send, 500, str(e).encode(), "text/plain")
        return

    session = await store.load(session_id) or Session(session_id=session_id)

    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"text/event-stream"],
            [b"cache-control", b"no-cache"],
            [b"x-session-id", session_id.encode()],
        ],
    })

    async for event in run_agent_loop(
        user_message=user_message,
        session=session,
        instructions=instructions,
        tools=tools,
        adapter=config.adapter,
        config=config,
    ):
        payload = _event_to_dict(event)
        chunk = f"data: {json.dumps(payload)}\n\n".encode()
        await send({"type": "http.response.body", "body": chunk, "more_body": True})

    await store.save(session)
    await send({"type": "http.response.body", "body": b"", "more_body": False})


async def _handle_get_session(send, session_id: str, store: DiskSessionStore) -> None:
    session = await store.load(session_id)
    if session is None:
        await _send_response(send, 404, b"Session not found", "text/plain")
        return
    body = json.dumps({
        "session_id": session.session_id,
        "history": [
            {"role": m.role, "content": m.content,
             "tool_call_id": m.tool_call_id, "tool_name": m.tool_name}
            for m in session.history
        ],
    }).encode()
    await _send_response(send, 200, body, "application/json")


async def _handle_delete_session(send, session_id: str, store: DiskSessionStore) -> None:
    await store.delete(session_id)
    await _send_response(send, 204, b"", "text/plain")


async def _read_body(receive) -> bytes:
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    return body


async def _send_response(send, status: int, body: bytes, content_type: str) -> None:
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", content_type.encode()]],
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})


def _event_to_dict(event) -> dict:
    if isinstance(event, TokenEvent):
        return {"type": "token", "text": event.text}
    if isinstance(event, ToolCallEvent):
        return {"type": "tool_call", "id": event.id, "name": event.name, "input": event.input}
    if isinstance(event, ToolResultEvent):
        return {"type": "tool_result", "id": event.id, "result": event.result}
    if isinstance(event, DoneEvent):
        return {"type": "done", "text": event.text}
    if isinstance(event, ErrorEvent):
        return {"type": "error", "message": event.message}
    return {"type": "unknown"}
