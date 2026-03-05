#!/usr/bin/env bash
# gemini.sh — Adapter for Google Gemini CLI (v0.32+)
# Implements: build_command(prompt, workdir, sandbox, extra_args)
#
# gemini syntax:
#   gemini -p "prompt"          Non-interactive (headless) mode
#   -s / --sandbox              Enable sandbox mode
#   -y / --yolo                 Auto-approve all actions
#   -o text                     Plain text output (no JSON)

build_command() {
    local prompt="$1"
    local workdir="${2:-.}"
    local sandbox="${3:-}"
    local extra_args="${4:-}"

    # Escape the prompt for shell embedding
    local escaped_prompt
    escaped_prompt=$(printf '%s' "${prompt}" | sed "s/'/'\\\\''/g")

    # Build the command string
    # Use -p for non-interactive headless mode, -o text for clean output
    local cmd="cd '${workdir}' && gemini -p '${escaped_prompt}' -o text"

    # Add sandbox flag if requested
    if [ "${sandbox}" = "read-only" ] || [ "${sandbox}" = "sandbox" ]; then
        cmd="${cmd} -s"
    fi

    if [ -n "${extra_args}" ]; then
        cmd="${cmd} ${extra_args}"
    fi

    echo "${cmd}"
}
