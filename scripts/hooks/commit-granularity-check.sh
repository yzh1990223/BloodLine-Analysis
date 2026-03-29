#!/usr/bin/env bash
set -euo pipefail

count="$(git diff --cached --name-only | sed '/^$/d' | wc -l | tr -d ' ')"

if [[ "${count}" -gt 35 ]]; then
  echo "[granularity] 本次提交包含 ${count} 个文件，超过 35，建议拆分提交。"
  exit 1
fi

if [[ "${count}" -gt 20 ]]; then
  echo "[granularity] 警告：本次提交包含 ${count} 个文件，建议确认是否过大。"
fi

