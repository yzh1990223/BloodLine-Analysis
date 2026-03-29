#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/../.." && pwd)"

backend_paths=(
  "/scan"
  "/scan-runs/latest"
  "/tables/search"
  "/analysis/cycles"
)

frontend_paths=(
  "/api/scan"
  "/api/scan-runs/latest"
  "/api/tables/search"
  "/api/analysis/cycles"
)

for path in "${backend_paths[@]}"; do
  if ! rg -F "$path" "$root_dir/backend/src/bloodline_api" >/dev/null; then
    echo "[api-sync] 后端未发现关键路径：$path"
    exit 1
  fi
done

for path in "${frontend_paths[@]}"; do
  if ! rg -F "$path" "$root_dir/frontend/src" >/dev/null; then
    echo "[api-sync] 前端未发现关键路径：$path"
    exit 1
  fi
done
