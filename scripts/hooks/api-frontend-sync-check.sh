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

search_fixed_path() {
  local needle="$1"
  local target_dir="$2"

  if command -v rg >/dev/null 2>&1; then
    rg -F "$needle" "$target_dir" >/dev/null
    return
  fi

  grep -R -F "$needle" "$target_dir" >/dev/null
}

for path in "${backend_paths[@]}"; do
  if ! search_fixed_path "$path" "$root_dir/backend/src/bloodline_api"; then
    echo "[api-sync] 后端未发现关键路径：$path"
    exit 1
  fi
done

for path in "${frontend_paths[@]}"; do
  if ! search_fixed_path "$path" "$root_dir/frontend/src"; then
    echo "[api-sync] 前端未发现关键路径：$path"
    exit 1
  fi
done
