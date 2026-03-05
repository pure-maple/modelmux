#!/usr/bin/env bash
# check_prereqs.sh — Verify prerequisites for multi-model collaboration
# Checks tmux and available model CLIs

set -euo pipefail

echo "=== Multi-Model Collaboration Prerequisites ==="
echo ""

ERRORS=0

# Check tmux
if command -v tmux &>/dev/null; then
    echo "[OK] tmux $(tmux -V 2>/dev/null || echo '(version unknown)')"
else
    echo "[MISSING] tmux — Install with: brew install tmux (macOS) or apt install tmux (Linux)"
    ERRORS=$((ERRORS + 1))
fi

# Check python3 (needed for JSON handling)
if command -v python3 &>/dev/null; then
    echo "[OK] python3 $(python3 --version 2>/dev/null)"
else
    echo "[MISSING] python3 — Required for JSON processing"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=== Available Model CLIs ==="
echo ""

MODELS=0

# Check codex
if command -v codex &>/dev/null; then
    echo "[OK] codex $(codex --version 2>/dev/null || echo '(version unknown)')"
    MODELS=$((MODELS + 1))
else
    echo "[--] codex — Not installed (npm i -g @openai/codex)"
fi

# Check gemini
if command -v gemini &>/dev/null; then
    echo "[OK] gemini $(gemini --version 2>/dev/null || echo '(version unknown)')"
    MODELS=$((MODELS + 1))
else
    echo "[--] gemini — Not installed"
fi

# Check for custom adapters
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo ""
echo "=== Installed Adapters ==="
for adapter in "${SCRIPT_DIR}/adapters/"*.sh; do
    [ -f "${adapter}" ] || continue
    name=$(basename "${adapter}" .sh)
    [ "${name}" = "_template" ] && continue
    echo "  - ${name}"
done

echo ""
if [ "${ERRORS}" -gt 0 ]; then
    echo "RESULT: ${ERRORS} missing prerequisite(s). Please install them first."
    exit 1
elif [ "${MODELS}" -eq 0 ]; then
    echo "RESULT: Prerequisites OK, but no model CLIs found. Install at least one."
    exit 1
else
    echo "RESULT: All good! ${MODELS} model(s) available."
    exit 0
fi
