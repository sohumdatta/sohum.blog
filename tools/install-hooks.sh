#!/usr/bin/env bash
# Installs the repo's git hooks. Hooks live outside version control: run once per clone.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
cp tools/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
echo "installed: .git/hooks/post-commit (safety-net OTS stamping after ${BLOG_STAMP_AFTER:-30} unstamped commits)"
