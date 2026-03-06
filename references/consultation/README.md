# Architecture Consultation Summary

modelmux's architecture was designed through multi-model consultation with three AI platforms. This document captures the key recommendations that shaped the project.

## Participants

| Model | Role |
|-------|------|
| **Claude Opus 4.6** | Original proposal, synthesis, implementation |
| **GPT-5.3 (Codex)** | Architecture review, code-level recommendations |
| **Gemini 3.1 Pro Preview** | Protocol analysis, A2A backbone design |

## Key Recommendations

### From Codex (GPT)

1. **Unified Hub over Separate Bridges** — One MCP server managing all providers, not 3 independent bridge servers. Simplifies deployment and enables cross-provider features (routing, failover, comparison).

2. **Policy Engine** — OPA-inspired policy enforcement for rate limits, provider blocking, and sandbox restrictions. Implemented as `policy.py`.

3. **Canonical Output Schema** — All adapters return the same `AdapterResult` structure regardless of provider, enabling uniform downstream processing.

### From Gemini

1. **A2A Protocol Backbone** — Use Google's Agent-to-Agent protocol for multi-agent collaboration, not just MCP tool calls. Enables iterative review loops and convergence detection.

2. **MCP Gateway Pattern** — The MCP server acts as a permission gateway. Subprocess calls made by the server bypass the client's permission system, solving the "approval storm" problem.

3. **Conductor Shared State** — Layered context management (pinned facts + rolling summary + recent window) for multi-turn collaboration sessions.

### Community Analysis

The project studied existing implementations including:
- [codexmcp](https://github.com/GuDaStudio/codexmcp) — Codex CLI → MCP bridge patterns
- [geminimcp](https://github.com/GuDaStudio/geminimcp) — Gemini CLI → MCP bridge patterns
- [skills](https://github.com/GuDaStudio/skills) — Agent Skills structure and RPI workflow

Key takeaway: these projects each bridge a single model. modelmux unifies them into one hub with cross-model orchestration capabilities.

## Consensus Decisions

1. **One unified MCP hub** (not N separate bridges)
2. **MCP-first** (bypass Bash permission issues)
3. **Canonical output schema** for standardized results
4. **Session continuity** via native CLI session IDs
5. **Code sovereignty** — external model outputs are prototypes, reviewed before applying
6. **A2A for collaboration** — iterative multi-agent patterns beyond simple dispatch
