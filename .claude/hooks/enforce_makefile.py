#!/usr/bin/env python3
"""PreToolUse hook that intercepts uv run/tool commands and suggests Makefile targets."""

import json
import re
import sys

# Map of command patterns to their Makefile equivalents.
# Each key is a regex anchored to match only when the command *starts* with the pattern
# (possibly after cd/&& prefixes), not when it appears inside quoted strings or arguments.
# Each value is the suggested make target with a human-readable description.
COMMAND_MAP = {
    r"uv (run )?ruff check": ("make ruff", "Run ruff linter"),
    r"uv (run )?ruff format": ("make fmt", "Format code with ruff and jq"),
    r"uv tool run ruff check": ("make ruff", "Run ruff linter"),
    r"uv tool run ruff format": ("make fmt", "Format code with ruff and jq"),
    r"uv (run )?pytest": ("make test", "Run pytest (or make test_fast, make test_slow)"),
    r"uv (run )?vulture": ("make vulture", "Find dead code with vulture"),
    r"uv tool run vulture": ("make vulture", "Find dead code with vulture"),
    r"uv (run )?ty check": ("make ty", "Run type checker"),
    r"uv (run )?deptry": ("make check_deps", "Check for unused dependencies"),
    r"uv (run )?pylint": ("make duplicate_code", "Detect duplicate code blocks"),
    r"uv tool run --from import-linter lint-imports": (
        "make import_lint",
        "Enforce module boundaries with import-linter",
    ),
}

# Regex prefix: matches start-of-string, or after "&&"/" ; " separators,
# skipping optional whitespace. This prevents matching inside quoted strings.
_CMD_START = r"(?:^|&&|;)\s*"


def main():
    hook_input = json.load(sys.stdin)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return

    command = hook_input.get("tool_input", {}).get("command", "")

    for pattern, (make_target, description) in COMMAND_MAP.items():
        if re.search(_CMD_START + pattern, command):
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"Use `{make_target}` instead. "
                        f"({description}). "
                        f"This project uses Makefile targets for all CI/dev commands. "
                        f"Run `make help` to see all available targets."
                    ),
                }
            }
            json.dump(result, sys.stdout)
            return


if __name__ == "__main__":
    main()
