#!/usr/bin/env bash
set -euo pipefail

changed="$(git diff --cached --name-only)"

if echo "$changed" | grep -E '^backend/src/bloodline_api/models.py$' >/dev/null; then
  if ! echo "$changed" | grep -E '^(backend/alembic/versions/|docs/superpowers/specs/)' >/dev/null; then
    echo "[schema-migration] 检测到 models.py 改动，但暂存区没有 backend/alembic/versions/ 或 docs/superpowers/specs/ 更新。请确认是否需要同步迁移与设计文档。"
  fi
fi
