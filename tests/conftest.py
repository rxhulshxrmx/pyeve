from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def weather_agent_dir() -> Path:
    return FIXTURES_DIR / "weather" / "agent"
