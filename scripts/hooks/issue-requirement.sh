#!/usr/bin/env bash
set -euo pipefail

list_staged_files() {
  git diff --cached --name-only --diff-filter=ACMR | sed '/^$/d'
}

is_docs_only_change() {
  local file
  local has_files=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    has_files=1
    case "$file" in
      README.md|docs/*.md|docs/**/*.md)
        ;;
      *)
        return 1
        ;;
    esac
  done < <(list_staged_files)

  [[ "$has_files" -eq 1 ]]
}

requires_issue_link() {
  local staged_count
  staged_count="$(list_staged_files | wc -l | tr -d ' ')"

  if [[ "$staged_count" -eq 0 ]]; then
    return 1
  fi

  if is_docs_only_change; then
    return 1
  fi

  return 0
}

current_issue_ref() {
  local branch_name issue_file
  branch_name="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"

  if [[ "$branch_name" =~ (^|[/_-])([0-9]+)([/_-]|$) ]]; then
    echo "${BASH_REMATCH[2]}"
    return 0
  fi

  issue_file="$(git rev-parse --git-path ISSUE_REF 2>/dev/null || echo '')"
  if [[ -n "$issue_file" && -f "$issue_file" ]]; then
    tr -d '[:space:]' < "$issue_file"
    return 0
  fi

  return 1
}
