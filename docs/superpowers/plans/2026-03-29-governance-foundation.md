# Governance Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a practical governance foundation to BloodLine Analysis with layered `AGENTS.md`, local Git hooks, lightweight AI-session helper hooks, and GitHub Actions CI.

**Architecture:** The governance system is anchored by a root `AGENTS.md` plus backend/frontend local rules, with `lefthook` dispatching repository scripts for commit and push gates. The hook scripts focus on this repo’s real risks: oversized commits, docs drift, protected files, model-migration drift, and backend/frontend API drift. GitHub Actions mirrors the local `pre-push` checks as a remote safety net.

**Tech Stack:** Markdown, shell scripts, Lefthook, GitHub Actions, pytest, npm, Vite

---

## File Structure

- Create: `AGENTS.md`
- Create: `backend/AGENTS.md`
- Create: `frontend/AGENTS.md`
- Create: `lefthook.yml`
- Create: `scripts/hooks/pre-commit`
- Create: `scripts/hooks/commit-msg`
- Create: `scripts/hooks/post-commit`
- Create: `scripts/hooks/pre-push`
- Create: `scripts/hooks/commit-granularity-check.sh`
- Create: `scripts/hooks/doc-sync-check.sh`
- Create: `scripts/hooks/protected-files-check.sh`
- Create: `scripts/hooks/schema-migration-check.sh`
- Create: `scripts/hooks/api-frontend-sync-check.sh`
- Create: `scripts/hooks/ai-session/lang-guard.sh`
- Create: `scripts/hooks/ai-session/post-edit-reminder.sh`
- Create: `scripts/hooks/ai-session/stop-review-reminder.sh`
- Create: `scripts/hooks/ai-session/dangerous-command-guard.sh`
- Create: `.github/workflows/ci.yml`
- Create: `docs/governance/governance-foundation.md`
- Create: `docs/governance/hook-matrix.md`

