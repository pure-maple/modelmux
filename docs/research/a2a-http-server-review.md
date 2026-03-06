# A2A HTTP Server Code Review Summary

**Date**: 2026-03-06
**Version**: v0.19.0
**File**: `mcp/modelmux/src/modelmux/a2a/http_server.py`
**Reviewers**: Gemini (gemini-2.5-pro), Codex (gpt-5.4, incomplete)

## Review Findings

### CRITICAL

| Issue | Status | Resolution |
|-------|--------|------------|
| Non-functional Cancellation | Fixed | `cancel_event` propagated from HTTP handler through EngineConfig to CollaborationEngine main loop |
| Missing Dependencies in pyproject.toml | Fixed | `starlette`/`uvicorn` transitive via `mcp[cli]`; `sse-starlette` added as `[a2a]` optional dep |

### MAJOR

| Issue | Status | Resolution |
|-------|--------|------------|
| No CORS Support | Fixed | `CORSMiddleware` added to Starlette app |
| Lack of Authentication | Fixed | Bearer token auth with `hmac.compare_digest` constant-time comparison |
| Zombie Tasks on Disconnect | Fixed | `CancelledError` handling in SSE generator cancels background `collab_future` |
| Information Leakage | Fixed | Generic "Internal server error" message instead of `str(e)` |
| Hardcoded Defaults | Fixed | `TaskParams` dataclass with configurable `timeout_per_turn` per request; `_create_engine` accepts and wires the param |
| No Persistence (TaskStore) | Deferred | In-memory is acceptable for v0.19.0; persistence planned for later version |

### MINOR

| Issue | Status | Notes |
|-------|--------|-------|
| Missing Optional Metadata in AgentCard | Partial | `authSchemes` conditionally included; other optional fields deferred |
| Task Event Naming (SSE) | Accepted | Using `task/status`, `task/progress` which matches Google A2A reference impl |
| Blocking `tasks/send` | Accepted | Standard A2A behavior; `tasks/sendSubscribe` available for long-running tasks |
| TaskStore Concurrency | Accepted | Single asyncio loop is thread-safe enough; no multi-threaded deployment planned |
| Dependency Management (sse_starlette) | Fixed | Added to `[project.optional-dependencies] a2a` |

### SUGGESTIONS

| Issue | Status | Notes |
|-------|--------|-------|
| Rate Limiting | Deferred | Compute-heavy operations warrant rate limiting; planned for production hardening phase |
| Health Check Endpoint | Fixed | `GET /health` returns `{"status": "ok", "version": ...}` |
| Robust Parameter Extraction | Fixed | `_extract_task_params` now returns structured `TaskParams` dataclass with validation |

## Key Architectural Decisions

1. **Auth model**: Bearer token (env var or CLI flag), constant-time comparison. Agent Card endpoint always open per A2A spec.
2. **Cancellation**: `asyncio.Event` propagated through entire chain: HTTP handler -> TaskStore entry -> EngineConfig -> Engine main loop.
3. **SSE zombie prevention**: `CancelledError` in SSE generator triggers `collab_future.cancel()` + state update.
4. **Timeout configurability**: Per-request `timeout_per_turn` via metadata, with 600s server default fallback.

## Lessons Learned

- Gemini's review was thorough and actionable — all CRITICAL/MAJOR issues were valid
- Codex review failed because source wasn't pushed to GitHub yet (it tried web search)
- For future reviews: push code first, or provide source inline in the prompt
