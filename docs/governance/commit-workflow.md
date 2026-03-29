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
git commit -m "feat: 增加闭环分析页面"
```

要求：

- 使用 Conventional Commits 前缀
- 描述默认用简体中文

## hooks 失败时怎么处理

### `pre-commit` 失败

常见原因：

- 提交了受保护文件
- 提交粒度过大
- 命中了文档同步或迁移提醒
- 存在基础 diff 问题

处理原则：

- 修根因，不绕过
- 不使用 `--no-verify`

### `commit-msg` 失败

说明提交信息不符合仓库规则。按提示改成：

```bash
feat: 中文说明
fix: 中文说明
docs: 中文说明
```

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
git commit -m "feat: 你的中文说明"
git push origin main
```

## 与 Superpowers 的边界

这份文档只定义仓库自己的提交建议与门禁。

- 怎么做设计、调试、验证：由 `superpowers` 决定
- 这个仓库提交时该遵守什么：由本文件和 hooks 决定
