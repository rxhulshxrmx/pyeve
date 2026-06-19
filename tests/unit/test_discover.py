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
