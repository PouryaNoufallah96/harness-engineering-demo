# Ralph — Autonomous Spec-Driven Loop

Ralph is a tight feedback loop that re-feeds a spec (`PROMPT.md`) to a fresh headless Claude process each iteration until the spec is fully satisfied or a safety cap is hit.

## What it does

```
loop:
  1. Check for DONE.txt → exit if present
  2. cat PROMPT.md | claude -p --output-format json --dangerously-skip-permissions --max-turns 40
  3. git add -A && git commit  (captures each iteration's work)
  4. Check for DONE.txt again
  5. Repeat up to MAX_ITER times
```

Claude reads `PROMPT.md`, does one logical unit of work (per the spec's work pattern), runs the specified validation commands, and when all spec items pass it runs `touch ralph/DONE.txt` to signal completion.

## Files

| File | Purpose |
|------|---------|
| `ralph.sh` | Bash driver (Linux/macOS) |
| `ralph.py` | Python driver (cross-platform, Windows-safe) |
| `PROMPT.md` | The spec Claude receives every iteration |
| `ralph.log` | Append-only log of every iteration's output |
| `fix_plan.md` | Running log Claude maintains across iterations |

## Running

```bash
# From repo root — bash driver
bash ralph/ralph.sh

# Python driver (Windows / any platform)
python ralph/ralph.py

# Tune limits with env vars
RALPH_MAX_ITER=10 RALPH_ITER_TIMEOUT=900 python ralph/ralph.py
```

## Guardrails

| Guardrail | Default | Purpose |
|-----------|---------|---------|
| `MAX_ITER` | 15 | Hard cap — prevents runaway loops |
| `ITER_TIMEOUT` | 1800 s | Per-iteration wall-clock limit |
| `DONE.txt` sentinel | — | Claude writes this only when ALL spec items pass |
| `git commit` per iter | — | Every iteration's changes are captured and reversible |

## `--dangerously-skip-permissions`

This flag tells Claude to skip interactive permission prompts for file writes, shell commands, etc. **Use only in a sandbox or dedicated worktree.** Never run Ralph on your main working branch.

## Agent SDK Credit Note (2026-06-15)

From 2026-06-15 onward, `claude -p` (headless / programmatic mode) draws from a **separate Agent SDK credit pool** rather than your interactive Claude Code subscription. Check your Anthropic console for Agent SDK usage and limits before running long Ralph loops.

## Anatomy of a Good PROMPT.md

1. **Goal** — one paragraph: what feature to build.
2. **Spec Items** — numbered checklist: each item is a concrete, verifiable condition.
3. **Work Pattern** — tell Claude to do ONE logical change per iteration, record in `fix_plan.md`, and only `touch DONE.txt` when all items pass.
4. **Fix Plan File** — instruct Claude to append `## Iteration N` entries with what changed, validation result, and what's next.

See `ralph/PROMPT.md` for the example (CSV export / SCH-142).
