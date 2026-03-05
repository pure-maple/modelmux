#!/usr/bin/env bash
# codex.sh — Adapter for OpenAI Codex CLI (v0.110+)
# Implements: build_command(prompt, workdir, sandbox, extra_args)
#
# codex exec syntax:
#   codex exec [OPTIONS] [PROMPT]
#   - PROMPT is a positional argument (not a flag)
#   - --cd DIR sets working directory
#   - No --sandbox flag; use --skip-git-repo-check for non-git dirs

build_command() {
    local prompt="$1"
    local workdir="${2:-.}"
    local sandbox="${3:-read-only}"
    local extra_args="${4:-}"

    # Escape the prompt for shell embedding
    local escaped_prompt
    escaped_prompt=$(printf '%s' "${prompt}" | sed "s/'/'\\\\''/g")

    # Build the command string
    # codex exec takes prompt as positional arg, --cd for workdir
    local cmd="codex exec --cd '${workdir}'"

    # Add skip-git-repo-check in case workdir is not a git repo
    cmd="${cmd} --skip-git-repo-check"

    # Add extra args before the prompt
    if [ -n "${extra_args}" ]; then
        cmd="${cmd} ${extra_args}"
    fi

    # Prompt must be last (positional argument)
    cmd="${cmd} '${escaped_prompt}'"

    echo "${cmd}"
}
