<div align="center">
  <a href="https://pypi.org/project/pyeve"><img alt="PyPI version" src="https://img.shields.io/pypi/v/pyeve.svg?style=for-the-badge&labelColor=000000"></a>
  <a href="https://github.com/rxhulshxrmx/pyeve/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/pyeve.svg?style=for-the-badge&labelColor=000000"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge&labelColor=000000"></a>
</div>

<br/>

**pyeve** is a filesystem-first framework for durable backend AI agents in Python. Core agent capabilities live in conventional locations, so projects are easier to inspect, extend, and operate.

## The filesystem is the authoring interface

A typical pyeve agent has this structure:

```text
my-agent/
└── agent/
    ├── agent.py            # model and runtime config
    ├── instructions.md     # always-on system prompt
    └── tools/              # functions the model can call
        └── get_weather.py
```

## Quick start

```bash
pip install pyeve
pyeve init my-agent
cd my-agent
pyeve dev
```

Your agent is running at `http://localhost:8000`.

## A minimal example

Replace `agent/instructions.md` with:

```md
You are a concise weather assistant. Tell users that the weather data is mocked.
```

Add a tool at `agent/tools/get_weather.py`:

```python
async def execute(city: str) -> dict:
    """Return current weather for a city."""
    return {"city": city, "condition": "Sunny", "temp_f": 72}
```

Configure the model in `agent/agent.py`:

```python
from pyeve import define_agent
from pyeve.adapters.anthropic import AnthropicAdapter

agent = define_agent(
    model="claude-sonnet-4-6",
    adapter=AnthropicAdapter(),
)
```

Send a message:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Berlin?"}'
```

Response streams as [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).

## Tools are plain async functions

No decorators, no schema classes. pyeve reads the docstring as the description and infers the JSON schema from type hints.

```python
# agent/tools/search.py
async def execute(query: str, limit: int = 5) -> list[dict]:
    """Search the knowledge base and return matching documents."""
    ...
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
| Anthropic | `pip install "pyeve[anthropic]"` | `AnthropicAdapter()` |
| OpenAI | `pip install "pyeve[openai]"` | `OpenAIAdapter()` |
| Mistral | `pip install "pyeve[mistral]"` | `MistralAdapter()` |
| SAP AI Core | `pip install "pyeve[sap]"` | `SAPAICoreAdapter()` |

## Durable sessions

Sessions are persisted to disk automatically. Pick up a conversation by passing `session_id`:

```bash
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Follow up question", "session_id": "user-123"}'
```

Retrieve history:

```bash
curl http://localhost:8000/sessions/user-123
```

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
