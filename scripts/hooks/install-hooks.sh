#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/../.." && pwd)"

cd "$root_dir"

if command -v lefthook >/dev/null 2>&1; then
  lefthook install
  echo "[install-hooks] 已使用系统中的 lefthook 安装本地 hooks。"
  exit 0
fi

if command -v npx >/dev/null 2>&1; then
  npx lefthook@latest install
  echo "[install-hooks] 未检测到系统级 lefthook，已通过 npx 安装本地 hooks。"
  exit 0
fi

echo "[install-hooks] 未检测到 lefthook 或 npx，无法自动安装 hooks。"
echo "[install-hooks] 可参考：https://github.com/evilmartians/lefthook"
exit 1
