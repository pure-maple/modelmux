"""Tests for the `modelmux dispatch` CLI subcommand."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modelmux.adapters.base import AdapterResult, BaseAdapter


def _make_adapter(available=True, result=None):
    """Create a mock adapter that passes isinstance(x, BaseAdapter)."""
    mock = MagicMock(spec=BaseAdapter)
    mock.check_available.return_value = available
    if result is not None:
        mock.run = AsyncMock(return_value=result)
    return mock


def test_dispatch_no_task_exits(monkeypatch):
    """dispatch with no task and empty stdin should exit 1."""
    from modelmux.cli import _cmd_dispatch

    ns = MagicMock()
    ns.provider = "auto"
    ns.model = ""
    ns.sandbox = "read-only"
    ns.timeout = 300
    ns.workdir = "."
    ns.task = []

    monkeypatch.setattr("sys.stdin", MagicMock(read=MagicMock(return_value="")))

    with pytest.raises(SystemExit) as exc_info:
        _cmd_dispatch(ns)
    assert exc_info.value.code == 1


def test_dispatch_no_providers_exits():
    """dispatch should exit 1 when no providers are available."""
    from modelmux.cli import _cmd_dispatch

    ns = MagicMock()
    ns.provider = "auto"
    ns.model = ""
    ns.sandbox = "read-only"
    ns.timeout = 300
    ns.workdir = "."
    ns.task = ["hello world"]

    mock_adapter = _make_adapter(available=False)

    with (
        patch(
            "modelmux.adapters.get_all_adapters",
            return_value={"codex": mock_adapter},
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        _cmd_dispatch(ns)
    assert exc_info.value.code == 1


def test_dispatch_success(capsys):
    """dispatch should print JSON and exit 0 on success."""
    from modelmux.cli import _cmd_dispatch

    ns = MagicMock()
    ns.provider = "codex"
    ns.model = ""
    ns.sandbox = "read-only"
    ns.timeout = 300
    ns.workdir = "."
    ns.task = ["review", "this", "code"]

    fake_result = AdapterResult(
        run_id="abc123",
        provider="codex",
        status="success",
        output="Looks good!",
        summary="Looks good!",
    )
    mock_adapter = _make_adapter(available=True, result=fake_result)

    with patch(
        "modelmux.adapters.get_all_adapters",
        return_value={"codex": mock_adapter},
    ):
        _cmd_dispatch(ns)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "success"
    assert result["provider"] == "codex"
    assert result["output"] == "Looks good!"


def test_dispatch_auto_routes(capsys):
    """dispatch with provider=auto should call smart_route."""
    from modelmux.cli import _cmd_dispatch

    ns = MagicMock()
    ns.provider = "auto"
    ns.model = ""
    ns.sandbox = "read-only"
    ns.timeout = 300
    ns.workdir = "."
    ns.task = ["analyze architecture"]

    mock_codex = _make_adapter(available=True)
    fake_result = AdapterResult(
        run_id="r1",
        provider="gemini",
        status="success",
        output="Analysis done",
        summary="Analysis done",
    )
    mock_gemini = _make_adapter(available=True, result=fake_result)

    with (
        patch(
            "modelmux.adapters.get_all_adapters",
            return_value={"codex": mock_codex, "gemini": mock_gemini},
        ),
        patch(
            "modelmux.routing.smart_route",
            return_value=("gemini", {}),
        ),
    ):
        _cmd_dispatch(ns)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["provider"] == "gemini"


def test_dispatch_passes_model(capsys):
    """dispatch should pass --model as extra_args."""
    from modelmux.cli import _cmd_dispatch

    ns = MagicMock()
    ns.provider = "codex"
    ns.model = "gpt-5.4"
    ns.sandbox = "read-only"
    ns.timeout = 120
    ns.workdir = "/tmp"
    ns.task = ["test"]

    fake_result = AdapterResult(
        run_id="r2",
        provider="codex",
        status="success",
        output="ok",
    )
    mock_adapter = _make_adapter(available=True, result=fake_result)

    with patch(
        "modelmux.adapters.get_all_adapters",
        return_value={"codex": mock_adapter},
    ):
        _cmd_dispatch(ns)

    call_kwargs = mock_adapter.run.call_args[1]
    assert call_kwargs["extra_args"] == {"model": "gpt-5.4"}
    assert call_kwargs["timeout"] == 120
    assert call_kwargs["workdir"] == "/tmp"


def test_dispatch_error_exits_1(capsys):
    """dispatch should exit 1 on adapter error."""
    from modelmux.cli import _cmd_dispatch

    ns = MagicMock()
    ns.provider = "codex"
    ns.model = ""
    ns.sandbox = "read-only"
    ns.timeout = 300
    ns.workdir = "."
    ns.task = ["fail"]

    fake_result = AdapterResult(
        run_id="r3",
        provider="codex",
        status="error",
        error="something broke",
    )
    mock_adapter = _make_adapter(available=True, result=fake_result)

    with (
        patch(
            "modelmux.adapters.get_all_adapters",
            return_value={"codex": mock_adapter},
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        _cmd_dispatch(ns)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "error"
