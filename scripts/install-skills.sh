#!/usr/bin/env bash
# Downloads the usage skill from the CLI-Template repository into .claude/skills/
set -euo pipefail

REPO="Miyamura80/CLI-Template"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

dir=".claude/skills/usage"
mkdir -p "${dir}"

echo "Downloading usage skill..."
curl -fsSL "${BASE_URL}/${dir}/SKILL.md" -o "${dir}/SKILL.md"
echo "Installed usage skill to ${dir}/SKILL.md"
