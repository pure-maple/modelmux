---
name: tmux-multi-model
description: >
  Orchestrate multi-model AI collaboration through tmux, dispatching tasks to
  different AI CLI tools (Codex, Gemini, and any custom model) running in parallel
  or sequential pipelines. Use this skill whenever the user asks for multi-model
  collaboration, cross-model code review, wants a second opinion from another AI,
  needs to compare outputs from different models, mentions "ask Codex/Gemini",
  or when a task would clearly benefit from leveraging multiple AI models'
  complementary strengths — even if they don't explicitly request it.
---

# Multi-Model Collaboration via tmux

This skill enables Claude to orchestrate multiple AI CLI tools (Codex, Gemini, etc.)
running in tmux sessions, combining each model's strengths for better results.

## Prerequisites

Before using this skill, ensure the following are installed:
- **tmux** — `brew install tmux` (macOS) or `apt install tmux` (Linux)
- At least one supported model CLI (see Model Adapters section)

Run `scripts/check_prereqs.sh` from the skill directory to verify readiness.

## Core Concepts

### Why Multi-Model Collaboration?

Different models excel at different things:
- **Codex** — Strong at code generation, algorithm implementation, bug fixes
- **Gemini** — Good at frontend design, multimodal tasks, broad knowledge
- **Claude** (you) — Architecture, reasoning, synthesis, code review

By combining these strengths, you produce better results than any single model alone.

### Architecture Overview

```
Claude Code (orchestrator)
    │
    ├── tmux session: "ai-collab-{timestamp}"
    │   ├── window "task-1": codex exec -p "..." > output
    │   ├── window "task-2": gemini -p "..." > output
    │   └── window "task-N": ...
    │
    ├── /tmp/ai-collab/{session}/  (output files)
    │   ├── task-1.json
    │   ├── task-2.json
    │   └── ...
    │
    └── Claude synthesizes all outputs
```

## Workflow Modes

### Mode 1: Parallel Fan-Out

Use when tasks are independent and you want speed. Send the same or different
prompts to multiple models simultaneously, then synthesize results.

**When to use**: Code review, getting multiple perspectives, comparing approaches,
independent subtasks of a larger project.

**Steps**:
1. Start a collaboration session
2. Dispatch tasks to multiple models in parallel
3. Poll for completion
4. Collect and synthesize all outputs
5. Clean up the session

### Mode 2: Sequential Pipeline

Use when each step depends on the previous one's output. Chain models in sequence,
passing each output as context to the next.

**When to use**: Code generation → review → refinement, research → implementation,
design → coding → testing.

**Steps**:
1. Start a collaboration session
2. Dispatch to first model, wait for result
3. Feed result into next model's prompt
4. Repeat until pipeline is complete
5. Synthesize final output and clean up

### Mode 3: Consensus / Best-of-N

Send the same task to multiple models, compare outputs, pick the best or merge them.

**When to use**: Critical code where correctness matters, exploring different
implementation strategies, when you're unsure which approach is best.

## How to Execute

All scripts are in the `scripts/` directory relative to this SKILL.md file.
Determine the skill directory path first by noting where this file was loaded from.

### Step 1: Start a Session

```bash
bash <skill-dir>/scripts/session.sh start [session-name]
```

This creates a tmux session and the output directory. Returns the session ID.

### Step 2: Dispatch Tasks

```bash
# Dispatch to a specific model
bash <skill-dir>/scripts/dispatch.sh \
  --session <session-id> \
  --model codex \
  --prompt "Implement a binary search tree in Python" \
  --workdir /path/to/project \
  --task-name "impl-bst"

# Dispatch to another model in parallel
bash <skill-dir>/scripts/dispatch.sh \
  --session <session-id> \
  --model gemini \
  --prompt "Review this binary search tree implementation" \
  --workdir /path/to/project \
  --task-name "review-bst" \
  --context-file /path/to/bst.py
```

Key parameters:
- `--model`: Which model adapter to use (codex, gemini, or any custom adapter)
- `--prompt`: The task description
- `--workdir`: Working directory for the model
- `--task-name`: Human-readable name for tracking
- `--context-file`: (optional) File to include as context
- `--sandbox`: (optional) Sandbox level for codex: read-only|workspace-write|full-access
- `--extra-args`: (optional) Pass-through args to the underlying CLI

### Step 3: Monitor and Collect

```bash
# Check status of all tasks
bash <skill-dir>/scripts/collect.sh --session <session-id> --status

# Wait for a specific task and get output
bash <skill-dir>/scripts/collect.sh --session <session-id> --task <task-name> --wait

# Collect all completed outputs
bash <skill-dir>/scripts/collect.sh --session <session-id> --all
```

Each collected output is a JSON object:
```json
{
  "task_name": "impl-bst",
  "model": "codex",
  "status": "completed",
  "exit_code": 0,
  "duration_seconds": 15,
  "output": "... model response ...",
  "prompt": "... original prompt ..."
}
```

### Step 4: Synthesize

After collecting outputs from all models, synthesize the results yourself:
- Compare approaches and pick the best parts from each
- Identify disagreements between models — these are areas worth extra scrutiny
- Present a unified result to the user with attribution

### Step 5: Clean Up

```bash
bash <skill-dir>/scripts/session.sh stop <session-id>
```

This kills the tmux session and optionally cleans up temp files.

## Model Adapters

Each model is supported through an adapter script in `scripts/adapters/`.
The skill ships with adapters for:

| Model | Adapter | CLI Command | Install |
|-------|---------|-------------|---------|
| Codex | `codex.sh` | `codex exec` | `npm i -g @openai/codex` |
| Gemini | `gemini.sh` | `gemini` | `npm i -g @anthropic/gemini-cli` or see Gemini docs |

To add a new model, copy `scripts/adapters/_template.sh` and implement the
required functions. See `references/adding-models.md` for the full guide.

## Decision Guidelines

Use this table to decide when to invoke multi-model collaboration:

| Scenario | Recommended Mode | Models |
|----------|-----------------|--------|
| Code generation + review | Sequential | Codex → Claude review |
| Multiple implementation approaches | Parallel | Codex + Gemini |
| Critical bugfix | Consensus | All available models |
| Frontend + backend split | Parallel | Gemini (frontend) + Codex (backend) |
| Quick second opinion | Parallel (single) | Whichever model is most relevant |

## Error Handling

- If tmux is not installed, inform the user and suggest `brew install tmux`
- If a model CLI is not found, skip it and report which models are available
- If a task times out (default: 5 minutes), kill it and report partial output
- If a model returns an error, capture the error and include it in the synthesis

## Important Notes

- Always clean up tmux sessions when done — stale sessions waste resources
- The user can observe model outputs in real-time by running `tmux attach -t <session-id>`
- Output files are stored in `/tmp/ai-collab/` and cleaned up with the session
- For large codebases, prefer passing specific files via `--context-file` rather than
  letting models scan the entire project
