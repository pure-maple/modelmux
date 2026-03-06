# A2A 协议调研与竞品分析

> 调研时间: 2026-03-06
> 参与模型: Claude (Opus 4.6), Codex (GPT-5.4 xhigh), Gemini (3.1-pro-preview)

## 1. A2A 协议概述

Google 发起的 Agent-to-Agent (A2A) 协议，现已移交 Linux Foundation。

### 核心概念

| 概念 | 说明 |
|------|------|
| **AgentCard** | Agent 的"名片"，描述身份、能力、端点、支持的特性 |
| **Task** | 生命周期: submitted → working → input-required → completed/failed/canceled |
| **contextId** | 跨消息维持会话上下文 |
| **Message** | 包含 role (user/agent) 和 Parts |
| **Part** | 最小内容单元: text/file/data |
| **Artifact** | Agent 产出的有形输出 |
| **SSE Streaming** | tasks/sendSubscribe 实时推送 |

### MCP vs A2A

| 维度 | MCP | A2A |
|------|-----|-----|
| 方向 | 垂直: Agent → Tool | 水平: Agent → Agent |
| 协议 | stdio/HTTP | HTTP + JSON-RPC 2.0 |
| 状态 | 无状态 | 有状态 (Task 生命周期) |
| 发现 | MCP Registry | /.well-known/agent.json |

**关键洞察**: MCP 和 A2A 互补而非竞争。modelmux 同时支持两种传输。

## 2. 竞品分析

### 直接竞品 (2026-03-06 调研)

| 项目 | 描述 | A2A 支持 | 迭代协作 | 差异化评估 |
|------|------|---------|---------|-----------|
| **multicli** | npm 包，多 CLI 并发分发 | 无 | 无 | 纯分发，无编排 |
| **claude_code_bridge** | Claude Code 的 MCP bridge | 无 | 无 | 单 provider 封装 |
| **agent-mux** (Nick Oak) | 类似名字的 AI multiplexer | 无 | 无 | 概念原型，未实现协作 |
| **CAO** (AWS) | Claude Agent Orchestrator | 无 | 部分 | AWS 生态绑定 |
| **Claude Code Agentrooms** | 多 agent 房间概念 | 无 | 概念 | 社区实验，非生产就绪 |
| **cmux** | CLI multiplexer | 无 | 无 | 终端复用器，非 AI 协作 |

### 结论

**截至 2026-03-06，没有任何项目实现了：**
1. 基于 A2A 协议的真正多 agent 迭代协作
2. 跨 CLI 工具的统一编排（codex + gemini + claude）
3. 收敛检测 + 分层上下文管理
4. MCP + A2A 双传输支持

**modelmux 是首个实现 A2A 协议核心能力的多模型协作项目。**

## 3. 架构决策

### 分层上下文管理

三个模型一致同意采用四层记忆策略:

1. **固定记忆** (Pinned Facts): 目标、约束、验收标准 — 永不裁剪
2. **滚动摘要** (Rolling Summary): 早期 turns 的结构化压缩
3. **最近原文窗口** (Recent Window): 最近 1-2 轮的完整输出
4. **工件索引** (Artifact Index): hash + summary 的轻量引用

### 四层收敛检测

1. **硬限制**: 最大轮次、最大时间、连续失败
2. **结构化信号**: CONVERGED/LGTM/APPROVED 和 blocking issue 正则匹配
3. **稳定性检测**: 工件 hash 跨轮次不变 → 输出已稳定
4. **LLM 裁判**: 模糊场景的最终裁决（昂贵，仅在前三层无结论时使用）

### 单编排器架构

modelmux 对外暴露为一个 A2A agent（而非每个 CLI 独立暴露），内部编排多个 provider。
理由: 简化客户端集成，统一 Agent Card，内部灵活调度。

## 4. 协作模式

| 模式 | 流程 | 适用场景 |
|------|------|---------|
| **Review** | 实现 → 审查 → 修订 循环 | 代码实现、文档撰写 |
| **Consensus** | 多视角并行分析 + 合成 | 技术选型、架构评审 |
| **Debate** | 正方 vs 反方 + 仲裁 | 争议决策、风险评估 |

## 5. 实现里程碑

- **v0.18.0**: A2A 核心引擎 (types, context, convergence, patterns, engine)
  - 23 个测试，3 种协作模式
- **v0.19.0**: A2A HTTP Server (Agent Card, JSON-RPC 2.0, SSE, TaskStore)
  - 17 个新测试，CLI 子命令 `modelmux a2a-server`
