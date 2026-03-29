#!/usr/bin/env bash
set -euo pipefail

if git diff --cached --name-only | grep -E '^(backend/.*\.db|\.env|\.env\..+)$' >/dev/null; then
  echo "[protected-files] 检测到不应提交的数据库或环境文件。"
  exit 1
fi

