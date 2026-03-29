# Experience Reminder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a post-commit reminder that nudges contributors to capture reusable experience when a commit matches known patterns.

**Architecture:** Extend the existing `post-commit` hook with lightweight pattern matching on commit message and changed files, then point users to the new experience entry docs.

**Tech Stack:** Shell scripts, Markdown docs, governance smoke checks.

---

### Task 1: Add Reminder Rules

**Files:**
- Modify: `scripts/hooks/post-commit`

- [ ] **Step 1: Add file-path and commit-message based reminder conditions**
- [ ] **Step 2: Print category suggestions and entry doc links**
- [ ] **Step 3: Keep the hook reminder-only and non-blocking**

### Task 2: Add Regression Coverage

**Files:**
- Modify: `backend/tests/test_governance_hooks.py`

- [ ] **Step 1: Add tests covering reminder output for governance and fix commits**
- [ ] **Step 2: Run the new tests and confirm they fail first**
- [ ] **Step 3: Re-run after implementation until they pass**

### Task 3: Update Governance Docs

**Files:**
- Modify: `docs/governance/experience-closure-foundation.md`
- Modify: `docs/experience/README.md`

- [ ] **Step 1: Document that post-commit now provides experience capture nudges**
- [ ] **Step 2: Keep the docs consistent with the reminder-only positioning**

### Task 4: Verify

**Files:**
- Verify only

- [ ] **Step 1: Run targeted governance tests**
- [ ] **Step 2: Run governance smoke**
- [ ] **Step 3: Confirm commit flow remains non-blocking**
