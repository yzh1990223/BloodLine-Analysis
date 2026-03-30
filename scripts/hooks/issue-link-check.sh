#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/hooks/issue-requirement.sh
source "$SCRIPT_DIR/issue-requirement.sh"

if ! requires_issue_link; then
  exit 0
fi

if current_issue_ref >/dev/null 2>&1; then
  echo "[issue-link] 已检测到关联 Issue，可继续提交。"
  exit 0
fi

echo "[issue-link] 检测到本次为非极小改动，提交前必须关联 GitHub Task/Issue。"
echo "[issue-link] 关联方式二选一："
echo "  1. 在分支名中带上 issue 编号，例如：codex/10-java-parsing"
echo "  2. 执行：bash scripts/hooks/set-issue-ref.sh <issue_number>"
echo "[issue-link] 最终 commit message 还必须包含 #<issue_number>。"
exit 1
