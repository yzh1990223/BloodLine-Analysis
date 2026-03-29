# Experience Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-version experience capture and feedback loop system that fits the current governance architecture.

**Architecture:** Create a docs-first experience system under `docs/experience/`, connect it into governance docs, AGENTS, README, and smoke checks, and seed it with real examples from the repository’s history.

**Tech Stack:** Markdown docs, shell smoke checks, existing governance documentation.

---

### Task 1: Add Experience Structure

**Files:**
- Create: `docs/experience/README.md`
- Create: `docs/experience/indexes/experience-index.md`
- Create: `docs/experience/digests/2026-03-experience-digest.md`

- [ ] **Step 1: Write the content for the experience landing docs**
- [ ] **Step 2: Add the index and digest with initial entries**
- [ ] **Step 3: Verify the files are present and internally consistent**

### Task 2: Seed Real Experience Entries

**Files:**
- Create: `docs/experience/incidents/2026-03-29-path-with-space-breaks-scan.md`
- Create: `docs/experience/implementation/2026-03-29-full-overview-graph-does-not-scale.md`
- Create: `docs/experience/operations/2026-03-29-dual-vite-dev-servers-cause-validation-confusion.md`
- Create: `docs/experience/governance/2026-03-29-ai-hooks-should-not-duplicate-superpowers.md`

- [ ] **Step 1: Write four real experience records using the standard template**
- [ ] **Step 2: Cross-link them from the index and digest**
- [ ] **Step 3: Check each record includes feedback actions**

### Task 3: Connect Experience Loop Into Governance

**Files:**
- Create: `docs/governance/experience-closure-foundation.md`
- Modify: `docs/governance/governance-foundation.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Add a governance entry document describing the experience loop**
- [ ] **Step 2: Add README and AGENTS entry points**
- [ ] **Step 3: Update governance foundation to reference the new layer**

### Task 4: Add Smoke Coverage

**Files:**
- Modify: `tests/governance_smoke.sh`

- [ ] **Step 1: Extend governance smoke to check experience core documents exist**
- [ ] **Step 2: Run governance smoke**
- [ ] **Step 3: Confirm smoke still stays lightweight and docs-focused**

### Task 5: Verify End-to-End

**Files:**
- Verify only

- [ ] **Step 1: Run governance smoke**
- [ ] **Step 2: Review README, AGENTS, governance docs, and experience docs for consistency**
- [ ] **Step 3: Confirm the repository now has a working first-version experience capture loop**
