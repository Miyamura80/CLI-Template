# Release Process

This project ships a CLI from a single version in `pyproject.toml`:

| Interface | Entry point | Distribution |
|-----------|------------|--------------|
| **CLI** | `mycli` | PyPI + GitHub Release |

## Prerequisites

### PyPI Trusted Publishing (one-time setup)

1. Go to [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/)
2. Add a **pending publisher** with:
   - PyPI project name: your package name from `pyproject.toml`
   - Owner: your GitHub username or org
   - Repository: your repo name
   - Workflow name: `release.yml`
   - Environment name: `release`
3. In your GitHub repo, go to **Settings > Environments** and create an environment called `release`

No API tokens needed - GitHub Actions authenticates via OIDC.

## Quick Release

```bash
# 1. Make sure working tree is clean
git status

# 2. Bump version, commit, and tag (default: patch)
make bump_version              # 0.1.0 → 0.1.1
make bump_version BUMP=minor   # 0.1.0 → 0.2.0
make bump_version BUMP=major   # 0.1.0 → 1.0.0

# 3. Push commit and tag - triggers the release workflow
git push && git push --tags
```

The GitHub Actions workflow will:
1. Run CI checks (`make ci`)
2. Run tests (`make test`)
3. Build the package (`uv build`)
4. Publish to PyPI (trusted publishing)
5. Create a GitHub Release with auto-generated notes

## Hotfix Release

```bash
# 1. Fix the bug on main
git checkout main
# ... make your fix, commit ...

# 2. Bump patch version
make bump_version BUMP=patch

# 3. Push
git push && git push --tags
```

## Version Format

Versions follow [Semantic Versioning](https://semver.org/):

- **MAJOR** - breaking changes
- **MINOR** - new features, backwards compatible
- **PATCH** - bug fixes, backwards compatible

The version is the single source of truth in `pyproject.toml` under `[project] version`.

## Verifying a Release

```bash
# Check the release on GitHub
gh release list

# Check the package on PyPI
pip index versions <your-package-name>

# Install from PyPI
pip install <your-package-name>
```
