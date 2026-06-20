<div align="center">
  <a href="https://pypi.org/project/pyeve"><img alt="PyPI version" src="https://img.shields.io/pypi/v/pyeve.svg?style=for-the-badge&labelColor=000000"></a>
  <a href="https://github.com/rxhulshxrmx/pyeve/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/pyeve.svg?style=for-the-badge&labelColor=000000"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge&labelColor=000000"></a>
</div>

<br/>

**pyeve** is a filesystem-first framework for durable backend AI agents in Python. Core agent capabilities live in conventional locations, so projects are easier to inspect, extend, and operate.

## The filesystem is the authoring interface

A pyeve agent is just three things:

```text
my-agent/
└── agent/
    ├── agent.py            # model and adapter config
    ├── instructions.md     # always-on system prompt
    └── tools/              # functions the model can call
        └── search.py
```

No decorators. No schema classes. No custom adapters. pyeve wires it all together automatically.

## Quick start

```bash
pip install "pyeve[mistral]"
pyeve init my-agent
cd my-agent
pyeve dev
```

Your agent is running at `http://localhost:8000`.

## A minimal example

`agent/instructions.md`:

```md
You are a concise weather assistant. Tell users that the weather data is mocked.
```

`agent/tools/get_weather.py`:

```python
async def execute(city: str) -> dict:
    """Return current weather for a city."""
    return {"city": city, "condition": "Sunny", "temp_f": 72}
```

`agent/agent.py`:

```python
from pyeve import define_agent
from pyeve.adapters.mistral import MistralAdapter

agent = define_agent(
    model="mistral-large-latest",
    adapter=MistralAdapter(),
)
```

Set your API key and start the server:

```bash
export MISTRAL_API_KEY=...
pyeve dev
```

Send a message:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Berlin?"}'
```

Response streams as [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).

## Tools are plain async functions

pyeve reads the docstring as the tool description and infers the JSON schema from type hints. No registration needed — any `.py` file in `tools/` is auto-discovered.

```python
# agent/tools/search.py
async def execute(query: str, limit: int = 5) -> list[dict]:
    """Search the knowledge base and return matching documents."""
    ...
```

## SSE event stream

Each `POST /chat` response streams newline-delimited SSE events:

| Event type | Payload |
|---|---|
| `token` | `{"type": "token", "text": "..."}` |
| `tool_call` | `{"type": "tool_call", "id": "...", "name": "...", "input": {...}}` |
| `tool_result` | `{"type": "tool_result", "id": "...", "result": {...}}` |
| `done` | `{"type": "done", "text": "<full response>"}` |
| `error` | `{"type": "error", "message": "..."}` |

## Durable sessions

Sessions are persisted to disk automatically. Resume a conversation by passing `session_id`:

```bash
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Follow up question", "session_id": "user-123"}'
```

Retrieve history:

```bash
curl http://localhost:8000/sessions/user-123
```

## Works with any Python framework

`agent()` returns a standard ASGI callable — mount it anywhere:

```python
# FastAPI
from fastapi import FastAPI
from pyeve import agent

app = FastAPI()
app.mount("/", agent("./agent"))
```

```python
# Standalone with uvicorn
import uvicorn
from pyeve import agent

uvicorn.run(agent("./agent"), port=8000)
```

## Provider adapters

| Provider | Install | Adapter |
|---|---|---|
| Mistral | `pip install "pyeve[mistral]"` | `MistralAdapter()` |
| SAP AI Core | `pip install "pyeve[sap]"` | `SAPAICoreAdapter()` |

## Testing

pyeve ships a `MockAdapter` and test client for unit testing agents without real API calls:

```python
from pyeve.adapters.mock import MockAdapter
from pyeve.testing import AgentTestClient

async def test_weather_agent():
    client = AgentTestClient(
        agent_dir="./agent",
        adapter=MockAdapter(responses=["The weather in Berlin is sunny and 72°F."]),
    )
    response = await client.chat("What is the weather in Berlin?")
    assert "Berlin" in response.text
```

## License

Apache 2.0
