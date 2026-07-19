---
name: onboarding
description: Interview the user, inspect this template repo, run the headless onboarding steps, and prune unused systems so a new Python CLI project gets running quickly.
---

# Onboarding

Use this skill when the user wants to turn this template into a real project,
especially when they invoke `/onboarding`, ask to run onboarding, or want to
remove unused template systems.

`onboard.py` is the source of truth for every step, default, and file it
rewrites. Read it before changing anything. It is a Typer app whose subcommands
(`branding`, `rename`, `cli_name`, `deps`, `env`, `hooks`, `media`, `jules`)
are the exact steps `make onboard` runs in order, and each subcommand shows
which files it touches and which template sentinels it replaces.

## Workflow

1. Inspect the repo before changing anything:
   - `CLAUDE.md` / `AGENTS.md`, `README.md`, `pyproject.toml`, `Makefile`
   - `onboard.py`, the step list (`STEPS`), the template sentinels
     (`_TEMPLATE_PACKAGE_NAME` = `miyamura80-cli-template`, `_TEMPLATE_OWNER` =
     `Miyamura80`, `_TEMPLATE_REPO_NAME` = `CLI-Template`, CLI name `mycli`,
     package fallback `python-template`), and what each step rewrites
   - The systems the steps configure: branding in `common/global_config.yaml`;
     project identity in `pyproject.toml` + `README.md`; the CLI name across
     `cli.py`, `src/cli/`, tests; secrets in `.env` (seeded from `.env.example`);
     hooks in `prek.toml`; media assets in `media/` and `docs/public/`; Jules
     workflows in `.github/workflows/`
   - Optional systems onboarding does NOT prune (handle manually, step 6):
     the `docs/` site, LLM inference (`utils/llm/`, DSPY + LangFuse),
     `init/`+`media/` media generation, CLI telemetry (`src/cli/telemetry.py`),
     and the various CI workflows in `.github/workflows/`

2. Interview the user briefly before running anything. Establish:
   - Project name (kebab-case) and one-line description
   - CLI command name (replaces `mycli` everywhere)
   - GitHub owner/repo (auto-detected from `git remote`; confirm it)
   - Which optional systems they want to keep vs. prune (docs site, LLM
     inference, media generation, telemetry, Jules automation)
   - Which secrets/API keys they have on hand for the `env` step

3. Run onboarding. `make onboard` (= `uv run python onboard.py`) launches the
   full interactive wizard. To drive individual steps headlessly, invoke the
   Typer subcommands directly:
   - `uv run python onboard.py deps`: non-interactive, creates `.venv` and runs
     `uv sync`. Safe to run unattended.
   - `uv run python onboard.py rename` / `cli_name` / `branding` / `env` /
     `hooks` / `media` / `jules`: each still prompts (via `questionary`), so
     run them in a real terminal or feed answers; they are not fully headless.
   - Prefer running `deps` first, then the identity steps (`rename`,
     `cli_name`), then `env`/`hooks`, leaving `media` (needs `GEMINI_API_KEY`)
     and `jules` for last.

4. Apply the natural ordering and dependencies:
   - `deps` must succeed before `hooks` (prek is installed via `uv tool`) and
     before verifying the CLI.
   - `rename` and `cli_name` are string replacements across tracked files;
     re-running is safe (they detect the current values and offer to re-rename).
   - `media` is skipped automatically when `GEMINI_API_KEY` is absent, don't
     force it.

5. Verify the resulting project:
   - `uv run <cli-name> --help` and one simple command (e.g. the greet/ping
     example) confirm the rename + CLI wiring.
   - Run focused `uv run pytest` first, then `make ci` when the change scope is
     large.

6. Prune unused systems, only after the user confirms each one. These are NOT
   automated, remove deliberately:
   - Docs site: delete `docs/` and its lint/link/translation workflows
     (`docs-lint.yaml`, `jules-sync-translations.yml`, `markdown-link-lint.yaml`
     as appropriate).
   - LLM inference: delete `utils/llm/`, drop DSPY/LangFuse deps from
     `pyproject.toml`, remove the LLM section from `CLAUDE.md`.
   - Media generation: delete `init/`, `media/`, the `banner`/`logo` Makefile
     targets, and the `media` step from `onboard.py`.
   - Jules automation: use `uv run python onboard.py jules` to disable the
     maintenance workflows, or delete the `jules-*.yml` files outright.
   - After any prune, run `make ci` and fix fallout (imports, dead config keys).

## Guardrails

- Do not delete the docs site, LLM layer, or CI workflows without explicit user
  confirmation.
- Do not push to `main`, force-push, or run destructive git commands. Onboarding
  reads `git remote` only; it never commits or pushes.
- Interview and confirm the plan before any mutating step; prefer a dry
  discussion of what each step rewrites before running it.
- Keep secrets in `.env` (git-ignored); never commit real API keys.
