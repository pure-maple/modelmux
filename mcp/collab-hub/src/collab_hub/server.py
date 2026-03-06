"""Unified MCP server for multi-model AI collaboration.

Exposes tools that route tasks to Codex CLI, Gemini CLI, or Claude Code CLI,
returning results in a canonical schema. Supports user-defined profiles for
third-party model configuration and custom routing rules.

Architecture: One hub, multiple internal adapters.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from collab_hub.adapters import ADAPTERS, BaseAdapter
from collab_hub.config import (
    CollabConfig,
    get_active_profile,
    load_config,
    route_by_rules,
)

mcp = FastMCP(
    "collab-hub",
    instructions=(
        "Multi-model AI collaboration hub. Use collab_dispatch to send "
        "tasks to different AI models (codex, gemini, claude) and receive "
        "structured results. Use provider='auto' for smart routing. "
        "Supports profiles for third-party model configuration and "
        "session continuity for multi-turn conversations."
    ),
)

# Adapter instances (lazy-initialized)
_adapter_cache: dict[str, BaseAdapter] = {}

# Built-in auto-routing keyword patterns (fallback when no custom rules)
_ROUTE_PATTERNS: dict[str, list[re.Pattern]] = {
    "gemini": [
        re.compile(r"\b(frontend|ui|ux|css|html|react|vue|svelte|angular|tailwind|"
                   r"component|layout|responsive|style|theme|dashboard|"
                   r"page|widget|modal|button|form|animation|figma|"
                   r"visual|color|font|icon|image|illustration)\b", re.I),
    ],
    "codex": [
        re.compile(r"\b(implement|algorithm|backend|api|endpoint|database|sql|"
                   r"debug|fix|bug|optimize|refactor|function|class|test|"
                   r"server|middleware|auth|crud|migration|schema|query|"
                   r"sort|search|tree|graph|linked.?list|hash|cache)\b", re.I),
    ],
    "claude": [
        re.compile(r"\b(architect|design.?pattern|review|analyze|explain|"
                   r"trade.?off|compare|evaluate|plan|strategy|"
                   r"security|audit|vulnerabilit|threat|"
                   r"documentation|spec|rfc|adr|critique)\b", re.I),
    ],
}


def _builtin_auto_route(task: str) -> str:
    """Built-in keyword routing (fallback when no custom rules)."""
    scores: dict[str, int] = {}
    for provider, patterns in _ROUTE_PATTERNS.items():
        score = sum(len(p.findall(task)) for p in patterns)
        scores[provider] = score

    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "codex"
    return best


def _auto_route(task: str, config: CollabConfig) -> str:
    """Route using custom rules first, then built-in patterns as fallback."""
    if config.routing_rules:
        result = route_by_rules(
            task, config.routing_rules, config.default_provider
        )
        if result:
            return result

    return _builtin_auto_route(task)


def _get_adapter(provider: str) -> BaseAdapter:
    if provider not in _adapter_cache:
        cls = ADAPTERS.get(provider)
        if cls is None:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {', '.join(ADAPTERS.keys())}"
            )
        _adapter_cache[provider] = cls()
    return _adapter_cache[provider]


@mcp.tool()
async def collab_dispatch(
    provider: Literal["auto", "codex", "gemini", "claude"],
    task: str,
    workdir: str = ".",
    sandbox: Literal["read-only", "write", "full"] = "read-only",
    session_id: str = "",
    timeout: int = 300,
    model: str = "",
    profile: str = "",
    reasoning_effort: str = "",
) -> str:
    """Dispatch a task to an AI model CLI and return the result.

    Args:
        provider: Which model to use — "auto" (smart routing based on task
            and user config), "codex" (code generation, algorithms, debugging),
            "gemini" (frontend, design, multimodal), or "claude" (architecture,
            reasoning, review).
        task: The task description / prompt to send to the model.
        workdir: Working directory for the model to operate in.
        sandbox: Security level — "read-only" (default, safe), "write"
            (can modify files), "full" (unrestricted, dangerous).
        session_id: Resume a previous session for multi-turn conversation.
            Pass the session_id from a previous result to continue.
        timeout: Maximum seconds to wait (default 300).
        model: Override the specific model version (e.g., "gpt-5.4",
            "gemini-2.5-pro", "claude-sonnet-4-6"). If empty, uses
            the CLI's default or the active profile's model setting.
        profile: Named profile from user config (e.g., "budget", "china").
            Overrides active_profile from config file. Controls which
            model/provider/base_url to use for each CLI.
        reasoning_effort: Codex reasoning effort level — "low", "medium",
            "high", "xhigh". Only applies to provider="codex".
    """
    # Load user configuration
    resolved_workdir = str(Path(workdir).resolve())
    config = load_config(resolved_workdir)

    # Determine which profile to use
    profile_name = profile or config.active_profile
    active_prof = config.profiles.get(profile_name)

    # Auto-route if needed
    actual_provider = provider
    if provider == "auto":
        actual_provider = _auto_route(task, config)
        # Skip disabled providers
        if actual_provider in config.disabled_providers:
            for alt in ["codex", "gemini", "claude"]:
                if alt != actual_provider and alt not in config.disabled_providers:
                    actual_provider = alt
                    break

    adapter = _get_adapter(actual_provider)

    if not adapter.check_available():
        if provider == "auto":
            for fallback in ["codex", "gemini", "claude"]:
                if fallback != actual_provider:
                    fb_adapter = _get_adapter(fallback)
                    if fb_adapter.check_available():
                        actual_provider = fallback
                        adapter = fb_adapter
                        break
            else:
                return json.dumps({
                    "run_id": "",
                    "provider": actual_provider,
                    "status": "error",
                    "error": "No model CLIs available on PATH.",
                }, indent=2)
        else:
            return json.dumps({
                "run_id": "",
                "provider": actual_provider,
                "status": "error",
                "error": (
                    f"{actual_provider} CLI is not installed or not on PATH. "
                    f"Please install it first."
                ),
            }, indent=2)

    # Build extra_args from explicit params + profile
    extra_args: dict = {}
    env_overrides: dict[str, str] = {}

    # Apply profile settings
    if active_prof:
        provider_conf = active_prof.providers.get(actual_provider)
        if provider_conf:
            if provider_conf.model and not model:
                extra_args["model"] = provider_conf.model
            if provider_conf.wire_api:
                extra_args["wire_api"] = provider_conf.wire_api
            env_overrides = provider_conf.to_env_overrides(actual_provider)

    # Explicit params override profile
    if model:
        extra_args["model"] = model
    if profile and actual_provider == "codex":
        extra_args["profile"] = profile
    if reasoning_effort:
        extra_args["reasoning_effort"] = reasoning_effort

    result = await adapter.run(
        prompt=task,
        workdir=resolved_workdir,
        sandbox=sandbox,
        session_id=session_id,
        timeout=timeout,
        extra_args=extra_args if extra_args else None,
        env_overrides=env_overrides if env_overrides else None,
    )

    result_dict = result.to_dict()
    if provider == "auto":
        result_dict["routed_from"] = "auto"
    if profile_name != "default" and active_prof:
        result_dict["profile"] = profile_name
    return json.dumps(result_dict, indent=2, ensure_ascii=False)


@mcp.tool()
async def collab_check() -> str:
    """Check which model CLIs are available and show active configuration.

    Returns availability status for codex, gemini, and claude CLIs,
    plus the active profile name and available profiles.
    """
    config = load_config(".")

    status: dict = {}
    for name, cls in ADAPTERS.items():
        adapter = cls()
        status[name] = {
            "available": adapter.check_available(),
            "binary": adapter._binary_name(),
        }

    status["_config"] = {
        "active_profile": config.active_profile,
        "available_profiles": list(config.profiles.keys()) or ["default (built-in)"],
        "custom_routing_rules": len(config.routing_rules),
        "disabled_providers": config.disabled_providers,
    }

    return json.dumps(status, indent=2)
