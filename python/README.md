# pyeve

Filesystem-first framework for durable backend AI agents in Python.

> **Coming soon.** This package is under active development.
> See the [TypeScript version](https://beta.eve.dev) for the stable release.

## What it will do

Drop an `agent/` directory, run `pyeve dev`. Your agent is live.

```
my-agent/
└── agent/
    ├── agent.py          # model + runtime config
    ├── instructions.md   # always-on system prompt
    └── tools/
        └── get_weather.py
```

Tools are plain async functions — no boilerplate:

```python
# agent/tools/get_weather.py
async def execute(city: str) -> dict:
    """Return current weather for a city."""
    return {"city": city, "condition": "Sunny", "temp_f": 72}
```

- Works with FastAPI, Django, Flask, or standalone
- Durable sessions out of the box
- Provider-agnostic: Anthropic, OpenAI, SAP AI Core, LiteLLM

## Stay tuned

- GitHub: https://github.com/vercel/eve
- Docs: https://beta.eve.dev
