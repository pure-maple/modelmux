"""Tests for smart routing v3 (keyword + history + benchmark scoring)."""

import json
import tempfile
import time
from pathlib import Path
from unittest import mock

from modelmux.routing import (
    ProviderScore,
    benchmark_scores,
    classify_task,
    keyword_scores,
    history_scores,
    smart_route,
)


def test_keyword_scores_backend_task():
    """Backend-heavy task should score codex highest."""
    scores = keyword_scores("implement a REST API endpoint with database query")
    assert scores["codex"] > scores["gemini"]
    assert scores["codex"] > scores["claude"]


def test_keyword_scores_frontend_task():
    """Frontend-heavy task should score gemini highest."""
    scores = keyword_scores("build a responsive dashboard with React components")
    assert scores["gemini"] > scores["codex"]
    assert scores["gemini"] > scores["claude"]


def test_keyword_scores_review_task():
    """Architecture/review task should score claude highest."""
    scores = keyword_scores("review the security architecture and evaluate trade-offs")
    assert scores["claude"] > scores["codex"]
    assert scores["claude"] > scores["gemini"]


def test_keyword_scores_no_match():
    """No keyword matches should return neutral 0.5 for all."""
    scores = keyword_scores("hello world")
    assert all(v == 0.5 for v in scores.values())


def test_keyword_scores_filter_providers():
    """Should only return scores for requested providers."""
    scores = keyword_scores("implement API", providers=["codex", "gemini"])
    assert "codex" in scores
    assert "gemini" in scores
    assert "claude" not in scores


def test_history_scores_no_history():
    """With no history file, all scores should be neutral."""
    with mock.patch("modelmux.routing._read_history_stats", return_value={}):
        scores = history_scores(["codex", "gemini", "claude"])
        for prov, score in scores.items():
            assert score.success_rate == 0.5
            assert score.latency_score == 0.5
            assert score.history_calls == 0


def test_history_scores_with_data():
    """Providers with history should get data-driven scores."""
    mock_stats = {
        "codex": {"calls": 10, "success": 9, "total_duration": 50.0},
        "gemini": {"calls": 10, "success": 5, "total_duration": 100.0},
    }
    with mock.patch("modelmux.routing._read_history_stats", return_value=mock_stats):
        scores = history_scores(["codex", "gemini", "claude"])
        assert scores["codex"].success_rate == 0.9
        assert scores["gemini"].success_rate == 0.5
        # codex is faster → higher latency score
        assert scores["codex"].latency_score > scores["gemini"].latency_score
        # claude has no history → neutral
        assert scores["claude"].success_rate == 0.5


def test_smart_route_keyword_only():
    """With no history, routing should be keyword-driven."""
    with mock.patch("modelmux.routing._read_history_stats", return_value={}):
        best, scores = smart_route(
            "implement a database migration",
            available_providers=["codex", "gemini", "claude"],
        )
        assert best == "codex"


def test_smart_route_history_boosts():
    """History data should boost a provider over a keyword-neutral task."""
    mock_stats = {
        # gemini has great history
        "gemini": {"calls": 20, "success": 19, "total_duration": 40.0},
        # codex has poor history
        "codex": {"calls": 20, "success": 5, "total_duration": 200.0},
    }
    with mock.patch("modelmux.routing._read_history_stats", return_value=mock_stats):
        # Neutral task (no keyword matches) — history should decide
        best, scores = smart_route(
            "do something interesting",
            available_providers=["codex", "gemini"],
        )
        assert best == "gemini"


def test_smart_route_excludes():
    """Excluded providers should not be candidates."""
    with mock.patch("modelmux.routing._read_history_stats", return_value={}):
        best, scores = smart_route(
            "implement API",
            available_providers=["codex", "gemini", "claude"],
            excluded=["codex"],
        )
        assert best != "codex"


def test_smart_route_single_candidate():
    """Single candidate should always be returned."""
    best, scores = smart_route(
        "anything",
        available_providers=["gemini"],
    )
    assert best == "gemini"
    assert scores["gemini"].composite == 1.0


def test_smart_route_default_on_tie():
    """When all scores are equal, default provider should win."""
    with mock.patch("modelmux.routing._read_history_stats", return_value={}):
        best, _ = smart_route(
            "hello world",
            available_providers=["codex", "gemini", "claude"],
            default="claude",
        )
        assert best == "claude"


def test_provider_score_dataclass():
    """ProviderScore should have all expected fields."""
    score = ProviderScore(
        provider="codex",
        keyword_score=0.8,
        success_rate=0.95,
        latency_score=0.7,
        history_calls=42,
        composite=0.85,
    )
    assert score.provider == "codex"
    assert score.composite == 0.85


# --- Smart routing v3: task classification ---


def test_classify_task_analysis():
    assert classify_task("review this code for security vulnerabilities") == "analysis"


def test_classify_task_generation():
    assert classify_task("implement a REST API endpoint") == "generation"


def test_classify_task_reasoning():
    assert classify_task("explain why this algorithm is O(n log n)") == "reasoning"


def test_classify_task_language():
    assert classify_task("translate the readme to Chinese") == "language"


def test_classify_task_mixed():
    """When multiple categories match, highest wins."""
    result = classify_task("review and analyze the code")
    assert result == "analysis"


def test_classify_task_no_match():
    """No category match returns empty string."""
    assert classify_task("hello") == ""


# --- Smart routing v3: benchmark scores ---


def test_benchmark_scores_no_file():
    """With no benchmark file, all scores should be neutral 0.5."""
    scores = benchmark_scores(
        ["codex", "gemini"], benchmark_path=Path("/nonexistent/path.json")
    )
    assert scores["codex"] == 0.5
    assert scores["gemini"] == 0.5


def test_benchmark_scores_with_data():
    """Benchmark data should produce differentiated scores."""
    data = {
        "results": [
            {"provider": "codex", "category": "analysis", "status": "success",
             "keyword_hits": 4, "keyword_total": 4},
            {"provider": "codex", "category": "analysis", "status": "success",
             "keyword_hits": 3, "keyword_total": 4},
            {"provider": "gemini", "category": "analysis", "status": "success",
             "keyword_hits": 1, "keyword_total": 4},
            {"provider": "gemini", "category": "analysis", "status": "error",
             "keyword_hits": 0, "keyword_total": 4},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        path = Path(f.name)

    try:
        scores = benchmark_scores(["codex", "gemini"], benchmark_path=path)
        assert scores["codex"] > scores["gemini"]
    finally:
        path.unlink()


def test_benchmark_scores_category_filter():
    """Category filter should only use matching results."""
    data = {
        "results": [
            {"provider": "codex", "category": "analysis", "status": "success",
             "keyword_hits": 4, "keyword_total": 4},
            {"provider": "codex", "category": "generation", "status": "error",
             "keyword_hits": 0, "keyword_total": 4},
            {"provider": "gemini", "category": "generation", "status": "success",
             "keyword_hits": 3, "keyword_total": 4},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        path = Path(f.name)

    try:
        # For "generation" category, gemini should beat codex
        scores = benchmark_scores(
            ["codex", "gemini"], category="generation", benchmark_path=path
        )
        assert scores["gemini"] > scores["codex"]

        # For "analysis" category, codex should win
        scores = benchmark_scores(
            ["codex", "gemini"], category="analysis", benchmark_path=path
        )
        assert scores["codex"] > scores["gemini"]
    finally:
        path.unlink()


def test_benchmark_scores_unknown_provider():
    """Provider not in benchmark data gets neutral 0.5."""
    data = {
        "results": [
            {"provider": "codex", "category": "analysis", "status": "success",
             "keyword_hits": 4, "keyword_total": 4},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        path = Path(f.name)

    try:
        scores = benchmark_scores(["codex", "ollama"], benchmark_path=path)
        assert scores["codex"] > 0.5
        assert scores["ollama"] == 0.5
    finally:
        path.unlink()


# --- Smart routing v3: three-signal composite ---


def test_smart_route_benchmark_boosts():
    """Benchmark data should influence routing when history is sparse."""
    bench_data = {
        "results": [
            {"provider": "gemini", "category": "analysis", "status": "success",
             "keyword_hits": 4, "keyword_total": 4},
            {"provider": "gemini", "category": "analysis", "status": "success",
             "keyword_hits": 3, "keyword_total": 4},
            {"provider": "codex", "category": "analysis", "status": "error",
             "keyword_hits": 0, "keyword_total": 4},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(bench_data, f)
        f.flush()
        path = Path(f.name)

    try:
        with mock.patch("modelmux.routing._read_history_stats", return_value={}):
            with mock.patch("modelmux.routing._BENCHMARK_FILE", path):
                best, scores = smart_route(
                    "review this code for security issues",
                    available_providers=["codex", "gemini"],
                )
                # gemini has better benchmark score for analysis tasks
                assert scores["gemini"].benchmark_score > scores["codex"].benchmark_score
    finally:
        path.unlink()


def test_smart_route_task_category_in_scores():
    """Task category should be stored in ProviderScore."""
    with mock.patch("modelmux.routing._read_history_stats", return_value={}):
        _, scores = smart_route(
            "implement a new API endpoint",
            available_providers=["codex", "gemini"],
        )
        for score in scores.values():
            assert score.task_category == "generation"
