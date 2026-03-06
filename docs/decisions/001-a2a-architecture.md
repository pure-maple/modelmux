# ADR-001: A2A 协议实现架构

> 状态: 已采纳
> 日期: 2026-03-06
> 参与决策: Claude, Codex (GPT-5.4), Gemini (3.1-pro)

## 背景

modelmux 需要实现真正的多 agent 迭代协作，超越单次 prompt 分发。
Google 的 A2A 协议提供了标准化的 agent-to-agent 通信规范。

## 决策

### 1. 单编排器模式

modelmux 对外暴露为 **一个** A2A agent，内部编排多个 CLI provider。

**理由**: 简化客户端集成。客户端只需知道一个 Agent Card 端点，
不需要理解 codex/gemini/claude 的细节。

**否决方案**: 每个 CLI 独立暴露为 A2A agent — 复杂度过高，
且 CLI 工具是无状态的，不原生支持 A2A 协议。

### 2. MCP + A2A 双传输

引擎层独立于传输，同时通过 MCP (mux_collaborate) 和 A2A HTTP 暴露。

**理由**: MCP 服务现有的 Claude Code/Codex/Gemini 用户，
A2A HTTP 对接任意 A2A 兼容客户端。

### 3. Starlette 作为 HTTP 框架

复用 mcp[cli] 的传递依赖（starlette + uvicorn），零额外依赖。

**理由**: 不增加包体积，starlette 足够轻量且性能优秀。

### 4. 内存 TaskStore

任务状态存储在内存中，上限 1000 个，自动淘汰已完成的旧任务。

**理由**: 简单够用。持久化存储可在需要时添加到 history.jsonl。

## 后果

- 客户端可通过标准 A2A 协议与 modelmux 交互
- 同一个 CollaborationEngine 支撑 MCP 和 HTTP 两种入口
- 无需额外依赖，安装体积不变
