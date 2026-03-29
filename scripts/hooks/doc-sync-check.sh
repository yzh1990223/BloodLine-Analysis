#!/usr/bin/env bash
set -euo pipefail

changed="$(git diff --cached --name-only)"

doc_changed=0
messages=()

if echo "$changed" | grep -E '^(README.md|docs/)' >/dev/null; then
  doc_changed=1
fi

add_message() {
  local message="$1"
  messages+=("$message")
}

if echo "$changed" | grep -E '^backend/src/bloodline_api/api/' >/dev/null; then
  add_message "[doc-sync] 检测到后端 API 改动，建议至少检查：README.md、docs/uat/、docs/deployment/。"
fi

if echo "$changed" | grep -E '^backend/src/bloodline_api/models.py$' >/dev/null; then
  add_message "[doc-sync] 检测到数据模型改动，建议至少检查：docs/superpowers/specs/、docs/deployment/。"
fi

if echo "$changed" | grep -E '^backend/src/bloodline_api/services/lineage_query.py$' >/dev/null; then
  add_message "[doc-sync] 检测到核心血缘服务改动，建议至少检查：docs/superpowers/specs/、docs/uat/、README.md。"
fi

if echo "$changed" | grep -E '^frontend/src/pages/' >/dev/null; then
  add_message "[doc-sync] 检测到页面改动，建议至少检查：README.md、docs/uat/。"
fi

if echo "$changed" | grep -E '^frontend/src/components/' >/dev/null; then
  add_message "[doc-sync] 检测到前端组件改动，建议确认是否影响：README.md、docs/uat/。"
fi

if [[ "${#messages[@]}" -gt 0 ]] && [[ "$doc_changed" -eq 0 ]]; then
  printf '%s\n' "${messages[@]}"
fi
