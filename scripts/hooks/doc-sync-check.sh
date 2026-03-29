#!/usr/bin/env bash
set -euo pipefail

changed="$(git diff --cached --name-only)"

if echo "$changed" | grep -E '^(backend/src/bloodline_api/api/|backend/src/bloodline_api/models.py|backend/src/bloodline_api/services/lineage_query.py|frontend/src/pages/|frontend/src/components/)' >/dev/null; then
  if ! echo "$changed" | grep -E '^(README.md|docs/)' >/dev/null; then
    echo "[doc-sync] 检测到接口、模型、服务或页面改动，但暂存区没有文档更新。请确认是否需要同步 README 或 docs。"
  fi
fi

