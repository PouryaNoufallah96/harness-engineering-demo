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
| `.claude/skills/plan/SKILL.md` | PIV step 1: analyze codebase + ticket, write `plans/<feature>-plan.md` |
| `.claude/skills/implement/SKILL.md` | PIV step 2: read plan, execute tasks, run per-task validation, write `reports/<feature>-implementation-report.md` |
| `.claude/skills/validate/SKILL.md` | PIV step 3: run the full gate (ruff + mypy + pytest + tsc + vitest) |
| `.claude/skills/review/SKILL.md` | PIV step 4: delegate diff to the code-reviewer sub-agent, write `reports/<feature>-review.md` |
| `.claude/agents/code-reviewer.md` | Sub-agent that reviews diffs against CLAUDE.md rules using codebase-search MCP tools |
| `.claude/hooks/post_tool_use_lint.py` | PostToolUse hook: runs ruff (Python) or `tsc --noEmit` typecheck (TS) after every file edit |
| `.claude/hooks/stop_validate.py` | Stop hook: blocks Claude from stopping until ruff + pytest are green |
| `.claude/settings.json` | Wires both hooks into Claude Code |
| `.mcp.json` | Registers the `codebase-search` MCP server (AST-based symbol navigation) |
| `tooling/mcp/codebase_search.py` | FastMCP server exposing `where_is`, `find_references`, `outline` over the project's Python AST |
| `tooling/pyproject.toml` | Isolated uv project declaring the `mcp` dependency for the tooling layer |
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
cd app/frontend && npx tsc --noEmit
cd app/frontend && npm run test
```

---

## Hooks

Hooks run automatically — no invocation needed.

**PostToolUse (static check):** After every `Edit`/`Write`/`MultiEdit`, `.claude/hooks/post_tool_use_lint.py` runs:
- Python files under `app/backend/` → `uv run ruff check <file>`
- TS/TSX files under `app/frontend/` → `npx tsc --noEmit` (typecheck — this brownfield app has no ESLint configured, and `next lint` would prompt interactively)

Non-blocking (always exits 0) — surfaces issues without stopping work. Binaries are resolved via `shutil.which` so it works under Windows cmd.exe too.

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
├── .mcp.json                      # Registers codebase-search MCP server
├── .claude/
│   ├── settings.json              # Hook wiring
│   ├── agents/
│   │   └── code-reviewer.md       # Sub-agent: reviews diffs against CLAUDE.md rules
│   ├── skills/
│   │   ├── plan/SKILL.md          # /plan skill (PIV step 1)
│   │   ├── implement/SKILL.md     # /implement skill (PIV step 2)
│   │   ├── validate/SKILL.md      # /validate skill (PIV step 3)
│   │   └── review/SKILL.md        # /review skill (PIV step 4 — sub-agent delegation)
│   ├── context/
│   │   ├── architecture.md        # Module map + add-resource pattern
│   │   ├── auth.md                # JWT vs legacy session
│   │   ├── codebase-search.md     # MCP tool descriptions (where_is / find_references / outline)
│   │   ├── export-pattern.md      # ExportService protocol + CSV escaping
│   │   ├── testing.md             # pytest + vitest patterns
│   │   └── timezones.md           # TimezoneAwareTime + UTC storage rules
│   └── hooks/
│       ├── post_tool_use_lint.py  # PostToolUse: lint on edit
│       └── stop_validate.py       # Stop: validation gate
├── tooling/
│   ├── pyproject.toml             # Isolated uv project for tooling deps (mcp)
│   └── mcp/
│       └── codebase_search.py     # FastMCP AST server: where_is / find_references / outline
├── plans/                         # /plan outputs land here
├── reports/                       # /implement + /review outputs land here
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
