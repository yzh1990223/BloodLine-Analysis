# AGENTS

## 项目定位

BloodLine Analysis 是一个面向 Kettle `.repo` 文件与 Java 源码目录的数据血缘分析工具。

当前真实边界：

- 已支持：
  - `.repo`
  - Java 源码
  - 对象级 / 表级血缘
  - 影响分析
  - 闭环分析
- 未真正接入：
  - MySQL 元数据读取
  - 字段级血缘

## 仓库结构

- `backend/`：FastAPI、解析器、图构建、查询接口
- `frontend/`：React 页面、图展示、测试
- `docs/`：设计、部署、UAT、阶段总结
- `scripts/hooks/`：本地治理脚本

## 标准命令

后端：

- 安装依赖：`cd backend && uv sync --project . --extra dev`
- 测试：`cd backend && .venv/bin/pytest -q`

前端：

- 安装依赖：`cd frontend && npm install`
- 测试：`cd frontend && npm test`
- 构建：`cd frontend && npm run build`

## 提交前验证

- 修改后端代码后，必须运行：
  - `cd backend && .venv/bin/pytest -q`
- 修改前端代码后，必须运行：
  - `cd frontend && npm test`
  - `cd frontend && npm run build`
- 修改接口、页面、运行方式、能力边界或数据结构后，必须检查文档同步

## 文档同步规则

以下变更应同步检查文档：

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
- `docs/superpowers/specs/`
- `docs/superpowers/plans/`

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

