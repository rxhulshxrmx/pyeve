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
    for path in sorted(p for p in tools_dir.glob("*.py") if not p.stem.startswith("_")):
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
