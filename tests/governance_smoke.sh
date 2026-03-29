#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

test -f AGENTS.md
test -f backend/AGENTS.md
test -f frontend/AGENTS.md
test -f docs/governance/governance-foundation.md
test -f docs/governance/hook-matrix.md
test -f docs/governance/commit-workflow.md
test -f docs/governance/ai-hook-integration.md

bash scripts/hooks/api-frontend-sync-check.sh
bash -n scripts/hooks/pre-commit
bash -n scripts/hooks/pre-push
bash -n scripts/hooks/commit-msg
bash -n scripts/hooks/post-commit
bash -n scripts/hooks/doc-sync-check.sh
bash -n scripts/hooks/schema-migration-check.sh
bash -n scripts/hooks/protected-files-check.sh
bash -n scripts/hooks/commit-granularity-check.sh
