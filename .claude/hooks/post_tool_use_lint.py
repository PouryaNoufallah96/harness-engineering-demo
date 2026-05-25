#!/usr/bin/env python3
"""Post-tool-use lint hook.

Reads the Claude Code hook JSON from stdin. When a Python file under app/backend
or a TS/TSX file under app/frontend is written/edited, runs the appropriate linter
and prints the result. Always exits 0 (non-blocking — surfaces lint, never stops work).

Wired to: PostToolUse / Edit|Write|MultiEdit
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    try:
        data: dict = json.load(sys.stdin)
    except Exception as e:
        print(f"[lint-hook] Could not parse hook JSON: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input: dict = data.get("tool_input") or {}
    file_path_raw: str | None = tool_input.get("file_path")

    if not file_path_raw:
        sys.exit(0)

    file_path = Path(file_path_raw).resolve()
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()

    # Resolve paths relative to project root
    app_backend = project_dir / "app" / "backend"
    app_frontend = project_dir / "app" / "frontend"

    try:
        rel = file_path.relative_to(project_dir)
    except ValueError:
        sys.exit(0)

    rel_str = rel.as_posix()

    if rel_str.startswith("app/backend/") and file_path.suffix == ".py":
        print(f"[lint-hook] ruff check on {rel_str}")
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file_path)],
            cwd=str(app_backend),
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        if result.returncode == 0:
            print(f"[lint-hook] ruff: OK")
        else:
            print(f"[lint-hook] ruff: issues found (see above) — fix before committing")

    elif rel_str.startswith("app/frontend/") and file_path.suffix in (".ts", ".tsx"):
        print(f"[lint-hook] eslint on {rel_str}")
        result = subprocess.run(
            ["npm", "run", "lint"],
            cwd=str(app_frontend),
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        if result.returncode == 0:
            print(f"[lint-hook] eslint: OK")
        else:
            print(f"[lint-hook] eslint: issues found (see above) — fix before committing")

    # Always exit 0: lint hook is advisory, not blocking
    sys.exit(0)


if __name__ == "__main__":
    main()
