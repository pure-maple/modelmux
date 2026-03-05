#!/usr/bin/env bash
# session.sh — Manage tmux collaboration sessions
# Usage:
#   session.sh start [name]   — Create a new collaboration session
#   session.sh stop <id>      — Destroy a session and clean up
#   session.sh list           — List active sessions
#   session.sh info <id>      — Show session details

set -euo pipefail

COLLAB_DIR="/tmp/ai-collab"

cmd_start() {
    local name="${1:-collab-$(date +%s)}"
    local session_id="ai-${name}"
    local work_dir="${COLLAB_DIR}/${session_id}"

    # Check tmux
    if ! command -v tmux &>/dev/null; then
        echo '{"error": "tmux not found. Install with: brew install tmux (macOS) or apt install tmux (Linux)"}' >&2
        exit 1
    fi

    # Check for existing session
    if tmux has-session -t "${session_id}" 2>/dev/null; then
        echo '{"error": "Session already exists", "session_id": "'"${session_id}"'"}' >&2
        exit 1
    fi

    # Create output directory
    mkdir -p "${work_dir}"

    # Create detached tmux session
    tmux new-session -d -s "${session_id}" -n "control"

    # Write session metadata
    cat > "${work_dir}/session.json" <<EOF
{
    "session_id": "${session_id}",
    "name": "${name}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "work_dir": "${work_dir}",
    "tasks": []
}
EOF

    echo "${session_id}"
}

cmd_stop() {
    local session_id="${1:?Session ID required}"

    # Kill tmux session if it exists
    if tmux has-session -t "${session_id}" 2>/dev/null; then
        tmux kill-session -t "${session_id}"
    fi

    # Clean up work directory
    local work_dir="${COLLAB_DIR}/${session_id}"
    if [ -d "${work_dir}" ]; then
        rm -rf "${work_dir}"
    fi

    echo "Session ${session_id} stopped and cleaned up."
}

cmd_list() {
    if ! command -v tmux &>/dev/null; then
        echo "[]"
        return
    fi

    local sessions
    sessions=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^ai-' || true)

    if [ -z "${sessions}" ]; then
        echo "[]"
        return
    fi

    echo "["
    local first=true
    while IFS= read -r sid; do
        local work_dir="${COLLAB_DIR}/${sid}"
        local task_count=0
        if [ -d "${work_dir}" ]; then
            task_count=$(find "${work_dir}" -name "task-*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
        fi
        if [ "${first}" = true ]; then
            first=false
        else
            echo ","
        fi
        printf '  {"session_id": "%s", "tasks": %d}' "${sid}" "${task_count}"
    done <<< "${sessions}"
    echo ""
    echo "]"
}

cmd_info() {
    local session_id="${1:?Session ID required}"
    local work_dir="${COLLAB_DIR}/${session_id}"

    if [ ! -f "${work_dir}/session.json" ]; then
        echo '{"error": "Session not found"}' >&2
        exit 1
    fi

    cat "${work_dir}/session.json"
}

# Main dispatcher
case "${1:-}" in
    start) shift; cmd_start "$@" ;;
    stop)  shift; cmd_stop "$@" ;;
    list)  cmd_list ;;
    info)  shift; cmd_info "$@" ;;
    *)
        echo "Usage: session.sh {start|stop|list|info} [args]" >&2
        exit 1
        ;;
esac
