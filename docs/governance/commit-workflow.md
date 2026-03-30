# 提交工作流

这份文档给 BloodLine Analysis 提供一套轻量、实战化的提交流程。

目标不是替代 `superpowers`，而是把仓库自己的提交约束说清楚：

- 怎么判断要不要拆分提交
- 什么时候文档应单独成批
- 本地 hooks 失败时应该怎么处理

## 提交前预检

建议先看一次工作区改动：

```bash
git status --short
git diff --name-only HEAD
git ls-files --others --exclude-standard
```

重点先判断三件事：

1. 这批改动是不是一个统一逻辑
2. 是否同时包含代码和文档
3. 是否触发了仓库里的联动规则

对非极小改动，还需要在提交前先确认：

4. 是否已经有对应的 GitHub Task / Issue

## 推荐分组方式

### 1. 业务代码批次

适用于：

- 后端接口、解析器、图构建逻辑
- 前端页面、图交互、查询流程
- 与这些代码直接配套的测试

推荐前缀：

- `feat:`
- `fix:`
- `refactor:`
- `test:`

### 2. 文档批次

适用于：

- `README.md`
- `docs/`

推荐前缀：

- `docs:`

如果本次改动很小，并且文档就是代码的一部分交付结果，也允许把代码和文档放在同一批；但默认更推荐拆开。

### 3. 治理/工具链批次

适用于：

- `scripts/hooks/`
- `lefthook.yml`
- `.github/workflows/`
- `AGENTS.md`

推荐前缀：

- `chore:`

## 什么时候应拆分提交

建议拆分的典型场景：

- 同时改了前后端业务和治理脚本
- 同时改了功能代码和大批文档
- 同时改了多个互不相干的页面或模块

不建议拆分过细。对这个仓库来说，一次提交能清晰表达一个目的，就已经足够。

## 提交命令建议

推荐显式添加文件，不要使用：

- `git add .`
- `git add -A`

推荐：

```bash
git add backend/src/...
git add frontend/src/...
git add docs/...
```

提交信息格式：

```bash
git commit -m "feat: 增加闭环分析页面 #12"
```

要求：

- 使用 Conventional Commits 前缀
- 描述默认用简体中文
- 非极小改动必须在提交信息中包含 `#<issue_number>`

## Issue / Task 关联规则

默认规则：

- 任何非极小改动，开始实现前都应先有关联的 GitHub Task / Issue
- 纯文档微调是当前唯一默认豁免场景

本仓库当前支持两种本地关联方式：

1. 分支名带上 issue 编号  
   例如：`codex/10-java-parsing`

2. 在当前仓库写入本地 issue 引用  
   执行：

```bash
bash scripts/hooks/set-issue-ref.sh 10
```

然后在提交信息中包含相同编号，例如：

```bash
git commit -m "feat: 增加循环边次数 #10"
```

## hooks 失败时怎么处理

### `pre-commit` 失败

常见原因：

- 提交了受保护文件
- 提交粒度过大
- 命中了文档同步或迁移提醒
- 存在基础 diff 问题
- 检测到非极小改动，但尚未关联 GitHub Task / Issue

处理原则：

- 修根因，不绕过
- 不使用 `--no-verify`

### `commit-msg` 失败

说明提交信息不符合仓库规则。按提示改成：

```bash
feat: 中文说明 #12
fix: 中文说明 #12
docs: 中文说明
```

如果已经通过 `set-issue-ref.sh` 绑定了当前 issue，则提交信息里的编号必须与之保持一致。

### `pre-push` 失败

说明至少有一项未通过：

- 后端测试
- 前端测试
- 前端构建
- API/前端同步检查
- 治理 smoke

优先根据命令输出修复，再重新推送。

## 推荐顺序

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm test
cd frontend && npm run build
bash tests/governance_smoke.sh
git add <明确文件列表>
bash scripts/hooks/set-issue-ref.sh 12
git commit -m "feat: 你的中文说明 #12"
git push origin main
```

## 与 Superpowers 的边界

这份文档只定义仓库自己的提交建议与门禁。

- 怎么做设计、调试、验证：由 `superpowers` 决定
- 这个仓库提交时该遵守什么：由本文件和 hooks 决定
