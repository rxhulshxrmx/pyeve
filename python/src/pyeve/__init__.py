"""
pyeve — filesystem-first framework for durable backend AI agents in Python.
"""

from pyeve.asgi import agent
from pyeve.types import AgentConfig

__version__ = "0.1.0"
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
