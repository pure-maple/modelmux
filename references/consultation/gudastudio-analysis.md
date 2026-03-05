# GuDaStudio 四项目深度分析

## 项目全景

| 项目 | Stars | 定位 | 核心技术 | 行数 |
|------|-------|------|---------|------|
| **codexmcp** | 1,654 | Codex CLI → MCP Server | Python/FastMCP | ~250 行 |
| **geminimcp** | 287 | Gemini CLI → MCP Server | Python/FastMCP | ~200 行 |
| **skills** | 1,847 | Claude Code Agent Skills 集合 | SKILL.md + Python bridge | ~500 行 |
| **commands** | 833 | Claude Code 自定义斜杠命令 | Markdown + OpenSpec | 4 个命令文件 |

## 架构层次关系

```
commands (最高层: RPI 工作流编排)
  ├── /gudaspec:research  → 使用 Auggie MCP + 子 agent 探索
  ├── /gudaspec:plan      → 使用 codexmcp + geminimcp 交叉验证
  └── /gudaspec:implementation → 路由任务到 codex/gemini MCP
         │
skills (中间层: Skill 标准封装)
  ├── collaborating-with-codex/SKILL.md
  └── collaborating-with-gemini/SKILL.md
         │
codexmcp / geminimcp (底层: MCP 桥接)
  ├── codex MCP tool → subprocess: codex exec --json
  └── gemini MCP tool → subprocess: gemini -p -o stream-json
```

## 关键设计模式

### 1. 线程化队列子进程模式（两个 MCP 项目共享）

```python
# 核心模式：两个项目都使用相同架构
output_queue: queue.Queue[str | None] = queue.Queue()

def read_output() -> None:
    for line in iter(process.stdout.readline, ""):
        output_queue.put(line.strip())
        if is_turn_completed(line):
            time.sleep(0.3)  # Grace period
            process.terminate()
            break
    output_queue.put(None)  # Sentinel

# 背景线程 + 前台 async 消费
thread = Thread(target=read_output, daemon=True)
thread.start()
```

### 2. turn.completed 事件检测

```python
def is_turn_completed(line: str) -> bool:
    try:
        data = json.loads(line)
        return data.get("type") == "turn.completed"
    except (json.JSONDecodeError, AttributeError, TypeError):
        return False
```

### 3. Session 连续性

- **Codex**: `thread_id` 从 JSONL 提取 → `codex exec resume <SESSION_ID>`
- **Gemini**: `session_id` 从 JSON 提取 → `gemini --resume <SESSION_ID>`
- 两者都通过 MCP 返回值传递 SESSION_ID，实现多轮对话

### 4. Code Sovereignty（代码主权）

skills 和 commands 都强制执行：
- 外部模型**只能返回 Unified Diff Patches**
- 外部模型**不可写入文件系统**（sandbox 模式）
- Claude **必须重写**外部模型的代码再应用
- 形成 "原型 → 审查 → 重写" 三步流程

### 5. RPI 工作流理论（commands 项目）

```
Phase 1: Research（研究）
  - 将需求转化为约束集
  - 子 agent 按代码上下文边界划分（非角色划分）
  - 使用 Auggie MCP 进行代码库检索
  ↓ /clear（清理上下文，防止超过 80K 有效窗口）

Phase 2: Plan（计划）
  - 消除所有歧义 → 零决策执行计划
  - Codex + Gemini 交叉检测隐含假设
  - 提取 Property-Based Testing 属性
  - 反模式检测："to be determined" = 不可接受
  ↓ /clear

Phase 3: Implementation（实现）
  - 纯机械执行，所有决策已在 Plan 阶段完成
  - 前端 → Gemini, 后端 → Codex
  - Dual-model LGTM 双模型审批
```

### 6. 多模型路由策略

| 任务类型 | 路由目标 | 原因 |
|---------|---------|------|
| 前端/UI/CSS/React/Vue | Gemini | 设计感和多模态能力 |
| 后端/算法/逻辑/调试 | Codex | 代码生成和逻辑推理 |
| 架构/集成/审查/重写 | Claude | 推理、综合、质量把控 |
| 分析阶段 | 同时两者 | 交叉验证，消除盲点 |
| 审计阶段 | 同时两者 | Dual LGTM 双审批 |

## codexmcp 技术细节

### MCP Tool 参数

```python
@mcp.tool()
async def codex(
    PROMPT: str,           # 任务指令
    cd: Path,              # 工作目录
    sandbox: Literal["read-only","workspace-write","danger-full-access"] = "read-only",
    SESSION_ID: str = "",  # 恢复会话
    skip_git_repo_check: bool = True,
    return_all_messages: bool = False,
    image: list[Path] = [],     # 图片附件
    model: str = "",
    yolo: bool = False,         # 跳过所有审批
    profile: str = ""           # config.toml profile
):
```

### 命令构造

```python
cmd = ["codex", "exec", "--sandbox", sandbox, "--cd", str(cd), "--json"]
if SESSION_ID:
    cmd.extend(["resume", str(SESSION_ID)])
cmd += ['--', PROMPT]
```

### 安装

```bash
claude mcp add codex -s user --transport stdio -- \
  uvx --from git+https://github.com/GuDaStudio/codexmcp.git codexmcp
```

## geminimcp 技术细节

### MCP Tool 参数

```python
@mcp.tool()
async def gemini(
    PROMPT: str,
    cd: Path,
    sandbox: bool = False,
    SESSION_ID: str = "",
    return_all_messages: bool = False,
    model: str = ""
):
```

### 命令构造

```python
cmd = ["gemini", "--prompt", PROMPT, "-o", "stream-json"]
if sandbox:
    cmd.extend(["--sandbox"])
if SESSION_ID:
    cmd.extend(["--resume", SESSION_ID])
```

### 安装

```bash
claude mcp add gemini -s user --transport stdio -- \
  uvx --from git+https://github.com/GuDaStudio/geminimcp.git geminimcp
```

## skills 项目结构

```
skills/
  collaborating-with-codex/     # git submodule
    SKILL.md                    # YAML frontmatter + Markdown
    scripts/
      codex_bridge.py           # Python subprocess bridge
  collaborating-with-gemini/    # git submodule
    SKILL.md
    scripts/
      gemini_bridge.py
  install.sh                    # Bash installer
  install.ps1                   # PowerShell installer
```

### SKILL.md 格式

```yaml
---
name: collaborating-with-codex
description: Delegates coding tasks to Codex CLI for prototyping, debugging, and code review.
---

# Skill Documentation
## Quick Start
## Parameters
## Multi-turn Sessions
## Common Usage Patterns
```

## commands 项目结构

```
commands/
  gudaspec/
    init.md              # /gudaspec:init
    research.md          # /gudaspec:research
    plan.md              # /gudaspec:plan
    implementation.md    # /gudaspec:implementation
  install.sh
  install.ps1
```

### Command 文件格式

```yaml
---
name: GudaSpec: Plan
description: Refine proposals into zero-decision executable task flows
category: GudaSpec
tags: [gudaspec, plan, multi-model, pbt]
allowed-tools: Bash(openspec:*), mcp__codex__codex, mcp__gemini__gemini
argument-hint: [proposal_id]
---

# Guardrails
# Steps
# Reference
# Exit Criteria
```

## 对我们项目的启示

### 应采纳的设计

1. **FastMCP + subprocess 模式** — 已被两个 MCP 项目验证，简单可靠
2. **turn.completed 检测** — 关键的子进程生命周期管理模式
3. **Session 连续性** — 多轮对话的 SESSION_ID 传递机制
4. **Code Sovereignty** — 安全模型，外部模型不可直接写入
5. **RPI 工作流** — 分阶段执行 + 上下文管理是成熟的编排模式
6. **双模型审批** — Dual LGTM 提升代码质量的有效机制
7. **约束集驱动** — 用约束集而非信息堆砌来指导决策

### 应改进的方面

1. **无统一 Hub** — 各项目独立，缺乏统一调度和输出标准化
2. **无超时机制** — codexmcp/geminimcp 主线均无超时（PR #8 添加中）
3. **无测试/CI** — 所有项目都缺乏自动化测试
4. **Claude-only** — 仅从 Claude Code 调用，不支持反向调用或跨平台
5. **无策略引擎** — 安全规则内嵌在 prompt 中，非程序化执行
6. **Windows 问题多** — 多个 open issues 涉及 Windows 兼容性

### 架构定位差异

```
GuDaStudio 方案:
  Claude Code → codexmcp (MCP) → codex exec
  Claude Code → geminimcp (MCP) → gemini -p
  单向调用，Claude 始终为主控

我们的目标:
  任意平台 → collab-hub (统一 MCP) → {codex, gemini, claude}
  双向可调，任何 MCP 客户端都可以是主控
```
