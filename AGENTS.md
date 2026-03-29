# AGENTS

## 项目事实

BloodLine Analysis 是一个面向 Kettle `.repo` 文件与 Java 源码目录的数据血缘分析工具。

当前已支持：

- `.repo`
- Java 源码
- 对象级 / 表级血缘
- 影响分析
- 闭环分析

当前未真正接入：

- MySQL 元数据读取
- 字段级血缘

当前重要事实：

- `mysql_dsn` 仍是预留字段
- 扫描当前仍是同步执行
- 每次重新扫描都会先清空旧图，再全量重建

## 仓库结构

- `backend/`：FastAPI、解析器、图构建、查询接口
- `frontend/`：React 页面、图展示、测试
- `docs/`：设计、部署、UAT、治理、阶段总结
- `scripts/hooks/`：本地治理脚本

## 必跑命令

后端改动后：

- `cd backend && .venv/bin/pytest -q`

前端改动后：

- `cd frontend && npm test`
- `cd frontend && npm run build`

治理脚本、治理文档或 CI 改动后：

- `bash tests/governance_smoke.sh`

修改接口、页面、运行方式、能力边界或数据结构后：

- 必须检查文档同步

重大 bug、治理失效、UAT 关键反馈或重要设计取舍出现后：

- 应评估是否需要沉淀到 `docs/experience/`

较大功能、治理升级或阶段性主题开始前：

- 应评估是否需要用 Epic / Task / Milestone / Roadmap 形成任务闭环

## 文档同步规则

以下路径发生改动时，应检查文档同步：

- `backend/src/bloodline_api/api/`
- `backend/src/bloodline_api/models.py`
- `backend/src/bloodline_api/services/lineage_query.py`
- `frontend/src/pages/`
- `frontend/src/components/`
- `README.md`

至少检查：

- `README.md`
- `docs/deployment/`
- `docs/uat/`
- `docs/governance/`
- `docs/superpowers/specs/`
- `docs/superpowers/plans/`

如果改动涉及提交流程、hooks、CI 或 AI 会话规则：

- 提交流程说明见 `docs/governance/commit-workflow.md`
- AI hooks 接入说明见 `docs/governance/ai-hook-integration.md`
- 经验沉淀闭环说明见 `docs/governance/experience-closure-foundation.md`

如果改动涉及任务拆解、阶段推进、Issue / Project 使用规范或 Roadmap 管理：

- 任务闭环体系说明见 `docs/governance/task-closure-and-roadmap-foundation.md`

## 提交规范

- 提交信息必须符合 Conventional Commits：
  - `feat:`
  - `fix:`
  - `docs:`
  - `refactor:`
  - `test:`
  - `chore:`
  - `style:`
- 描述默认使用简体中文

## 禁止事项

- 不要提交 `backend/*.db`
- 不要默认使用 `git add .`、`git add -A`
- 不要使用 `git commit --no-verify`
- 不要在文档里写成“已接入 MySQL 元数据”或“扫描已异步化”
- 不要在没有验证的情况下声称“已经完成”

## 协同边界

- 本文件只定义仓库事实与仓库规则
- 通用工作方法由 `superpowers` 负责
- hooks 与 CI 负责把规则落成门禁
- 协同原则见：
  - `docs/governance/superpowers-collaboration-principles.md`
