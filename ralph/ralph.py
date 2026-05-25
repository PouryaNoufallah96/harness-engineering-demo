#!/usr/bin/env python3
"""ralph/ralph.py — The Ralph loop (Python driver).

Cross-platform alternative to ralph.sh. Feeds PROMPT.md to a fresh headless
Claude CLI process each iteration until DONE.txt appears or MAX_ITER is reached.

Usage:
    cd harness-engineering-demo
    python ralph/ralph.py

    # Override defaults with env vars:
    RALPH_MAX_ITER=10 RALPH_ITER_TIMEOUT=900 python ralph/ralph.py

Requirements:
    - `claude` CLI on PATH
    - Run from the repo root (where CLAUDE.md lives)

WARNING: --dangerously-skip-permissions bypasses file-write confirmations.
Use only in a sandbox / dedicated worktree.

NOTE (2026-06-15): `claude -p` draws from a separate Agent SDK credit pool,
distinct from your interactive Claude Code subscription.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.resolve()
SCRIPT_DIR = Path(__file__).parent.resolve()

PROMPT_FILE = SCRIPT_DIR / "PROMPT.md"
DONE_FILE = SCRIPT_DIR / "DONE.txt"
LOG_FILE = SCRIPT_DIR / "ralph.log"

MAX_ITER: int = int(os.environ.get("RALPH_MAX_ITER", "15"))
ITER_TIMEOUT: int = int(os.environ.get("RALPH_ITER_TIMEOUT", "1800"))  # seconds


def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def git_commit(iteration: int) -> None:
    """Stage all changes and commit if there's anything to commit."""
    subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=False)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_ROOT,
    )
    if diff.returncode != 0:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        subprocess.run(
            ["git", "commit", "-m", f"ralph: iteration {iteration} — {ts}", "--no-verify"],
            cwd=REPO_ROOT,
            check=False,
        )
        log(f"git commit: iteration {iteration}")
    else:
        log("git: nothing to commit this iteration")


def run_claude(spec: str) -> dict:
    """Invoke `claude -p` with spec on stdin; return parsed JSON output.

    Resolve the binary via shutil.which so this works on Windows too, where the
    Claude CLI is `claude.cmd` (an npm shim) and bare-name subprocess.run does
    not resolve `.cmd` files.
    """
    claude_bin = shutil.which("claude") or "claude"
    result = subprocess.run(
        [
            claude_bin,
            "-p",
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--max-turns", "40",
        ],
        input=spec,
        capture_output=True,
        text=True,
        encoding="utf-8",  # spec/PROMPT.md contains non-cp1252 chars (e.g. →); force UTF-8 on Windows
        timeout=ITER_TIMEOUT,
        cwd=REPO_ROOT,
    )
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write(result.stderr)

    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def main() -> None:
    if not PROMPT_FILE.exists():
        print(f"ERROR: PROMPT.md not found at {PROMPT_FILE}", file=sys.stderr)
        sys.exit(1)

    spec = PROMPT_FILE.read_text(encoding="utf-8")

    log("=== Ralph loop started ===")
    log(f"PROMPT: {PROMPT_FILE}")
    log(f"MAX_ITER: {MAX_ITER} | TIMEOUT per iter: {ITER_TIMEOUT}s")

    for iteration in range(1, MAX_ITER + 1):
        log(f"--- Iteration {iteration} / {MAX_ITER} ---")

        if DONE_FILE.exists():
            log(f"DONE.txt found — spec complete after {iteration - 1} iterations.")
            sys.exit(0)

        try:
            output = run_claude(spec)
            log(f"Claude finished iteration {iteration}")
        except subprocess.TimeoutExpired:
            log(f"Iteration {iteration} timed out after {ITER_TIMEOUT}s")
        except Exception as exc:
            log(f"Iteration {iteration} error: {exc}")

        git_commit(iteration)

        if DONE_FILE.exists():
            log(f"DONE.txt found — spec complete after {iteration} iterations.")
            sys.exit(0)

        log(f"Iteration {iteration} complete — spec not yet done.")

    log(f"MAX_ITER ({MAX_ITER}) reached without DONE.txt. Review ralph.log and fix_plan.md.")
    sys.exit(1)


if __name__ == "__main__":
    main()
