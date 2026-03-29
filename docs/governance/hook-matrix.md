# Hook Matrix

## Git Hooks

| Hook | 位置 | 作用 | 触发时机 |
|---|---|---|---|
| pre-commit | `scripts/hooks/pre-commit` | 基础 diff 检查 | `git commit` |
| commit-granularity-check | `scripts/hooks/commit-granularity-check.sh` | 控制提交粒度 | `git commit` |
| doc-sync-check | `scripts/hooks/doc-sync-check.sh` | 提醒文档同步 | `git commit` / `git push` |
| protected-files-check | `scripts/hooks/protected-files-check.sh` | 阻止误提交 `.db` / `.env` | `git commit` |
| schema-migration-check | `scripts/hooks/schema-migration-check.sh` | 模型与迁移/设计文档联动提醒 | `git commit` |
| commit-msg | `scripts/hooks/commit-msg` | 校验提交信息格式 | 输入 commit message 后 |
| post-commit | `scripts/hooks/post-commit` | 提交后提醒 | commit 成功后 |
| pre-push | `scripts/hooks/pre-push` | 推送前运行测试、构建和专项检查 | `git push` |
| api-frontend-sync-check | `scripts/hooks/api-frontend-sync-check.sh` | 检查关键 API 路径是否在前后端同时存在 | `git push` |
| install-hooks | `scripts/hooks/install-hooks.sh` | 安装 lefthook 到本地 `.git/hooks` | 手动执行 |
| governance-smoke | `tests/governance_smoke.sh` | 检查治理文档和关键脚本是否完整可运行 | 手动执行 / CI |

## AI Session Hooks

| Hook | 位置 | 作用 | 当前状态 |
|---|---|---|---|
| lang-guard | `scripts/hooks/ai-session/lang-guard.sh` | 语言约束提醒 | 已提供骨架 |
| post-edit-reminder | `scripts/hooks/ai-session/post-edit-reminder.sh` | 编辑后规则提醒 | 已提供骨架 |
| stop-review-reminder | `scripts/hooks/ai-session/stop-review-reminder.sh` | 收尾自审提醒 | 已提供骨架 |
| dangerous-command-guard | `scripts/hooks/ai-session/dangerous-command-guard.sh` | 危险命令提醒 | 已提供骨架 |

## 推荐落地顺序

1. 先执行 `bash scripts/hooks/install-hooks.sh`
2. 先验证：
   - `cd backend && .venv/bin/pytest -q`
   - `cd frontend && npm test`
   - `cd frontend && npm run build`
   - `bash tests/governance_smoke.sh`
3. 再开始日常 `commit` / `push`

## 相关文档

- `docs/governance/commit-workflow.md`
- `docs/governance/ai-hook-integration.md`
