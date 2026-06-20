import pytest
from pathlib import Path
from pyeve.session import Session, DiskSessionStore
from pyeve.types import Message


async def test_load_nonexistent_returns_none(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    assert await store.load("no-such-session") is None


async def test_save_and_load_roundtrip(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    session = Session(session_id="abc123")
    session.history.append(Message(role="user", content="hello"))
    session.history.append(Message(role="assistant", content="hi there"))

    await store.save(session)
    loaded = await store.load("abc123")

    assert loaded is not None
    assert loaded.session_id == "abc123"
    assert len(loaded.history) == 2
    assert loaded.history[0].role == "user"
    assert loaded.history[0].content == "hello"
    assert loaded.history[1].role == "assistant"


async def test_save_is_atomic(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    session = Session(session_id="xyz")
    await store.save(session)

    # no .tmp file left behind
    tmp_files = list(tmp_path.rglob("*.tmp"))
    assert tmp_files == []


async def test_save_with_tool_messages(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    session = Session(session_id="tool-test")
    session.history.append(
        Message(role="tool", content='{"temp": 72}', tool_call_id="call_1", tool_name="get_weather")
    )
    await store.save(session)
    loaded = await store.load("tool-test")

    assert loaded.history[0].tool_call_id == "call_1"
    assert loaded.history[0].tool_name == "get_weather"


async def test_save_and_load_tool_calls_roundtrip(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    session = Session(session_id="tc-roundtrip")
    session.history.append(Message(
        role="assistant",
        content="",
        tool_calls=[{"id": "tc1", "name": "search", "arguments": '{"query": "Paris"}'}],
    ))
    await store.save(session)
    loaded = await store.load("tc-roundtrip")

    assert loaded.history[0].tool_calls is not None
    assert loaded.history[0].tool_calls[0]["id"] == "tc1"
    assert loaded.history[0].tool_calls[0]["name"] == "search"


async def test_overwrite_existing_session(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    session = Session(session_id="overwrite")
    session.history.append(Message(role="user", content="first"))
    await store.save(session)

    session.history.append(Message(role="assistant", content="second"))
    await store.save(session)

    loaded = await store.load("overwrite")
    assert len(loaded.history) == 2
