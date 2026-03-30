#!/usr/bin/env bash
set -euo pipefail

issue_number="${1:-}"

if [[ ! "$issue_number" =~ ^[0-9]+$ ]]; then
  echo "[set-issue-ref] 用法：bash scripts/hooks/set-issue-ref.sh <issue_number>"
  exit 1
fi

issue_file="$(git rev-parse --git-path ISSUE_REF)"
printf '%s\n' "$issue_number" > "$issue_file"
echo "[set-issue-ref] 已记录当前仓库 Issue 引用：#$issue_number"
