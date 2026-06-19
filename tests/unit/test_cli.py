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
    subprocess.run(
        [sys.executable, "-m", "pyeve.cli", "init", "bot"],
        capture_output=True, cwd=tmp_path,
    )
    content = (tmp_path / "bot" / "agent" / "instructions.md").read_text()
    assert len(content) > 10
