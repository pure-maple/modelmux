"""Tests for the mux_orchestrate MCP tool."""

import json
from unittest.mock import patch

import pytest

from modelmux.orchestrate_store import OrchestrateStore


class FakeRequestContext:
    """Minimal request context stub."""


class FakeContext:
    """Mock MCP Context with async methods."""

    def __init__(self):
        self._request_context = FakeRequestContext()
        self.session = None
        self.messages = []

    async def info(self, msg):
        self.messages.append(("info", msg))

    async def warning(self, msg):
        self.messages.append(("warning", msg))


class TestMuxOrchestrate:
    @pytest.mark.asyncio
    async def test_plan_assign_status_review_merge_flow(self, tmp_path):
        from modelmux.server import mux_orchestrate

        store = OrchestrateStore(path=tmp_path / "orchestrate.jsonl")
        ctx = FakeContext()

        with patch("modelmux.server._get_orchestrate_store", return_value=store):
            planned = json.loads(
                await mux_orchestrate(
                    action="plan", task="write release notes", ctx=ctx
                )
            )
            assert planned["status"] == "success"
            task_id = planned["task"]["task_id"]
            assert planned["task"]["suggested_role"] == "writer"

            assigned = json.loads(
                await mux_orchestrate(
                    action="assign",
                    task_id=task_id,
                    role="writer",
                    agent="claude",
                    branch="codex/notes",
                    ctx=ctx,
                )
            )
            assert assigned["task"]["state"] == "implementing"

            status = json.loads(
                await mux_orchestrate(action="status", task_id=task_id, ctx=ctx)
            )
            assert status["task"]["branch"] == "codex/notes"

            review = json.loads(
                await mux_orchestrate(action="review", branch="codex/notes", ctx=ctx)
            )
            assert review["task"]["state"] == "reviewing"

            merged = json.loads(
                await mux_orchestrate(action="merge", task_id=task_id, ctx=ctx)
            )
            assert merged["task"]["state"] == "integrated"

    @pytest.mark.asyncio
    async def test_status_summary_lists_tasks(self, tmp_path):
        from modelmux.server import mux_orchestrate

        store = OrchestrateStore(path=tmp_path / "orchestrate.jsonl")
        ctx = FakeContext()

        with patch("modelmux.server._get_orchestrate_store", return_value=store):
            await mux_orchestrate(action="plan", task="implement feature", ctx=ctx)
            await mux_orchestrate(action="plan", task="debug flaky test", ctx=ctx)

            result = json.loads(
                await mux_orchestrate(action="status", ctx=ctx, limit=5)
            )
            assert result["status"] == "success"
            assert result["summary"]["total"] == 2
            assert len(result["tasks"]) == 2
            assert "implementer" in result["roles"]

    @pytest.mark.asyncio
    async def test_invalid_action_returns_error(self, tmp_path):
        from modelmux.server import mux_orchestrate

        store = OrchestrateStore(path=tmp_path / "orchestrate.jsonl")
        ctx = FakeContext()

        with patch("modelmux.server._get_orchestrate_store", return_value=store):
            result = json.loads(await mux_orchestrate(action="ship", ctx=ctx))
        assert result["status"] == "error"
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_task_for_assign_returns_error(self, tmp_path):
        from modelmux.server import mux_orchestrate

        store = OrchestrateStore(path=tmp_path / "orchestrate.jsonl")
        ctx = FakeContext()

        with patch("modelmux.server._get_orchestrate_store", return_value=store):
            result = json.loads(
                await mux_orchestrate(
                    action="assign",
                    task_id="T999",
                    role="implementer",
                    agent="codex",
                    ctx=ctx,
                )
            )
        assert result["status"] == "error"
        assert "required" in result["error"] or "Unknown task_id" in result["error"]
