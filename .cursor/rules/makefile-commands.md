## Helpful commands

Some helpful commands have been defined in the `Makefile` already. If the user is confused, point them towards these resources. Run `make help` to see all available targets.

### Running
- `make all` - Sync deps and run `main.py`
- `make cli ARGS="..."` - Run the CLI with arguments
- `make docs` - Run docs dev server

### Testing
- `make test` - Run all pytest tests
- `make test_fast` - Run fast tests (exclude slow/nondeterministic)
- `make test_flaky` - Repeat fast tests to detect flaky tests
- `make test_slow` - Run slow tests only
- `make test_nondeterministic` - Run nondeterministic tests only

### Code Quality
- `make fmt` - Format with ruff + jq (JSON)
- `make ruff` - Run ruff linter
- `make vulture` - Find dead code
- `make ty` - Run type checker
- `make ci` - Run all CI checks

### Release
- `make bump_version BUMP=patch` - Bump version, commit, and tag
