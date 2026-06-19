import json
import pytest
import httpx
from pyeve import agent


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


async def test_chat_returns_200(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with _client(app) as client:
        response = await client.post("/chat", json={"message": "What's the weather?"})
    assert response.status_code == 200


async def test_chat_streams_sse(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with _client(app) as client:
        response = await client.post("/chat", json={"message": "weather?"})
    assert "text/event-stream" in response.headers.get("content-type", "")


async def test_chat_contains_done_event(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with _client(app) as client:
        response = await client.post("/chat", json={"message": "weather?"})

    lines = response.text.splitlines()
    data_lines = [l for l in lines if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in data_lines]
    assert any(e.get("type") == "done" for e in events)


async def test_get_session_returns_history(weather_agent_dir, tmp_path):
    app = agent(str(weather_agent_dir), sessions_dir=tmp_path)
    async with _client(app) as client:
        await client.post("/chat", json={"message": "hello", "session_id": "test-sess"})
        response = await client.get("/sessions/test-sess")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-sess"
    assert len(data["history"]) >= 1


async def test_delete_session(weather_agent_dir, tmp_path):
    app = agent(str(weather_agent_dir), sessions_dir=tmp_path)
    async with _client(app) as client:
        await client.post("/chat", json={"message": "hello", "session_id": "del-sess"})
        response = await client.delete("/sessions/del-sess")

    assert response.status_code == 204


async def test_unknown_route_returns_404(weather_agent_dir):
    app = agent(str(weather_agent_dir))
    async with _client(app) as client:
        response = await client.get("/unknown")
    assert response.status_code == 404
