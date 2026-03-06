"""Tests for A2A HTTP Server."""

import asyncio
import json

from starlette.testclient import TestClient

from modelmux.a2a.http_server import (
    A2AServer,
    InvalidParamsError,
    TaskNotFoundError,
    TaskStore,
    _extract_task_params,
)
from modelmux.adapters.base import AdapterResult, BaseAdapter


# --- Fake adapter for testing ---


class FakeAdapter(BaseAdapter):
    provider_name = "fake"

    def _binary_name(self) -> str:
        return "echo"

    def build_command(self, prompt, workdir, **kw):
        return ["echo", prompt]

    def parse_output(self, lines):
        return "\n".join(lines), "", ""

    async def run(self, prompt="", **kw):
        if "CONVERGED" in prompt or "synthesize" in prompt.lower():
            output = "CONVERGED: looks good\n\nAll criteria met."
        else:
            output = f"Fake response to: {prompt[:80]}"
        return AdapterResult(
            provider="fake",
            status="success",
            output=output,
            summary=output[:100],
            duration_seconds=0.1,
        )


def _get_fake_adapter(name: str) -> BaseAdapter:
    return FakeAdapter()


def _make_client() -> TestClient:
    server = A2AServer(
        get_adapter=_get_fake_adapter,
        host="127.0.0.1",
        port=0,
        workdir="/tmp",
        sandbox="read-only",
    )
    app = server.create_app()
    return TestClient(app)


# --- Agent Card Tests ---


def test_agent_card_endpoint():
    client = _make_client()
    resp = client.get("/.well-known/agent.json")
    assert resp.status_code == 200
    card = resp.json()
    assert card["name"] == "modelmux"
    assert card["protocolVersion"] == "0.3.0"
    assert "skills" in card
    assert "capabilities" in card
    assert card["capabilities"]["streaming"] is True


def test_agent_card_has_skills():
    client = _make_client()
    card = client.get("/.well-known/agent.json").json()
    skill_names = [s["name"] for s in card["skills"]]
    assert any("review" in n for n in skill_names)
    assert any("consensus" in n for n in skill_names)
    assert any("debate" in n for n in skill_names)


# --- JSON-RPC Validation Tests ---


def test_invalid_json():
    client = _make_client()
    resp = client.post("/", content="not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == -32700


def test_invalid_jsonrpc_version():
    client = _make_client()
    resp = client.post(
        "/",
        json={"jsonrpc": "1.0", "id": 1, "method": "tasks/get", "params": {}},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == -32600


def test_unknown_method():
    client = _make_client()
    resp = client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}},
    )
    body = resp.json()
    assert body["error"]["code"] == -32601


# --- TaskStore Tests ---


def test_task_store_create():
    store = TaskStore()
    entry = store.create()
    assert entry.task_id.startswith("task-")
    assert entry.context_id.startswith("ctx-")
    assert entry.state == "submitted"


def test_task_store_get():
    store = TaskStore()
    entry = store.create(task_id="test-123")
    assert store.get("test-123") is entry
    assert store.get("nonexistent") is None


def test_task_store_update():
    store = TaskStore()
    entry = store.create(task_id="test-456")
    store.update("test-456", state="working")
    assert entry.state == "working"


def test_task_store_eviction():
    store = TaskStore(max_tasks=3)
    for i in range(5):
        e = store.create(task_id=f"task-{i}")
        e.state = "completed"
    # Should have evicted oldest completed tasks
    assert len(store._tasks) <= 3


# --- _extract_task_params Tests ---


def test_extract_task_params_basic():
    params = {
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "implement a REST API"}],
        }
    }
    text, pattern, providers = _extract_task_params(params)
    assert text == "implement a REST API"
    assert pattern == "review"  # default
    assert providers is None


def test_extract_task_params_with_metadata():
    params = {
        "message": {
            "role": "user",
            "parts": [{"text": "analyze this code"}],
        },
        "metadata": {
            "pattern": "consensus",
            "providers": {"analyst_impl": "codex"},
        },
    }
    text, pattern, providers = _extract_task_params(params)
    assert text == "analyze this code"
    assert pattern == "consensus"
    assert providers == {"analyst_impl": "codex"}


def test_extract_task_params_empty_message():
    try:
        _extract_task_params({"message": {"parts": []}})
        assert False, "Should have raised"
    except InvalidParamsError:
        pass


# --- tasks/get Tests ---


def test_tasks_get_not_found():
    client = _make_client()
    resp = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"id": "nonexistent"},
        },
    )
    body = resp.json()
    assert body["error"]["code"] == -32001


def test_tasks_get_missing_id():
    client = _make_client()
    resp = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {},
        },
    )
    body = resp.json()
    assert body["error"]["code"] == -32602


# --- tasks/send Tests ---


def test_tasks_send_basic():
    client = _make_client()
    resp = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "hello world"}],
                },
                "metadata": {"pattern": "review"},
            },
        },
    )
    body = resp.json()
    assert "result" in body
    result = body["result"]
    assert "id" in result
    assert "contextId" in result
    assert result["status"]["state"] in ("completed", "failed")
    assert result["metadata"]["pattern"] == "review"


# --- tasks/cancel Tests ---


def test_tasks_cancel_not_found():
    client = _make_client()
    resp = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/cancel",
            "params": {"id": "nonexistent"},
        },
    )
    body = resp.json()
    assert body["error"]["code"] == -32001


# --- tasks/sendSubscribe Tests ---


def test_tasks_send_subscribe():
    client = _make_client()
    resp = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/sendSubscribe",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "quick test"}],
                },
                "metadata": {"pattern": "review"},
            },
        },
    )
    # SSE response
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
