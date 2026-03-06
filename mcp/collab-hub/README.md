# collab-hub

Unified MCP server for cross-platform multi-model AI collaboration.

Route tasks to **Codex CLI**, **Gemini CLI**, and **Claude Code CLI** through a single MCP interface with smart routing and caller auto-detection.

## Install

```bash
# One-command install for Claude Code
claude mcp add collab-hub -s user -- uvx collab-hub

# Codex CLI (~/.codex/config.toml)
# [mcp_servers.collab-hub]
# command = "uvx"
# args = ["collab-hub"]

# Gemini CLI (~/.gemini/settings.json)
# {"mcpServers": {"collab-hub": {"command": "uvx", "args": ["collab-hub"]}}}
```

## Tools

- **`collab_dispatch`** — Send a task to a model and get structured results
  - `provider`: `"auto"` / `"codex"` / `"gemini"` / `"claude"`
  - `task`: The prompt to send
  - `workdir`, `sandbox`, `session_id`, `timeout`, `model`, `profile`, `reasoning_effort`
- **`collab_check`** — Check which CLIs are available, show detected caller and config

## Smart Routing

`provider="auto"` routes tasks by keyword analysis and auto-excludes the calling platform:

```
From Claude Code → routes to Codex or Gemini (never back to Claude)
From Codex CLI → routes to Claude or Gemini (never back to Codex)
```

## Audit & Policy

Every dispatch call is logged to `~/.config/collab-hub/audit.jsonl` for debugging and cost tracking.

Policy enforcement via `~/.config/collab-hub/policy.json`:

```json
{
  "blocked_providers": ["gemini"],
  "blocked_sandboxes": ["full"],
  "max_timeout": 600,
  "max_calls_per_hour": 30,
  "max_calls_per_day": 200
}
```

`collab_check()` now shows policy summary and audit stats.

## User Configuration

Create `.collab-hub/profiles.toml` or `~/.config/collab-hub/profiles.toml`:

```toml
[routing]
default_provider = "codex"

[[routing.rules]]
provider = "gemini"
[routing.rules.match]
keywords = ["frontend", "react", "css"]

[profiles.budget]
[profiles.budget.providers.codex]
model = "gpt-4.1-mini"
```

## Links

- [Full Documentation](https://github.com/pure-maple/multi-model-collab)
- [中文文档](https://github.com/pure-maple/multi-model-collab/blob/main/docs/README_CN.md)

## License

MIT
