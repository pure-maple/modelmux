# Adding New Model Adapters

This guide explains how to add support for a new AI CLI tool.

## Quick Start

1. Copy the template:
   ```bash
   cp scripts/adapters/_template.sh scripts/adapters/mymodel.sh
   ```

2. Implement `build_command()` — it receives 4 arguments and must echo a shell
   command string that runs your model CLI:

   ```bash
   build_command() {
       local prompt="$1"      # Task description
       local workdir="$2"     # Working directory
       local sandbox="$3"     # Sandbox level (may be ignored)
       local extra_args="$4"  # Additional CLI flags

       local escaped_prompt
       escaped_prompt=$(printf '%s' "${prompt}" | sed "s/'/'\\\\''/g")

       echo "mymodel run -p '${escaped_prompt}' --dir '${workdir}' ${extra_args}"
   }
   ```

3. Make it executable:
   ```bash
   chmod +x scripts/adapters/mymodel.sh
   ```

4. Use it:
   ```bash
   bash scripts/dispatch.sh --session <id> --model mymodel --prompt "hello"
   ```

## Adapter Contract

Your `build_command` function must return a **single shell command string** that:

- Accepts the prompt and produces output on **stdout**
- Returns **exit code 0** on success, non-zero on failure
- Runs in the given working directory
- Handles prompt escaping (the template includes a standard approach)

The dispatch system handles:
- tmux window creation
- Output redirection to file
- Timeout watchdog
- Done marker creation

## Examples

### Batch CLI (like codex exec)

```bash
build_command() {
    local escaped=$(printf '%s' "$1" | sed "s/'/'\\\\''/g")
    echo "mymodel exec --prompt '${escaped}' --cd '$2'"
}
```

### Interactive CLI with pipe mode

```bash
build_command() {
    local escaped=$(printf '%s' "$1" | sed "s/'/'\\\\''/g")
    echo "echo '${escaped}' | mymodel --non-interactive --dir '$2'"
}
```

### API-based (curl wrapper)

```bash
build_command() {
    local escaped=$(printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
    echo "curl -s https://api.example.com/v1/chat -H 'Authorization: Bearer \$MY_API_KEY' -d '{\"prompt\": ${escaped}}' | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"response\"])'"
}
```

## Testing Your Adapter

```bash
# Source the adapter
source scripts/adapters/mymodel.sh

# Check the generated command (don't run it)
build_command "Hello world" "/tmp" "read-only" ""

# Full integration test
bash scripts/session.sh start test
bash scripts/dispatch.sh --session ai-test --model mymodel --prompt "Say hello"
bash scripts/collect.sh --session ai-test --task mymodel-* --wait
bash scripts/session.sh stop ai-test
```
