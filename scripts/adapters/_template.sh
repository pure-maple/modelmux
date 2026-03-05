#!/usr/bin/env bash
# _template.sh — Template for creating new model adapters
#
# To add a new model:
# 1. Copy this file: cp _template.sh mymodel.sh
# 2. Implement the build_command function
# 3. The adapter is automatically available via --model mymodel
#
# The function receives:
#   $1 = prompt (the task description, may include context)
#   $2 = workdir (working directory path)
#   $3 = sandbox (sandbox level: read-only, workspace-write, full-access)
#   $4 = extra_args (additional CLI arguments)
#
# It must echo a single shell command string that:
#   - Runs the model CLI with the given prompt
#   - Outputs the result to stdout
#   - Returns exit code 0 on success

build_command() {
    local prompt="$1"
    local workdir="${2:-.}"
    local sandbox="${3:-}"
    local extra_args="${4:-}"

    # Escape the prompt for shell embedding
    local escaped_prompt
    escaped_prompt=$(printf '%s' "${prompt}" | sed "s/'/'\\\\''/g")

    # TODO: Replace with your model's CLI command
    # Example:
    #   echo "mymodel run --prompt '${escaped_prompt}' --dir '${workdir}' ${extra_args}"

    echo "echo 'ERROR: _template adapter not implemented. Copy and customize this file.'" >&2
    exit 1
}
