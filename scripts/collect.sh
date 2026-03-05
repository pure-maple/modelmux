#!/usr/bin/env bash
# collect.sh — Collect output from dispatched model tasks
# Usage:
#   collect.sh --session <id> --status           Show status of all tasks
#   collect.sh --session <id> --task <name>       Get output of a specific task
#   collect.sh --session <id> --task <name> --wait  Wait for task and get output
#   collect.sh --session <id> --all               Get all completed outputs
#   collect.sh --session <id> --wait-all          Wait for all tasks to complete

set -euo pipefail

COLLAB_DIR="/tmp/ai-collab"
POLL_INTERVAL=2  # seconds between status checks

# Parse arguments
SESSION_ID=""
TASK_NAME=""
ACTION=""
WAIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --session)   SESSION_ID="$2"; shift 2 ;;
        --task)      TASK_NAME="$2"; shift 2 ;;
        --status)    ACTION="status"; shift ;;
        --all)       ACTION="all"; shift ;;
        --wait-all)  ACTION="wait-all"; shift ;;
        --wait)      WAIT=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "${SESSION_ID}" ]; then
    echo '{"error": "Required: --session"}' >&2
    exit 1
fi

WORK_DIR="${COLLAB_DIR}/${SESSION_ID}"

if [ ! -d "${WORK_DIR}" ]; then
    echo '{"error": "Session directory not found: '"${SESSION_ID}"'"}' >&2
    exit 1
fi

# Check if a task is done and get its result
get_task_result() {
    local task_name="$1"
    local meta_file="${WORK_DIR}/task-${task_name}.json"
    local output_file="${WORK_DIR}/task-${task_name}.output"
    local done_marker="${WORK_DIR}/task-${task_name}.done"

    if [ ! -f "${meta_file}" ]; then
        echo '{"error": "Task not found: '"${task_name}"'"}'
        return 1
    fi

    local model
    model=$(python3 -c "import json; d=json.load(open('${meta_file}')); print(d.get('model','unknown'))")
    local prompt
    prompt=$(python3 -c "import json; d=json.load(open('${meta_file}')); print(json.dumps(d.get('prompt','')))")
    local started_at
    started_at=$(python3 -c "import json; d=json.load(open('${meta_file}')); print(d.get('started_at',''))")

    if [ -f "${done_marker}" ]; then
        local exit_code
        exit_code=$(cat "${done_marker}" | tr -d '[:space:]')
        local output=""
        if [ -f "${output_file}" ]; then
            output=$(python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" < "${output_file}")
        else
            output='""'
        fi

        # Calculate duration using python3 for cross-platform ISO date parsing
        local duration
        duration=$(python3 -c "
from datetime import datetime, timezone
import sys
try:
    start = datetime.fromisoformat('${started_at}'.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    print(int((now - start).total_seconds()))
except:
    print(0)
" 2>/dev/null || echo "0")

        local status="completed"
        if [ "${exit_code}" = "124" ]; then
            status="timeout"
        elif [ "${exit_code}" != "0" ]; then
            status="failed"
        fi

        cat <<EOF
{
    "task_name": "${task_name}",
    "model": "${model}",
    "status": "${status}",
    "exit_code": ${exit_code},
    "duration_seconds": ${duration},
    "output": ${output},
    "prompt": ${prompt}
}
EOF
    else
        cat <<EOF
{
    "task_name": "${task_name}",
    "model": "${model}",
    "status": "running",
    "prompt": ${prompt}
}
EOF
    fi
}

# Status: show all tasks and their current state
cmd_status() {
    echo "["
    local first=true
    for meta_file in "${WORK_DIR}"/task-*.json; do
        [ -f "${meta_file}" ] || continue
        local task_name
        task_name=$(basename "${meta_file}" .json | sed 's/^task-//')
        local done_marker="${WORK_DIR}/task-${task_name}.done"
        local model
        model=$(python3 -c "import json; d=json.load(open('${meta_file}')); print(d.get('model','unknown'))")

        local status="running"
        if [ -f "${done_marker}" ]; then
            local ec
            ec=$(cat "${done_marker}" | tr -d '[:space:]')
            if [ "${ec}" = "0" ]; then status="completed"
            elif [ "${ec}" = "124" ]; then status="timeout"
            else status="failed"
            fi
        fi

        if [ "${first}" = true ]; then first=false; else echo ","; fi
        printf '  {"task_name": "%s", "model": "%s", "status": "%s"}' \
            "${task_name}" "${model}" "${status}"
    done
    echo ""
    echo "]"
}

# Get a specific task (with optional wait)
cmd_task() {
    if [ -z "${TASK_NAME}" ]; then
        echo '{"error": "Required: --task <name>"}' >&2
        exit 1
    fi

    if [ "${WAIT}" = true ]; then
        local done_marker="${WORK_DIR}/task-${TASK_NAME}.done"
        while [ ! -f "${done_marker}" ]; do
            sleep "${POLL_INTERVAL}"
        done
    fi

    get_task_result "${TASK_NAME}"
}

# Get all completed tasks
cmd_all() {
    echo "["
    local first=true
    for meta_file in "${WORK_DIR}"/task-*.json; do
        [ -f "${meta_file}" ] || continue
        local task_name
        task_name=$(basename "${meta_file}" .json | sed 's/^task-//')
        local done_marker="${WORK_DIR}/task-${task_name}.done"

        [ -f "${done_marker}" ] || continue

        if [ "${first}" = true ]; then first=false; else echo ","; fi
        get_task_result "${task_name}"
    done
    echo ""
    echo "]"
}

# Wait for all tasks to complete, then return all
cmd_wait_all() {
    while true; do
        local all_done=true
        for meta_file in "${WORK_DIR}"/task-*.json; do
            [ -f "${meta_file}" ] || continue
            local task_name
            task_name=$(basename "${meta_file}" .json | sed 's/^task-//')
            if [ ! -f "${WORK_DIR}/task-${task_name}.done" ]; then
                all_done=false
                break
            fi
        done

        if [ "${all_done}" = true ]; then
            break
        fi
        sleep "${POLL_INTERVAL}"
    done

    cmd_all
}

# Main dispatcher
if [ -n "${TASK_NAME}" ]; then
    cmd_task
elif [ "${ACTION}" = "status" ]; then
    cmd_status
elif [ "${ACTION}" = "all" ]; then
    cmd_all
elif [ "${ACTION}" = "wait-all" ]; then
    cmd_wait_all
else
    echo "Usage: collect.sh --session <id> {--status|--task <name> [--wait]|--all|--wait-all}" >&2
    exit 1
fi
