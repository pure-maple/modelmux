# Reef Local Tasks

## Active

- [ ] CI 修复后验证: 确认 ruff format 修复后 CI 全绿
- [ ] v0.27.0 发版准备: 创建 docs/releases/v0.27.0.md + 版本号 bump

## Done

- [x] GitHub Actions 集成: composite action + `modelmux dispatch` CLI subcommand + 6 tests
- [x] CHANGELOG 更新: v0.27.0 unreleased section (dispatch CLI, GH Actions, cache, health, config validation)
- [x] Routing history cache: TTL cache for history/benchmark/feedback data (60s)
- [x] Config validation: unknown key warnings + 9 config tests
- [x] mux_check provider latency: last_used_ago + avg_latency + success_rate per provider
- [x] Test coverage: routing v4 four-signal weight paths (90% → 93%)
- [x] CI fix: ruff format all source files

## Backlog

- [ ] Adapter cache thread safety: asyncio.Lock for adapter_cache in server.py (low priority — GIL makes it safe)
- [ ] Dashboard WebSocket 实时更新（替代轮询）
- [ ] mux_dispatch 重试策略增强（指数退避 + 可配置重试次数）
