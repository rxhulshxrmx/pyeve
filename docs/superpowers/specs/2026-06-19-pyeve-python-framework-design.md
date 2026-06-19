# pyeve — Python Framework Design Spec

**Date:** 2026-06-19
**Status:** Approved

## Overview

pyeve is a filesystem-first framework for durable backend AI agents in Python. It mirrors the
philosophy of the TypeScript `eve` framework — agent capabilities live as files in conventional
locations — but is adapted to Python idioms rather than being a 1:1 port.

Published to PyPI as `pyeve`. Run with `pip install pyeve`.

---

## 1. Filesystem Layout

A pyeve agent is a directory on disk:

```
my-agent/
└── agent/
    ├── agent.py              # model + runtime config
    ├── instructions.md       # always-on system prompt (plain markdown)
    ├── tools/
    │   └── get_weather.py    # execute() + InputSchema = auto-registered tool
    ├── skills/
    │   └── plan_a_trip.md    # loaded on demand by the model
    ├── connections/          # MCP client connections (later milestone)
    ├── subagents/            # nested agent directories (later milestone)
    └── schedules/            # cron jobs (later milestone)
```

### Tool files

A tool file is a plain async function — no pyeve imports, no schema class:

```python
# agent/tools/get_weather.py
async def execute(city: str) -> dict:
    """Return current weather for a city."""
    return {"city": city, "condition": "Sunny", "temp_f": 72}
```

pyeve introspects the function signature to auto-generate the JSON schema (via Pydantic under the hood). The docstring becomes the tool description passed to the model.

For complex input types, standard Python type hints work as expected:

```python
from typing import Literal

async def execute(city: str, units: Literal["celsius", "fahrenheit"] = "fahrenheit") -> dict:
    """Return current weather for a city."""
    ...
```

**Invariants:**
- Tool name = filename stem (`get_weather.py` → tool named `get_weather`)
- Docstring = tool description (required — pyeve raises at startup if missing)
- `execute()` must be `async`
- Parameters must have type hints — pyeve raises at startup if any are missing
- No `name` field, no `InputSchema` class, no pyeve imports needed

### agent.py

```python
from pyeve import define_agent
from pyeve.adapters.anthropic import AnthropicAdapter

agent = define_agent(
    model="claude-sonnet-4-6",
    adapter=AnthropicAdapter(),
    max_tokens=4096,
)
```

### instructions.md

Plain markdown. No frontmatter required. Identical format to TypeScript eve — agents can share
instruction files across implementations.

### Skills

Markdown files under `skills/`. Loaded into context on demand when the model decides they are
relevant. Same format as TypeScript eve.

---

## 2. Agent Loop

The same loop runs regardless of where the message originates (HTTP, Slack, CLI):

```
Message in
    │
    ▼
Load session (resume if existing, create if new)
    │
    ▼
Build context (instructions + history + tools + skills)
    │
    ▼
Call model via adapter → stream tokens
    │
    ▼
Tool call requested?
   ├── yes → execute tool → append result → loop back to model
   └── no  → final response → stream to caller
    │
    ▼
Persist session state
    │
    ▼
Response out (async generator of StreamEvent)
```

Streaming is via `AsyncIterator[StreamEvent]` throughout the stack. Event types:

- `token` — a text chunk from the model
- `tool_start` — model requested a tool call
- `tool_end` — tool returned a result
- `done` — final response complete
- `error` — unrecoverable failure

---

## 3. Durability

Sessions are durable by default. State is persisted at each checkpoint so agents can resume after
crashes or restarts.

**Default backend: local disk**

```
.pyeve/
└── sessions/
    └── <session-id>/
        ├── meta.json       # session metadata, model config
        ├── history.json    # full message history
        └── step-<n>.json   # per-step checkpoint
```

Files are written atomically (write to tmp, rename). If the process crashes mid-tool, the next
request replays from the last committed checkpoint.

**SessionStore protocol** — swap the backend without changing agent code:

```python
class SessionStore(Protocol):
    async def load(self, session_id: str) -> Session | None: ...
    async def save(self, session: Session) -> None: ...
```

Bundled backends: `DiskSessionStore` (default), `RedisSessionStore` (via `pyeve[redis]`),
`SQLiteSessionStore` (via `pyeve[sqlite]`).

Session IDs come from the caller (HTTP header, Slack thread ID, etc.) so sessions naturally map
to conversations.

---

## 4. Provider Adapters

pyeve never calls an AI SDK directly. All model access goes through a `ModelAdapter` protocol:

```python
class ModelAdapter(Protocol):
    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        config: ModelConfig,
    ) -> AsyncIterator[StreamEvent]: ...
```

Bundled adapters are optional extras — they don't bloat the base install:

| Extra | Adapter | Underlying SDK |
|---|---|---|
| `pyeve[anthropic]` | `AnthropicAdapter` | `anthropic` |
| `pyeve[openai]` | `OpenAIAdapter` | `openai` |
| `pyeve[litellm]` | `LiteLLMAdapter` | `litellm` (100+ models) |
| `pyeve[sap]` | `SAPAICoreAdapter` | `generative-ai-hub-sdk` |

Adapters are thin wrappers — they translate `StreamEvent` from SDK-specific stream chunks. No
business logic lives in adapters.

### SAP AI Core adapter

SAP AI Core exposes an OpenAI-compatible API. The adapter handles token exchange and routes
through the SAP AI Core endpoint:

```python
from pyeve.adapters.sap import SAPAICoreAdapter

agent = define_agent(
    model="gpt-4o",   # deployment name in SAP AI Core
    adapter=SAPAICoreAdapter(
        resource_group="default",
        # credentials from env: AICORE_CLIENT_ID, AICORE_CLIENT_SECRET,
        # AICORE_AUTH_URL, AICORE_BASE_URL
        # or from ~/.aicore/config.json
    ),
)
```

---

## 5. CLI

```bash
pyeve init my-agent   # scaffold a new agent directory
pyeve dev             # watch agent/, hot-reload, serve on localhost
pyeve build           # validate + export deployable artifact
pyeve eval            # run evals (later milestone)
```

`pyeve dev` starts a lightweight ASGI app, auto-discovers tools/skills on file change, and prints
a local URL. No config required.

---

## 6. Framework Integration

pyeve exposes a single ASGI callable via `agent()`. It mounts into any ASGI-compatible framework:

```python
from pyeve import agent

# Standalone
import uvicorn
uvicorn.run(agent(), port=8000)

# FastAPI
from fastapi import FastAPI
app = FastAPI()
app.mount("/agent", agent("./agent"))

# Django (asgi.py)
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
application = ProtocolTypeRouter({
    "http": URLRouter([path("agent/", agent("./agent"))]),
})
```

`agent()` defaults to `./agent` if no path is given.

### HTTP endpoints (mounted at user-chosen prefix)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/chat` | Start or continue a session, streams SSE |
| `GET` | `/sessions/{id}` | Fetch session history |
| `DELETE` | `/sessions/{id}` | Clear a session |

Streaming response format: **Server-Sent Events (SSE)** — works in every browser and HTTP client
with no special setup.

---

## 7. Testing

pyeve ships a test harness for unit and integration testing without real model calls.

### Unit tests — test tool functions directly

```python
from pyeve.testing import run_tool
from agent.tools.get_weather import execute, InputSchema

async def test_get_weather():
    result = await run_tool(execute, InputSchema(city="Berlin"))
    assert result["city"] == "Berlin"
```

### Integration tests — full agent loop with mock model

```python
from pyeve.testing import AgentTestClient, MockAdapter

async def test_agent_responds():
    client = AgentTestClient(
        agent_dir="./agent",
        adapter=MockAdapter(responses=["The weather in Berlin is sunny."]),
    )
    response = await client.chat("What's the weather in Berlin?")
    assert "sunny" in response.text
```

`MockAdapter` plays back scripted responses in order — no API keys needed in CI.

### Test tiers

| Tier | How | Speed |
|---|---|---|
| Unit | Call `execute()` directly | <1s |
| Integration | `AgentTestClient` + `MockAdapter` | <5s |
| E2E | `AgentTestClient` + real adapter | minutes, needs credentials |

---

## 8. v0.1 Scope

Build in this order. Each item is independently shippable:

1. **Discovery** — scan `agent/tools/*.py`, validate `InputSchema` + `execute()`, build `ToolDefinition`
2. **Agent loop** — context assembly, model call via adapter, tool execution, streaming
3. **Durability** — `DiskSessionStore`, atomic checkpoint writes, resume on crash
4. **ASGI app** — `agent()` callable, `/chat` SSE endpoint, session endpoints
5. **CLI** — `pyeve init`, `pyeve dev` (file watcher + hot reload)
6. **Bundled adapters** — `AnthropicAdapter`, `OpenAIAdapter`, `SAPAICoreAdapter`
7. **Testing harness** — `run_tool`, `AgentTestClient`, `MockAdapter`
8. **PyPI publish** — `pyeve` package with optional extras

**Out of scope for v0.1:** channels (Slack, Discord), connections (MCP clients), subagents,
schedules, `pyeve build`, `pyeve eval`.

---

## 9. Package Structure

```
pyeve/
├── pyproject.toml
├── src/
│   └── pyeve/
│       ├── __init__.py          # exports: agent(), define_agent()
│       ├── discover.py          # filesystem scanner
│       ├── loop.py              # agent loop
│       ├── session.py           # Session, SessionStore protocol
│       ├── stores/
│       │   ├── disk.py          # DiskSessionStore
│       │   └── redis.py         # RedisSessionStore (pyeve[redis])
│       ├── adapters/
│       │   ├── base.py          # ModelAdapter protocol
│       │   ├── anthropic.py     # AnthropicAdapter
│       │   ├── openai.py        # OpenAIAdapter
│       │   ├── litellm.py       # LiteLLMAdapter
│       │   └── sap.py           # SAPAICoreAdapter
│       ├── asgi.py              # agent() ASGI callable
│       ├── cli.py               # pyeve CLI entry point
│       └── testing.py           # run_tool, AgentTestClient, MockAdapter
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```
