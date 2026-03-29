# GitHub Issue 模板与任务执行规范实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 BloodLine Analysis 增加 GitHub Issue 模板与任务执行规范，使当前任务闭环体系可以落到 GitHub Issues / Project / Roadmap 的执行层。

**Architecture:** 在 `.github/ISSUE_TEMPLATE/` 下新增最小模板集合，在 `docs/governance/` 中新增对应 playbook，并把入口接入 `README.md`、`AGENTS.md`、治理基线与 governance smoke。重型增强项不在本次实现，而是显式进入后续 TODO。

**Tech Stack:** GitHub Issue forms YAML、Markdown 文档、governance smoke shell 脚本

---

### Task 1: 新增最小 Issue 模板集合

**Files:**
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/ISSUE_TEMPLATE/epic.yml`
- Create: `.github/ISSUE_TEMPLATE/task.yml`
- Create: `.github/ISSUE_TEMPLATE/bug.yml`
- Create: `.github/ISSUE_TEMPLATE/governance.yml`
- Create: `.github/ISSUE_TEMPLATE/experience-follow-up.yml`
- Test: `tests/governance_smoke.sh`

- [ ] 新增 governance smoke 校验，要求 `.github/ISSUE_TEMPLATE/` 下关键模板存在
- [ ] 创建 5 类 issue 模板与 `config.yml`
- [ ] 运行 `bash tests/governance_smoke.sh`

### Task 2: 新增 Issue / Project 使用规范

**Files:**
- Create: `docs/governance/github-issue-and-project-playbook.md`
- Modify: `docs/governance/task-closure-and-roadmap-foundation.md`

- [ ] 编写 playbook，说明 Issue 类型、Project 字段、状态流转、Milestone / Roadmap 约定
- [ ] 在任务闭环基础文档里反向链接 playbook
- [ ] 自检文档是否与现有任务闭环设计一致

### Task 3: 接入仓库入口文档

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/governance/governance-foundation.md`

- [ ] 在 README 中新增 Issue / Project 使用规范入口
- [ ] 在 AGENTS 中声明任务拆解与 Issue / Project 规范入口
- [ ] 在治理基线中补上该文档的定位说明

### Task 4: 把重方案列入后续 TODO

**Files:**
- Modify: `docs/governance/next-stage-improvement-checklist.md`

- [ ] 明确将 label 体系、Milestone 初始化建议、Project 自动化配置等列为后续 TODO
- [ ] 保持当前版本仍然是“最小可执行任务闭环”

### Task 5: 验证并收口

**Files:**
- Modify: `tests/governance_smoke.sh`

- [ ] 运行 `bash tests/governance_smoke.sh`
- [ ] 检查 `git status --short`
- [ ] 准备提交说明
