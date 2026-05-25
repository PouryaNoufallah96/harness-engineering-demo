# Harness Engineering Demo

Companion repo for the YouTube video **"What is Harness Engineering?"**

A minimal, real **harness** built with the primitives already inside Claude Code —
no framework required. It wraps the [Schedulr](https://github.com/coleam00/schedulr)
brownfield app with a **PIV loop** (Plan → Implement → Validate) so you can see
what "building your own harness" actually looks like in production.

> **Harness engineering** = building the context and workflows that wrap a coding
> agent — the ecosystem it operates in — so it works the way *you* work: your
> processes enforced, your standards applied, building like another engineer on
> your team instead of a clever stranger guessing at your codebase.

---

## What's in here

| Piece | What it shows |
|-------|--------------|
| `CLAUDE.md` + `.claude/context/` | Rules + on-demand context derived from the real codebase (the "AI Layer") |
| `.claude/commands/plan.md` | PIV step 1: analyze codebase + ticket, write `plans/<feature>-plan.md` |
| `.claude/commands/implement.md` | PIV step 2: read plan, execute tasks, run per-task validation, write `reports/<feature>-implementation-report.md` |
| `.claude/commands/validate.md` | PIV step 3: run the full gate (ruff + mypy + pytest + eslint + tsc) |
| `.claude/hooks/post_tool_use_lint.py` | PostToolUse hook: runs ruff (Python) or eslint (TS) after every file edit |
| `.claude/hooks/stop_validate.py` | Stop hook: blocks Claude from stopping until ruff + pytest are green |
| `.claude/settings.json` | Wires both hooks into Claude Code |
| `ralph/ralph.sh` + `ralph/ralph.py` | The Ralph loop: strings headless Claude sessions together by re-feeding a spec each iteration |
| `app/` | Schedulr brownfield app (FastAPI + Next.js) — what the harness operates on |

---

## The two halves of a harness

1. **Within a session (the AI Layer):** `CLAUDE.md`, context modules, commands, hooks — everything that shapes how Claude behaves inside one Claude Code session.
2. **Across sessions (orchestration):** plan in one session → implement+validate in another → review in a third. Handed off via markdown files in `plans/` and `reports/`. Automated with the Ralph loop.

---

## Running the PIV loop

```bash
# Prerequisites: Claude Code CLI, uv (Python), npm (Node 20+)
# Start Postgres (runs on host port 5433)
cd app && docker compose up -d

# Install backend deps
cd app/backend && uv sync --extra dev

# Install frontend deps
cd app/frontend && npm install
```

### Step 1 — Plan

Open a Claude Code session in this repo and run:

```
/plan Add CSV export to the meetings page (SCH-142)
```

Claude reads the codebase, loads the relevant `.claude/context/` modules, and writes:
`plans/add-csv-export-plan.md`

### Step 2 — Implement

In the same or a fresh session:

```
/implement plans/add-csv-export-plan.md
```

Claude reads the plan, executes each ordered task, runs per-task validation, then writes:
`reports/add-csv-export-implementation-report.md`

### Step 3 — Validate

```
/validate
```

Runs the full gate. Same commands the Stop hook enforces automatically:

```bash
cd app/backend && uv run ruff check app
cd app/backend && uv run mypy app
cd app/backend && uv run pytest
cd app/frontend && npm run lint
cd app/frontend && npx tsc --noEmit
```

---

## Hooks

Hooks run automatically — no invocation needed.

**PostToolUse (lint):** After every `Edit`/`Write`/`MultiEdit`, `.claude/hooks/post_tool_use_lint.py` runs:
- Python files under `app/backend/` → `uv run ruff check <file>`
- TS/TSX files under `app/frontend/` → `npm run lint`

Non-blocking (always exits 0) — surfaces lint warnings without stopping work.

**Stop (validate gate):** Before Claude ends its turn, `.claude/hooks/stop_validate.py` runs ruff + pytest. If either fails it prints a JSON block decision and Claude is asked to fix the issue. It checks `stop_hook_active` in the hook JSON to avoid infinite loops.

---

## Ralph loop

Ralph strings together headless Claude sessions, re-feeding a spec to a fresh `claude -p` process each iteration until a `DONE.txt` sentinel appears.

**Example spec:** `ralph/PROMPT.md` — instructs Claude to add CSV export (SCH-142), with 8 verifiable spec items.

```bash
# From repo root — Python driver (cross-platform)
python ralph/ralph.py

# Bash driver (Linux/macOS)
bash ralph/ralph.sh

# Tune limits
RALPH_MAX_ITER=10 RALPH_ITER_TIMEOUT=900 python ralph/ralph.py
```

Ralph commits after each iteration so every step is reversible. See `ralph/README.md` for full documentation.

**Important:** `--dangerously-skip-permissions` is used by Ralph to allow unattended file writes. Use Ralph only in a sandbox or dedicated worktree — never on your main branch.

**Credit note (2026-06-15):** `claude -p` draws from a separate Agent SDK credit pool, not your interactive Claude Code subscription.

---

## Repo layout

```
harness-engineering-demo/
├── CLAUDE.md                      # Global rules (the AI Layer)
├── .claude/
│   ├── settings.json              # Hook wiring
│   ├── commands/
│   │   ├── plan.md                # /plan command
│   │   ├── implement.md           # /implement command
│   │   └── validate.md            # /validate command
│   ├── context/
│   │   ├── architecture.md        # Module map + add-resource pattern
│   │   ├── auth.md                # JWT vs legacy session
│   │   ├── export-pattern.md      # ExportService protocol + CSV escaping
│   │   ├── testing.md             # pytest + vitest patterns
│   │   └── timezones.md           # TimezoneAwareTime + UTC storage rules
│   └── hooks/
│       ├── post_tool_use_lint.py  # PostToolUse: lint on edit
│       └── stop_validate.py       # Stop: validation gate
├── plans/                         # /plan outputs land here
├── reports/                       # /implement outputs land here
├── ralph/
│   ├── PROMPT.md                  # Example spec (CSV export)
│   ├── ralph.sh                   # Bash loop driver
│   ├── ralph.py                   # Python loop driver (cross-platform)
│   └── README.md                  # Ralph documentation
└── app/                           # Schedulr brownfield app
    ├── backend/                   # FastAPI + SQLAlchemy 2.0, Python 3.12, uv
    ├── frontend/                  # Next.js 15 App Router, TypeScript
    └── docker-compose.yml         # Postgres 16 (host 5433)
```
