#!/usr/bin/env bash
# ralph/ralph.sh — The Ralph loop (bash driver)
#
# Feeds PROMPT.md to a fresh headless Claude each iteration until DONE.txt
# appears or MAX_ITER is reached.
#
# Usage:
#   cd harness-engineering-demo
#   bash ralph/ralph.sh
#
# Requirements:
#   - `claude` CLI on PATH (Claude Code CLI)
#   - Run from the repo root (where CLAUDE.md lives)
#
# WARNING: --dangerously-skip-permissions bypasses file-write confirmations.
# Use only in a sandbox / dedicated worktree. Never on your main working tree.
#
# NOTE (2026-06-15): `claude -p` draws from a separate Agent SDK credit pool,
# distinct from your interactive Claude Code subscription.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PROMPT_FILE="$SCRIPT_DIR/PROMPT.md"
DONE_FILE="$SCRIPT_DIR/DONE.txt"
LOG_FILE="$SCRIPT_DIR/ralph.log"
MAX_ITER="${RALPH_MAX_ITER:-15}"
ITER_TIMEOUT="${RALPH_ITER_TIMEOUT:-1800}"  # seconds per iteration

cd "$REPO_ROOT"

echo "=== Ralph loop started at $(date) ===" | tee -a "$LOG_FILE"
echo "PROMPT: $PROMPT_FILE" | tee -a "$LOG_FILE"
echo "MAX_ITER: $MAX_ITER | TIMEOUT per iter: ${ITER_TIMEOUT}s" | tee -a "$LOG_FILE"

ITER=0

while [ "$ITER" -lt "$MAX_ITER" ]; do
    ITER=$((ITER + 1))
    echo "" | tee -a "$LOG_FILE"
    echo "--- Iteration $ITER / $MAX_ITER at $(date) ---" | tee -a "$LOG_FILE"

    # Check done sentinel BEFORE running Claude
    if [ -f "$DONE_FILE" ]; then
        echo "DONE.txt found — spec complete after $((ITER - 1)) iterations." | tee -a "$LOG_FILE"
        exit 0
    fi

    # Feed spec to a fresh Claude headless session
    timeout "$ITER_TIMEOUT" \
        claude -p \
            --output-format json \
            --dangerously-skip-permissions \
            --max-turns 40 \
        < "$PROMPT_FILE" \
        >> "$LOG_FILE" 2>&1 || {
            EXIT=$?
            if [ "$EXIT" -eq 124 ]; then
                echo "Iteration $ITER timed out after ${ITER_TIMEOUT}s" | tee -a "$LOG_FILE"
            else
                echo "Claude exited with code $EXIT" | tee -a "$LOG_FILE"
            fi
        }

    # Commit any changes made this iteration
    git add -A
    git diff --cached --quiet || git commit \
        -m "ralph: iteration $ITER — $(date +%Y-%m-%dT%H:%M:%S)" \
        --no-verify 2>&1 | tee -a "$LOG_FILE"

    # Check done sentinel AFTER Claude ran
    if [ -f "$DONE_FILE" ]; then
        echo "DONE.txt found — spec complete after $ITER iterations." | tee -a "$LOG_FILE"
        exit 0
    fi

    echo "Iteration $ITER complete — spec not yet done." | tee -a "$LOG_FILE"
done

echo "" | tee -a "$LOG_FILE"
echo "MAX_ITER ($MAX_ITER) reached without DONE.txt. Review ralph.log and fix_plan.md." \
    | tee -a "$LOG_FILE"
exit 1
