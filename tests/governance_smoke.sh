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
test -f docs/governance/vibe-coding-architecture-overview.md
test -f docs/governance/next-stage-improvement-checklist.md
test -f docs/governance/experience-closure-foundation.md
test -f docs/governance/task-closure-and-roadmap-foundation.md
test -f docs/governance/github-issue-and-project-playbook.md
test -f docs/experience/README.md
test -f docs/experience/indexes/experience-index.md
test -f start-backend.bat
test -f start-frontend.bat
test -f start-all.bat
test -f .github/ISSUE_TEMPLATE/config.yml
test -f .github/ISSUE_TEMPLATE/epic.yml
test -f .github/ISSUE_TEMPLATE/task.yml
test -f .github/ISSUE_TEMPLATE/bug.yml
test -f .github/ISSUE_TEMPLATE/governance.yml
test -f .github/ISSUE_TEMPLATE/experience-follow-up.yml
rg -q "Windows" README.md

bash scripts/hooks/api-frontend-sync-check.sh
bash -n scripts/hooks/pre-commit
bash -n scripts/hooks/pre-push
bash -n scripts/hooks/commit-msg
bash -n scripts/hooks/post-commit
bash -n scripts/hooks/issue-link-check.sh
bash -n scripts/hooks/issue-requirement.sh
bash -n scripts/hooks/set-issue-ref.sh
bash -n scripts/hooks/doc-sync-check.sh
bash -n scripts/hooks/schema-migration-check.sh
bash -n scripts/hooks/protected-files-check.sh
bash -n scripts/hooks/commit-granularity-check.sh
