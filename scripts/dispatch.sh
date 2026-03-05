#!/usr/bin/env bash
# dispatch.sh — Dispatch a task to a model CLI via tmux
# Usage:
#   dispatch.sh --session <id> --model <name> --prompt "task" [options]
#
# Options:
#   --session <id>        tmux session ID (required)
#   --model <name>        Model adapter name: codex, gemini, etc. (required)
#   --prompt <text>       Task prompt (required)
#   --workdir <path>      Working directory for the model (default: cwd)
#   --task-name <name>    Human-readable task name (default: auto-generated)
#   --context-file <path> File to include as context
#   --sandbox <level>     Sandbox level for codex (default: read-only)
#   --timeout <seconds>   Max execution time (default: 300)
#   --extra-args <args>   Extra arguments to pass to the CLI

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLAB_DIR="/tmp/ai-collab"

# Parse arguments
SESSION_ID=""
MODEL=""
PROMPT=""
WORKDIR="$(pwd)"
TASK_NAME=""
CONTEXT_FILE=""
SANDBOX="read-only"
TIMEOUT=300
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --session)     SESSION_ID="$2"; shift 2 ;;
        --model)       MODEL="$2"; shift 2 ;;
        --prompt)      PROMPT="$2"; shift 2 ;;
        --workdir)     WORKDIR="$2"; shift 2 ;;
        --task-name)   TASK_NAME="$2"; shift 2 ;;
        --context-file) CONTEXT_FILE="$2"; shift 2 ;;
        --sandbox)     SANDBOX="$2"; shift 2 ;;
        --timeout)     TIMEOUT="$2"; shift 2 ;;
        --extra-args)  EXTRA_ARGS="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# Validate required params
if [ -z "${SESSION_ID}" ] || [ -z "${MODEL}" ] || [ -z "${PROMPT}" ]; then
    echo '{"error": "Required: --session, --model, --prompt"}' >&2
    exit 1
fi

# Check session exists
if ! tmux has-session -t "${SESSION_ID}" 2>/dev/null; then
    echo '{"error": "Session not found: '"${SESSION_ID}"'"}' >&2
    exit 1
fi

# Check adapter exists
ADAPTER="${SCRIPT_DIR}/adapters/${MODEL}.sh"
if [ ! -f "${ADAPTER}" ]; then
    echo '{"error": "No adapter found for model: '"${MODEL}"'. Available adapters:"}' >&2
    ls "${SCRIPT_DIR}/adapters/"*.sh 2>/dev/null | grep -v _template | sed 's/.*\//  /' | sed 's/\.sh$//' >&2
    exit 1
fi

# Generate task name if not provided
if [ -z "${TASK_NAME}" ]; then
    TASK_NAME="${MODEL}-$(date +%s)-$$"
fi

# Setup output paths
WORK_DIR="${COLLAB_DIR}/${SESSION_ID}"
OUTPUT_FILE="${WORK_DIR}/task-${TASK_NAME}.output"
META_FILE="${WORK_DIR}/task-${TASK_NAME}.json"
DONE_MARKER="${WORK_DIR}/task-${TASK_NAME}.done"

# Prepare context
CONTEXT=""
if [ -n "${CONTEXT_FILE}" ] && [ -f "${CONTEXT_FILE}" ]; then
    CONTEXT=$(cat "${CONTEXT_FILE}")
fi

# Build the full prompt with context
FULL_PROMPT="${PROMPT}"
if [ -n "${CONTEXT}" ]; then
    FULL_PROMPT="Context from file ${CONTEXT_FILE}:
---
${CONTEXT}
---

Task: ${PROMPT}"
fi

# Source the adapter to get the command
# Adapter must define: build_command() that sets CMD_ARRAY
source "${ADAPTER}"

# Build the model-specific command
CMD=$(build_command "${FULL_PROMPT}" "${WORKDIR}" "${SANDBOX}" "${EXTRA_ARGS}")

# Write task metadata
START_TIME=$(date +%s)
cat > "${META_FILE}" <<EOF
{
    "task_name": "${TASK_NAME}",
    "model": "${MODEL}",
    "status": "running",
    "prompt": $(printf '%s' "${PROMPT}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    "workdir": "${WORKDIR}",
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "timeout_seconds": ${TIMEOUT},
    "output_file": "${OUTPUT_FILE}"
}
EOF

# Write the command to a temp script to avoid nested quoting issues with tmux
WINDOW_NAME="task-${TASK_NAME}"
TASK_SCRIPT="${WORK_DIR}/task-${TASK_NAME}.sh"
cat > "${TASK_SCRIPT}" <<SCRIPT_EOF
#!/usr/bin/env bash
${CMD} > "${OUTPUT_FILE}" 2>&1
echo \$? > "${DONE_MARKER}"
sleep 2
SCRIPT_EOF
chmod +x "${TASK_SCRIPT}"

# Create a tmux window that runs the task script
tmux new-window -t "${SESSION_ID}" -n "${WINDOW_NAME}" "bash '${TASK_SCRIPT}'"

# Also set up a timeout watchdog in the background
(
    sleep "${TIMEOUT}"
    if [ ! -f "${DONE_MARKER}" ]; then
        tmux kill-window -t "${SESSION_ID}:${WINDOW_NAME}" 2>/dev/null || true
        echo "124" > "${DONE_MARKER}"  # 124 = timeout exit code
    fi
) &
WATCHDOG_PID=$!
disown "${WATCHDOG_PID}" 2>/dev/null || true

# Return task info
cat <<EOF
{
    "task_name": "${TASK_NAME}",
    "model": "${MODEL}",
    "session_id": "${SESSION_ID}",
    "status": "dispatched",
    "output_file": "${OUTPUT_FILE}",
    "meta_file": "${META_FILE}",
    "tmux_window": "${SESSION_ID}:${WINDOW_NAME}"
}
EOF
