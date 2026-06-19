# pyeve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pyeve` — a filesystem-first Python framework for durable AI agents, installable via `pip install pyeve`.

**Architecture:** pyeve discovers `agent/tools/*.py` files at startup, introspects their signatures and docstrings to build tool definitions, runs a durable agentic loop that streams events, and exposes the whole thing as a standard ASGI callable. The filesystem is the authoring interface — no decorators, no registration, no imports of pyeve in tool files.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest + pytest-asyncio, httpx (ASGI testing), watchfiles (dev server), uvicorn (standalone runner), hatchling (build)

---

## File Map

```
python/
├── pyproject.toml                        # MODIFY: add deps, extras, pytest config
├── src/pyeve/
│   ├── __init__.py                       # MODIFY: export agent(), define_agent()
│   ├── types.py                          # CREATE: all shared types & protocols
│   ├── discover.py                       # CREATE: filesystem scanner
│   ├── session.py                        # CREATE: Session, DiskSessionStore
│   ├── loop.py                           # CREATE: agent loop
│   ├── asgi.py                           # CREATE: agent() ASGI callable
│   ├── testing.py                        # CREATE: run_tool, AgentTestClient
│   ├── cli.py                            # MODIFY: pyeve init, pyeve dev
│   └── adapters/
│       ├── __init__.py                   # CREATE: empty
│       ├── mock.py                       # CREATE: MockAdapter (for TDD)
│       ├── anthropic.py                  # CREATE: AnthropicAdapter
│       ├── openai.py                     # CREATE: OpenAIAdapter
│       └── sap.py                        # CREATE: SAPAICoreAdapter
└── tests/
    ├── conftest.py                       # CREATE: shared fixtures
    ├── fixtures/weather/agent/
    │   ├── instructions.md               # CREATE: test agent instructions
    │   ├── agent.py                      # CREATE: test agent config
    │   └── tools/get_weather.py          # CREATE: test tool
    ├── unit/
    │   ├── test_discover.py              # CREATE: tool discovery tests
    │   └── test_session.py              # CREATE: session store tests
    └── integration/
        ├── test_loop.py                  # CREATE: agent loop tests
        └── test_asgi.py                  # CREATE: HTTP endpoint tests
```

---

## Task 1: Project Setup

**Files:**
- Modify: `python/pyproject.toml`
- Create: `python/tests/conftest.py`
- Create: `python/tests/fixtures/weather/agent/instructions.md`
- Create: `python/tests/fixtures/weather/agent/tools/get_weather.py`

- [ ] **Step 1: Update pyproject.toml with dependencies, extras, and pytest config**

Replace the contents of `python/pyproject.toml` with:

```toml
[project]
name = "pyeve"
version = "0.0.1"
description = "Filesystem-first framework for durable backend AI agents in Python"
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.11"
keywords = ["ai", "agents", "llm", "framework", "durable"]
classifiers = [
    "Development Status :: 2 - Pre-Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
]
dependencies = [
    "pydantic>=2.0",
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
openai = ["openai>=1.0"]
sap = ["generative-ai-hub-sdk>=4.0"]
litellm = ["litellm>=1.0"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "watchfiles>=0.24",
    "uvicorn>=0.30",
    "anthropic>=0.40",
    "openai>=1.0",
]

[project.urls]
Homepage = "https://github.com/vercel/eve"
Documentation = "https://beta.eve.dev/docs"
Repository = "https://github.com/vercel/eve"

[project.scripts]
pyeve = "pyeve.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pyeve"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.hatch.envs.default]
features = ["dev"]
```

- [ ] **Step 2: Install dependencies**

```bash
cd python && uv sync --extra dev
```

Expected: packages install, `.venv/` created.

- [ ] **Step 3: Create test fixtures directory**

```bash
mkdir -p python/tests/fixtures/weather/agent/tools
mkdir -p python/tests/unit
mkdir -p python/tests/integration
```

- [ ] **Step 4: Create weather agent fixture — instructions**

Create `python/tests/fixtures/weather/agent/instructions.md`:

```markdown
You are a helpful weather assistant. Use the get_weather tool to answer questions about the weather.
```

- [ ] **Step 5: Create weather agent fixture — tool**

Create `python/tests/fixtures/weather/agent/tools/get_weather.py`:

```python
async def execute(city: str) -> dict:
    """Return mock weather data for a city."""
    return {"city": city, "condition": "Sunny", "temp_f": 72}
```

- [ ] **Step 6: Create conftest.py**

Create `python/tests/conftest.py`:

```python
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def weather_agent_dir() -> Path:
    return FIXTURES_DIR / "weather" / "agent"
```

- [ ] **Step 7: Verify setup runs**

```bash
cd python && uv run pytest --collect-only
```

Expected: `no tests ran`, no errors.

- [ ] **Step 8: Commit**

```bash
git add python/ && git commit -s -m "chore(pyeve): project setup — deps, fixtures, pytest config"
```

---

## Task 2: Core Types

**Files:**
- Create: `python/src/pyeve/types.py`
- Create: `python/tests/unit/test_types.py`

- [ ] **Step 1: Write failing test**

Create `python/tests/unit/test_types.py`:

```python
from pyeve.types import (
    Message, ToolDefinition, AgentConfig, TokenEvent, ToolCallEvent,
    ToolResultEvent, DoneEvent, ErrorEvent, StreamEvent,
)
from pyeve.adapters.mock import MockAdapter


def test_message_fields():
    m = Message(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"
    assert m.tool_call_id is None
    assert m.tool_name is None


def test_tool_definition():
    td = ToolDefinition(
        name="get_weather",
        description="Get weather",
        input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
    )
    assert td.name == "get_weather"


def test_stream_events():
    assert TokenEvent(text="hi").type == "token"
    assert ToolCallEvent(id="1", name="get_weather", input={"city": "Berlin"}).type == "tool_call"
    assert ToolResultEvent(id="1", result={"temp": 72}).type == "tool_result"
    assert DoneEvent(text="done").type == "done"
    assert ErrorEvent(message="oops").type == "error"


def test_mock_adapter_satisfies_protocol():
    from pyeve.types import ModelAdapter
    adapter = MockAdapter(responses=["hello"])
    assert isinstance(adapter, ModelAdapter)
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd python && uv run pytest tests/unit/test_types.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyeve.types'`

- [ ] **Step 3: Create types.py**

Create `python/src/pyeve/types.py`:

```python
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
```

- [ ] **Step 4: Create adapters/__init__.py**

Create `python/src/pyeve/adapters/__init__.py`:

```python
```

- [ ] **Step 5: Create MockAdapter (needed by test_types)**

Create `python/src/pyeve/adapters/mock.py`:

```python
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
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/unit/test_types.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): core types, ModelAdapter protocol, MockAdapter"
```

---

## Task 3: Tool Discovery

**Files:**
- Create: `python/src/pyeve/discover.py`
- Create: `python/tests/unit/test_discover.py`

- [ ] **Step 1: Write failing tests**

Create `python/tests/unit/test_discover.py`:

```python
import pytest
from pathlib import Path
from pyeve.discover import discover_tools, discover_instructions


def test_discover_tools_returns_tool_definition(weather_agent_dir):
    tools = discover_tools(weather_agent_dir)
    assert "get_weather" in tools
    td, fn = tools["get_weather"]
    assert td.name == "get_weather"
    assert td.description == "Return mock weather data for a city."
    assert td.input_schema["properties"]["city"]["type"] == "string"


async def test_discover_tools_execute_is_callable(weather_agent_dir):
    tools = discover_tools(weather_agent_dir)
    _, fn = tools["get_weather"]
    result = await fn(city="Berlin")
    assert result["city"] == "Berlin"
    assert result["condition"] == "Sunny"


def test_discover_instructions(weather_agent_dir):
    instructions = discover_instructions(weather_agent_dir)
    assert "weather" in instructions.lower()


def test_discover_tools_missing_docstring(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "bad_tool.py").write_text(
        "async def execute(city: str) -> dict:\n    return {}\n"
    )
    with pytest.raises(ValueError, match="docstring"):
        discover_tools(tmp_path)


def test_discover_tools_missing_type_hint(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "bad_tool.py").write_text(
        'async def execute(city) -> dict:\n    """Get weather."""\n    return {}\n'
    )
    with pytest.raises(ValueError, match="type hint"):
        discover_tools(tmp_path)


def test_discover_tools_not_async(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "bad_tool.py").write_text(
        'def execute(city: str) -> dict:\n    """Get weather."""\n    return {}\n'
    )
    with pytest.raises(ValueError, match="async"):
        discover_tools(tmp_path)


def test_discover_tools_empty_dir(tmp_path):
    (tmp_path / "tools").mkdir()
    assert discover_tools(tmp_path) == {}


def test_discover_instructions_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_instructions(tmp_path)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd python && uv run pytest tests/unit/test_discover.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyeve.discover'`

- [ ] **Step 3: Implement discover.py**

Create `python/src/pyeve/discover.py`:

```python
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable

from pydantic import create_model

from pyeve.types import AgentConfig, ToolDefinition


def discover_tools(agent_dir: Path) -> dict[str, tuple[ToolDefinition, Callable]]:
    """Scan agent_dir/tools/*.py and return {name: (ToolDefinition, execute_fn)}."""
    tools_dir = agent_dir / "tools"
    if not tools_dir.exists():
        return {}

    result: dict[str, tuple[ToolDefinition, Callable]] = {}
    for path in sorted(tools_dir.glob("*.py")):
        name = path.stem
        module = _load_module(f"_pyeve_tool_{name}", path)

        execute = getattr(module, "execute", None)
        if execute is None or not inspect.iscoroutinefunction(execute):
            raise ValueError(
                f"{path}: must define an async `execute` function"
            )

        doc = inspect.getdoc(execute)
        if not doc:
            raise ValueError(
                f"{path}: `execute` must have a docstring (used as tool description)"
            )

        sig = inspect.signature(execute)
        input_schema = _sig_to_json_schema(sig, path)

        result[name] = (ToolDefinition(name=name, description=doc, input_schema=input_schema), execute)

    return result


def discover_instructions(agent_dir: Path) -> str:
    """Read agent_dir/instructions.md and return its contents."""
    path = agent_dir / "instructions.md"
    if not path.exists():
        raise FileNotFoundError(f"instructions.md not found in {agent_dir}")
    return path.read_text()


def discover_agent_config(agent_dir: Path) -> AgentConfig:
    """Import agent_dir/agent.py and return the `agent` variable (an AgentConfig)."""
    path = agent_dir / "agent.py"
    if not path.exists():
        raise FileNotFoundError(f"agent.py not found in {agent_dir}")
    module = _load_module("_pyeve_agent_config", path)
    config = getattr(module, "agent", None)
    if config is None or not isinstance(config, AgentConfig):
        raise ValueError(f"{path}: must export `agent = define_agent(...)`")
    return config


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sig_to_json_schema(sig: inspect.Signature, path: Path) -> dict:
    fields: dict[str, Any] = {}
    for param_name, param in sig.parameters.items():
        if param.annotation is inspect.Parameter.empty:
            raise ValueError(
                f"{path}: parameter `{param_name}` must have a type hint"
            )
        if param.default is inspect.Parameter.empty:
            fields[param_name] = (param.annotation, ...)
        else:
            fields[param_name] = (param.annotation, param.default)

    model = create_model("_InputModel", **fields)
    schema = model.model_json_schema()
    schema.pop("title", None)
    return schema
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/unit/test_discover.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): tool discovery from filesystem"
```

---

## Task 4: Session & DiskSessionStore

**Files:**
- Create: `python/src/pyeve/session.py`
- Create: `python/tests/unit/test_session.py`

- [ ] **Step 1: Write failing tests**

Create `python/tests/unit/test_session.py`:

```python
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


async def test_overwrite_existing_session(tmp_path):
    store = DiskSessionStore(base_dir=tmp_path)
    session = Session(session_id="overwrite")
    session.history.append(Message(role="user", content="first"))
    await store.save(session)

    session.history.append(Message(role="assistant", content="second"))
    await store.save(session)

    loaded = await store.load("overwrite")
    assert len(loaded.history) == 2
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd python && uv run pytest tests/unit/test_session.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyeve.session'`

- [ ] **Step 3: Implement session.py**

Create `python/src/pyeve/session.py`:

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/unit/test_session.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): Session and DiskSessionStore with atomic writes"
```

---

## Task 5: Agent Loop

**Files:**
- Create: `python/src/pyeve/loop.py`
- Create: `python/tests/integration/test_loop.py`

- [ ] **Step 1: Write failing tests**

Create `python/tests/integration/test_loop.py`:

```python
import pytest
from pyeve.loop import run_agent_loop
from pyeve.session import Session
from pyeve.types import (
    AgentConfig, DoneEvent, ErrorEvent, ToolCallEvent,
    ToolDefinition, TokenEvent, ToolResultEvent,
)
from pyeve.adapters.mock import MockAdapter


def _make_config(adapter) -> AgentConfig:
    return AgentConfig(model="mock", adapter=adapter)


def _make_tools():
    td = ToolDefinition(
        name="get_weather",
        description="Get weather",
        input_schema={"properties": {"city": {"type": "string"}}},
    )

    async def execute(city: str) -> dict:
        return {"city": city, "condition": "Sunny"}

    return {"get_weather": (td, execute)}


async def test_simple_response():
    adapter = MockAdapter(responses=["The weather is sunny."])
    session = Session(session_id="s1")
    config = _make_config(adapter)

    events = []
    async for event in run_agent_loop(
        user_message="What's the weather?",
        session=session,
        instructions="You are a weather bot.",
        tools={},
        adapter=adapter,
        config=config,
    ):
        events.append(event)

    assert any(isinstance(e, TokenEvent) for e in events)
    assert any(isinstance(e, DoneEvent) for e in events)
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.text == "The weather is sunny."


async def test_user_message_appended_to_history():
    adapter = MockAdapter(responses=["hi"])
    session = Session(session_id="s2")
    config = _make_config(adapter)

    async for _ in run_agent_loop(
        user_message="hello",
        session=session,
        instructions="",
        tools={},
        adapter=adapter,
        config=config,
    ):
        pass

    assert session.history[0].role == "user"
    assert session.history[0].content == "hello"
    assert session.history[1].role == "assistant"
    assert session.history[1].content == "hi"


async def test_tool_call_executes_and_loops(monkeypatch):
    """Adapter first returns a tool call, then a final response."""
    from pyeve.types import ToolCallEvent

    call_count = 0

    class TwoTurnAdapter:
        async def complete(self, messages, tools, config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async def _first():
                    yield ToolCallEvent(id="c1", name="get_weather", input={"city": "Berlin"})
                    yield DoneEvent(text="")
                return _first()
            else:
                async def _second():
                    yield TokenEvent(text="It's sunny in Berlin.")
                    yield DoneEvent(text="It's sunny in Berlin.")
                return _second()

    session = Session(session_id="s3")
    adapter = TwoTurnAdapter()
    config = AgentConfig(model="mock", adapter=adapter)

    events = []
    async for event in run_agent_loop(
        user_message="Weather in Berlin?",
        session=session,
        instructions="",
        tools=_make_tools(),
        adapter=adapter,
        config=config,
    ):
        events.append(event)

    assert call_count == 2
    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].result["city"] == "Berlin"

    done = next(e for e in events if isinstance(e, DoneEvent))
    assert "sunny" in done.text.lower()


async def test_unknown_tool_yields_error():
    class BadToolAdapter:
        async def complete(self, messages, tools, config):
            async def _stream():
                yield ToolCallEvent(id="c1", name="nonexistent", input={})
                yield DoneEvent(text="")
            return _stream()

    session = Session(session_id="s4")
    adapter = BadToolAdapter()
    config = AgentConfig(model="mock", adapter=adapter)

    events = []
    async for event in run_agent_loop(
        user_message="test",
        session=session,
        instructions="",
        tools={},
        adapter=adapter,
        config=config,
    ):
        events.append(event)

    assert any(isinstance(e, ErrorEvent) for e in events)
    error = next(e for e in events if isinstance(e, ErrorEvent))
    assert "nonexistent" in error.message
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd python && uv run pytest tests/integration/test_loop.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyeve.loop'`

- [ ] **Step 3: Implement loop.py**

Create `python/src/pyeve/loop.py`:

```python
from __future__ import annotations

from typing import AsyncIterator, Callable

from pyeve.session import Session
from pyeve.types import (
    AgentConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    ModelAdapter,
    StreamEvent,
    TokenEvent,
    ToolCallEvent,
    ToolDefinition,
    ToolResultEvent,
)


async def run_agent_loop(
    *,
    user_message: str,
    session: Session,
    instructions: str,
    tools: dict[str, tuple[ToolDefinition, Callable]],
    adapter: ModelAdapter,
    config: AgentConfig,
) -> AsyncIterator[StreamEvent]:
    session.history.append(Message(role="user", content=user_message))
    tool_defs = [td for td, _ in tools.values()]

    while True:
        full_text = ""
        tool_calls: list[ToolCallEvent] = []

        system_message = Message(role="system", content=instructions)
        messages = [system_message, *session.history] if instructions else list(session.history)

        async for event in await adapter.complete(messages, tool_defs, config):
            if isinstance(event, TokenEvent):
                full_text += event.text
                yield event
            elif isinstance(event, ToolCallEvent):
                tool_calls.append(event)
                yield event
            elif isinstance(event, DoneEvent):
                break
            elif isinstance(event, ErrorEvent):
                yield event
                return

        session.history.append(Message(role="assistant", content=full_text))

        if not tool_calls:
            yield DoneEvent(text=full_text)
            return

        for call in tool_calls:
            if call.name not in tools:
                yield ErrorEvent(message=f"Unknown tool: {call.name}")
                return

            _, execute_fn = tools[call.name]
            result = await execute_fn(**call.input)

            yield ToolResultEvent(id=call.id, result=result)

            session.history.append(
                Message(
                    role="tool",
                    content=str(result),
                    tool_call_id=call.id,
                    tool_name=call.name,
                )
            )
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/integration/test_loop.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): agent loop with tool execution and streaming"
```

---

## Task 6: ASGI App

**Files:**
- Create: `python/src/pyeve/asgi.py`
- Create: `python/tests/integration/test_asgi.py`
- Create: `python/tests/fixtures/weather/agent/agent.py`

- [ ] **Step 1: Create agent.py fixture**

Create `python/tests/fixtures/weather/agent/agent.py`:

```python
from pyeve import define_agent
from pyeve.adapters.mock import MockAdapter

agent = define_agent(
    model="mock",
    adapter=MockAdapter(responses=["The weather in Berlin is sunny and 72°F."]),
)
```

- [ ] **Step 2: Write failing tests**

Create `python/tests/integration/test_asgi.py`:

```python
import json
import pytest
import httpx
from pyeve import agent


@pytest.fixture
def client(weather_agent_dir):
    app = agent(str(weather_agent_dir.parent.parent))  # points to fixtures/weather
    return httpx.AsyncClient(app=app, base_url="http://test")


async def test_chat_returns_200(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "What's the weather?"})
    assert response.status_code == 200


async def test_chat_streams_sse(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "weather?"})
    assert "text/event-stream" in response.headers.get("content-type", "")


async def test_chat_contains_done_event(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "weather?"})

    lines = response.text.splitlines()
    data_lines = [l for l in lines if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in data_lines]
    assert any(e.get("type") == "done" for e in events)


async def test_get_session_returns_history(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/chat", json={"message": "hello", "session_id": "test-sess"})
        response = await client.get("/sessions/test-sess")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-sess"
    assert len(data["history"]) >= 1


async def test_delete_session(weather_agent_dir, tmp_path):
    app = agent(str(weather_agent_dir), sessions_dir=tmp_path)
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/chat", json={"message": "hello", "session_id": "del-sess"})
        response = await client.delete("/sessions/del-sess")

    assert response.status_code == 204


async def test_unknown_route_returns_404(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/unknown")
    assert response.status_code == 404
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
cd python && uv run pytest tests/integration/test_asgi.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `pyeve.asgi` / `pyeve.agent`.

- [ ] **Step 4: Implement asgi.py**

Create `python/src/pyeve/asgi.py`:

```python
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Callable

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
            await _handle_get_session(send, session_id, store)
        elif method == "DELETE" and path.startswith("/sessions/"):
            session_id = path.removeprefix("/sessions/").strip("/")
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
    session_id: str = data.get("session_id") or str(uuid.uuid4())

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
    import shutil
    session_path = store._base / session_id
    if session_path.exists():
        shutil.rmtree(session_path)
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
```

- [ ] **Step 5: Update __init__.py**

Replace `python/src/pyeve/__init__.py`:

```python
"""
pyeve — filesystem-first framework for durable backend AI agents in Python.
"""

from pyeve.asgi import agent
from pyeve.types import AgentConfig

__version__ = "0.0.1"
__all__ = ["agent", "define_agent", "AgentConfig"]


def define_agent(
    *,
    model: str,
    adapter,
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> AgentConfig:
    """Configure the agent model and runtime options."""
    return AgentConfig(model=model, adapter=adapter, max_tokens=max_tokens, temperature=temperature)
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/integration/test_asgi.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): ASGI app with /chat SSE, /sessions CRUD, define_agent"
```

---

## Task 7: Testing Harness

**Files:**
- Modify: `python/src/pyeve/testing.py`

- [ ] **Step 1: Write failing tests for the testing harness**

Add to `python/tests/integration/test_loop.py`:

```python
from pyeve.testing import run_tool, AgentTestClient, ChatResponse
from pyeve.adapters.mock import MockAdapter


async def test_run_tool_calls_execute():
    from tests.fixtures.weather.agent.tools.get_weather import execute
    result = await run_tool(execute, city="Tokyo")
    assert result["city"] == "Tokyo"
    assert result["condition"] == "Sunny"


async def test_agent_test_client_chat(weather_agent_dir):
    adapter = MockAdapter(responses=["Tokyo is sunny today."])
    client = AgentTestClient(agent_dir=str(weather_agent_dir), adapter=adapter)
    response = await client.chat("Weather in Tokyo?")

    assert isinstance(response, ChatResponse)
    assert "sunny" in response.text.lower()
    assert len(response.events) > 0


async def test_agent_test_client_session_persists(tmp_path, weather_agent_dir):
    adapter = MockAdapter(responses=["Hello!", "Goodbye!"])
    client = AgentTestClient(
        agent_dir=str(weather_agent_dir),
        adapter=adapter,
        sessions_dir=tmp_path,
    )

    r1 = await client.chat("Hello", session_id="persist-test")
    r2 = await client.chat("Bye", session_id="persist-test")

    assert r1.text == "Hello!"
    assert r2.text == "Goodbye!"
```

- [ ] **Step 2: Run — verify fails**

```bash
cd python && uv run pytest tests/integration/test_loop.py::test_run_tool_calls_execute tests/integration/test_loop.py::test_agent_test_client_chat -v
```

Expected: `ImportError` for `pyeve.testing`.

- [ ] **Step 3: Implement testing.py**

Replace `python/src/pyeve/testing.py` (note: file already exists as placeholder, fully replace):

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/integration/test_loop.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): testing harness — run_tool, AgentTestClient, ChatResponse"
```

---

## Task 8: AnthropicAdapter

**Files:**
- Create: `python/src/pyeve/adapters/anthropic.py`

- [ ] **Step 1: Write failing test**

Add `python/tests/unit/test_adapters.py`:

```python
import pytest


def test_anthropic_adapter_importable():
    from pyeve.adapters.anthropic import AnthropicAdapter
    assert AnthropicAdapter is not None


def test_anthropic_adapter_satisfies_protocol():
    from pyeve.adapters.anthropic import AnthropicAdapter
    from pyeve.types import ModelAdapter
    assert isinstance(AnthropicAdapter(), ModelAdapter)


def test_openai_adapter_importable():
    from pyeve.adapters.openai import OpenAIAdapter
    assert OpenAIAdapter is not None


def test_sap_adapter_importable():
    from pyeve.adapters.sap import SAPAICoreAdapter
    assert SAPAICoreAdapter is not None
```

- [ ] **Step 2: Run — verify fails**

```bash
cd python && uv run pytest tests/unit/test_adapters.py::test_anthropic_adapter_importable -v
```

Expected: `ModuleNotFoundError: No module named 'pyeve.adapters.anthropic'`

- [ ] **Step 3: Implement AnthropicAdapter**

Create `python/src/pyeve/adapters/anthropic.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from pyeve.types import (
    AgentConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    StreamEvent,
    ToolCallEvent,
    ToolDefinition,
    TokenEvent,
)

if TYPE_CHECKING:
    pass


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
        import anthropic

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
                                elif hasattr(delta, "partial_json"):
                                    pass  # tool input accumulates in final message
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
            continue  # system is passed as system= param — handled separately if needed
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
```

- [ ] **Step 4: Implement OpenAIAdapter**

Create `python/src/pyeve/adapters/openai.py`:

```python
from __future__ import annotations

from typing import AsyncIterator

from pyeve.types import (
    AgentConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    StreamEvent,
    ToolCallEvent,
    ToolDefinition,
    TokenEvent,
)


class OpenAIAdapter:
    """Adapter for the OpenAI SDK (pip install pyeve[openai])."""

    def __init__(self) -> None:
        try:
            import openai as _openai
            self._client = _openai.AsyncOpenAI()
        except ImportError:
            raise ImportError(
                "OpenAIAdapter requires the openai package. "
                "Install it with: pip install pyeve[openai]"
            )

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: AgentConfig,
    ) -> AsyncIterator[StreamEvent]:
        import json

        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        openai_tools = [
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
            "max_tokens": config.max_tokens,
            "messages": openai_messages,
            "stream": True,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature

        async def _stream() -> AsyncIterator[StreamEvent]:
            try:
                full_text = ""
                tool_calls_accumulator: dict[int, dict] = {}

                async for chunk in await self._client.chat.completions.create(**kwargs):
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    if delta.content:
                        full_text += delta.content
                        yield TokenEvent(text=delta.content)

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_accumulator:
                                tool_calls_accumulator[idx] = {
                                    "id": tc.id or "",
                                    "name": tc.function.name or "" if tc.function else "",
                                    "arguments": "",
                                }
                            if tc.function and tc.function.arguments:
                                tool_calls_accumulator[idx]["arguments"] += tc.function.arguments

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
```

- [ ] **Step 5: Implement SAPAICoreAdapter**

Create `python/src/pyeve/adapters/sap.py`:

```python
from __future__ import annotations

from typing import AsyncIterator

from pyeve.types import (
    AgentConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    StreamEvent,
    ToolCallEvent,
    ToolDefinition,
    TokenEvent,
)


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
        import json

        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        openai_tools = [
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
            "model_name": config.model,
            "messages": openai_messages,
            "stream": True,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools
        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature

        async def _stream() -> AsyncIterator[StreamEvent]:
            try:
                full_text = ""
                tool_calls_accumulator: dict[int, dict] = {}

                async for chunk in await self._client.chat.completions.create(**kwargs):
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    if delta.content:
                        full_text += delta.content
                        yield TokenEvent(text=delta.content)

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_accumulator:
                                tool_calls_accumulator[idx] = {
                                    "id": tc.id or "",
                                    "name": tc.function.name or "" if tc.function else "",
                                    "arguments": "",
                                }
                            if tc.function and tc.function.arguments:
                                tool_calls_accumulator[idx]["arguments"] += tc.function.arguments

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
```

- [ ] **Step 6: Run adapter tests**

```bash
cd python && uv run pytest tests/unit/test_adapters.py -v
```

Expected: all 4 tests PASS (import checks only — no real API calls).

- [ ] **Step 7: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): AnthropicAdapter, OpenAIAdapter, SAPAICoreAdapter"
```

---

## Task 9: CLI

**Files:**
- Modify: `python/src/pyeve/cli.py`

- [ ] **Step 1: Write failing test**

Create `python/tests/unit/test_cli.py`:

```python
import subprocess
import sys
from pathlib import Path


def test_pyeve_help():
    result = subprocess.run(
        [sys.executable, "-m", "pyeve.cli"],
        capture_output=True, text=True,
    )
    assert "init" in result.stdout or "init" in result.stderr


def test_pyeve_init_creates_directory(tmp_path):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pyeve.cli", "init", "my-agent"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert result.returncode == 0
    agent_dir = tmp_path / "my-agent" / "agent"
    assert (agent_dir / "instructions.md").exists()
    assert (agent_dir / "agent.py").exists()
    assert (agent_dir / "tools").is_dir()


def test_pyeve_init_instructions_content(tmp_path):
    import subprocess, sys
    subprocess.run(
        [sys.executable, "-m", "pyeve.cli", "init", "bot"],
        capture_output=True, cwd=tmp_path,
    )
    content = (tmp_path / "bot" / "agent" / "instructions.md").read_text()
    assert len(content) > 10
```

- [ ] **Step 2: Run — verify fails**

```bash
cd python && uv run pytest tests/unit/test_cli.py -v
```

Expected: tests fail because CLI doesn't implement `init` yet.

- [ ] **Step 3: Implement cli.py**

Replace `python/src/pyeve/cli.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="pyeve", description="pyeve agent framework")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Scaffold a new agent directory")
    init_parser.add_argument("name", help="Directory name for the new agent")

    dev_parser = subparsers.add_parser("dev", help="Run agent in development mode with hot reload")
    dev_parser.add_argument("--dir", default="./agent", help="Path to agent directory")
    dev_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    dev_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    if args.command == "init":
        _cmd_init(args.name)
    elif args.command == "dev":
        _cmd_dev(args.dir, args.host, args.port)
    else:
        parser.print_help()
        sys.exit(0)


def _cmd_init(name: str) -> None:
    root = Path(name)
    agent_dir = root / "agent"
    tools_dir = agent_dir / "tools"

    for d in [root, agent_dir, tools_dir]:
        d.mkdir(parents=True, exist_ok=True)

    (agent_dir / "instructions.md").write_text(
        "You are a helpful assistant.\n\n"
        "Use the tools available to you to answer questions accurately.\n"
    )

    (agent_dir / "agent.py").write_text(
        "from pyeve import define_agent\n"
        "from pyeve.adapters.anthropic import AnthropicAdapter\n\n"
        "agent = define_agent(\n"
        '    model="claude-sonnet-4-6",\n'
        "    adapter=AnthropicAdapter(),\n"
        ")\n"
    )

    (tools_dir / "example.py").write_text(
        'async def execute(query: str) -> str:\n'
        '    """Answer a question with a placeholder response."""\n'
        '    return f"You asked: {query}"\n'
    )

    print(f"Created {agent_dir}")
    print(f"  {agent_dir}/instructions.md")
    print(f"  {agent_dir}/agent.py")
    print(f"  {agent_dir}/tools/example.py")
    print(f"\nRun: cd {name} && pyeve dev")


def _cmd_dev(agent_dir: str, host: str, port: int) -> None:
    try:
        import uvicorn
        from watchfiles import run_process
    except ImportError:
        print(
            "pyeve dev requires uvicorn and watchfiles.\n"
            "Install with: pip install uvicorn watchfiles"
        )
        sys.exit(1)

    agent_path = Path(agent_dir).resolve()
    print(f"Starting pyeve dev server on http://{host}:{port}")
    print(f"Watching {agent_path} for changes...")

    def _start():
        from pyeve import agent
        import uvicorn
        app = agent(str(agent_path))
        uvicorn.run(app, host=host, port=port, log_level="info")

    run_process(str(agent_path), target=_start)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd python && uv run pytest tests/unit/test_cli.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): CLI — pyeve init and pyeve dev"
```

---

## Task 10: Full Test Run & Version Bump

**Files:**
- Modify: `python/pyproject.toml` (version → 0.1.0)
- Modify: `python/src/pyeve/__init__.py` (version → 0.1.0)

- [ ] **Step 1: Run full test suite**

```bash
cd python && uv run pytest tests/ -v
```

Expected: all tests PASS. If any fail, fix before proceeding.

- [ ] **Step 2: Bump version to 0.1.0**

In `python/pyproject.toml`, change:
```toml
version = "0.0.1"
```
to:
```toml
version = "0.1.0"
```

In `python/src/pyeve/__init__.py`, change:
```python
__version__ = "0.0.1"
```
to:
```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Build**

```bash
cd python && uv build
```

Expected: `dist/pyeve-0.1.0.tar.gz` and `dist/pyeve-0.1.0-py3-none-any.whl` created.

- [ ] **Step 4: Commit**

```bash
git add python/ && git commit -s -m "feat(pyeve): v0.1.0 — filesystem-first Python agent framework"
```

- [ ] **Step 5: Publish to PyPI**

```bash
cd python && uv publish --token $PYPI_TOKEN
```

Expected: `pyeve 0.1.0` published to https://pypi.org/project/pyeve/

---

## Summary

| Task | What ships |
|---|---|
| 1 | Project setup, test fixtures |
| 2 | Core types, MockAdapter |
| 3 | Tool discovery from filesystem |
| 4 | Session + DiskSessionStore |
| 5 | Agent loop with streaming |
| 6 | ASGI app + define_agent |
| 7 | Testing harness |
| 8 | Anthropic, OpenAI, SAP adapters |
| 9 | CLI (init + dev) |
| 10 | Full test run + v0.1.0 publish |
