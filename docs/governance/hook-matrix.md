# Hook Matrix

## Git Hooks

| Hook | 位置 | 作用 |
|---|---|---|
| pre-commit | `scripts/hooks/pre-commit` | 基础 diff 检查 |
| commit-granularity-check | `scripts/hooks/commit-granularity-check.sh` | 控制提交粒度 |
| doc-sync-check | `scripts/hooks/doc-sync-check.sh` | 提醒文档同步 |
| protected-files-check | `scripts/hooks/protected-files-check.sh` | 阻止误提交 `.db` / `.env` |
| schema-migration-check | `scripts/hooks/schema-migration-check.sh` | 模型与迁移/设计文档联动提醒 |
| commit-msg | `scripts/hooks/commit-msg` | 校验提交信息格式 |
| post-commit | `scripts/hooks/post-commit` | 提交后提醒 |
| pre-push | `scripts/hooks/pre-push` | 推送前运行测试、构建和专项检查 |

## AI Session Hooks

| Hook | 位置 | 作用 |
|---|---|---|
| lang-guard | `scripts/hooks/ai-session/lang-guard.sh` | 语言约束提醒 |
| post-edit-reminder | `scripts/hooks/ai-session/post-edit-reminder.sh` | 编辑后规则提醒 |
| stop-review-reminder | `scripts/hooks/ai-session/stop-review-reminder.sh` | 收尾自审提醒 |
| dangerous-command-guard | `scripts/hooks/ai-session/dangerous-command-guard.sh` | 危险命令提醒 |

