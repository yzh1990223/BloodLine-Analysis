# BloodLine Analysis

一个面向 Kettle `.repo` 文件与 Java 源码目录的数据血缘分析工具，当前聚焦对象级与表级血缘、影响分析、闭环分析和 Web 查询体验。

## 当前能力

- 解析 Kettle `.repo` 文件中的 Job、Transformation、数据库输入输出步骤和部分 Job SQL
- 解析 Java 源码中的静态 SQL，识别读写表关系
- 支持 Java 方法级事实与最小调用图归并
- 支持把部分 Spring MVC HTTP 接口继续穿透为 `api_endpoint` 终点节点
- 支持一部分 MyBatis 场景：
  - 注解 SQL
  - 同 stem XML Mapper 的最小静态 SQL
- 支持在扫描时实时接入 MySQL `information_schema` 元数据
- 支持按库白名单读取 metadata，并将表 / 视图归并到统一对象图
- 使用独立元数据表 `object_metadata` / `object_metadata_columns` 保存最新 metadata
- 支持从 `INFORMATION_SCHEMA.VIEWS.VIEW_DEFINITION` 解析视图血缘
- 视图解析失败时不会中断整次扫描，详情页会展示具体失败原因
- 统一构建对象级血缘图，并派生 `FLOWS_TO` 表级关系
- 支持对象类型区分：
  - `data_table`
  - `table_view`
  - `source_table`
  - `source_file`
- 提供 Web 页面：
  - 扫描控制面板
  - 首页对象概览
  - 按类型对象列表
  - 最近一次扫描失败汇总
  - 对象详情与完整链路图
  - 影响分析
  - 闭环分析
  - 最近扫描输入自动回填

## 当前限制

- 当前只做到对象级 / 表级血缘，未实现字段级血缘
- 扫描是同步执行的，每次重新扫描都会先清空旧图，再全量重建
- 动态 SQL、自定义 Step、复杂脚本类处理仍然是部分覆盖
- 高动态 MyBatis XML、ORM 自动生成 SQL 和字段级链路仍未覆盖
- HTTP API 节点当前仅支持 Spring MVC 常见映射注解，不支持 RPC / Feign / OpenAPI 同步
- MySQL metadata 当前读取的是“最新版本”，还未做独立缓存式同步流程

## 项目结构

- `backend`：FastAPI 服务、解析器、图构建与查询逻辑
- `frontend`：React + Vite 页面
- `docs`：设计、实施、部署和 UAT 文档
- `scripts/hooks`：本地 Git hooks、专项治理脚本、AI 会话 hooks 骨架

## 启动后端

```bash
cd backend
UV_CACHE_DIR='/Users/nathan/Documents/GithubProjects/BloodLine Analysis/.uv-cache' uv sync --project . --extra dev
.venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/uvicorn bloodline_api.main:app --host 127.0.0.1 --port 8000
```

开发模式也可以用：

```bash
cd backend
PYTHONPATH=src .venv/bin/uvicorn bloodline_api.main:app --reload
```

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发环境默认通过 Vite 代理访问同机后端 `/api`。

## Windows 双击启动

如果你在 Windows 环境下使用项目根目录，可以直接双击这些脚本：

- `start-backend.bat`
  - 自动执行后端 Alembic 迁移
  - 启动 `http://127.0.0.1:8000`
- `start-frontend.bat`
  - 启动 `http://127.0.0.1:5173`
- `start-all.bat`
  - 同时打开前后端两个独立窗口

首次使用前请先完成依赖安装：

```powershell
cd backend
uv sync --project . --extra dev

cd ../frontend
npm install
```

如果依赖缺失，`.bat` 脚本会给出中文提示，而不是直接闪退。

## 样例扫描

启动后端后，可以使用仓库内置样例触发一次扫描：

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "tests/fixtures/sample.repo.xml",
    "java_source_root": "tests/fixtures/java"
  }'
```

样例会构建出这条链路：

- `ods.orders -> dm.user_order_summary`
- `dm.user_order_summary -> app.order_dashboard`

也支持只传一个输入源：

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "tests/fixtures/repository.xml"
  }'
```

说明：

- `repo_path` 和 `java_source_root` 只要有一个非空即可触发扫描
- 带空格的路径可以直接传真实路径，后端也兼容 `\ ` 形式的 shell 转义路径
- `mysql_dsn` 现在会在扫描时实时读取 MySQL metadata
- 可选传 `metadata_databases` 指定要读取的库白名单；不传时会回退到 DSN 默认库

带 metadata 的扫描示例：

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "tests/fixtures/sample.repo.xml",
    "mysql_dsn": "mysql+pymysql://user:pass@localhost/winddf",
    "metadata_databases": ["winddf"]
  }'
```

## 主要页面

- `/`
  - 扫描控制面板（最近一次扫描输入自动回填）
  - 对象概览卡片
  - 搜索与局部预览
- `/objects`
  - 按类型浏览对象
- `/tables/:tableKey`
  - 详情页、直接上下游、完整链路图、API 终点节点、关联对象高亮、元数据摘要
  - 视图对象会展示 `VIEW_DEFINITION` 解析状态与失败原因
- `/tables/:tableKey/impact`
  - 最多 3 跳影响分析
- `/analysis/cycles`
  - 多表闭环分组分析
- `/scan-failures`
  - 最近一次扫描失败汇总，按来源类型和文件聚合展示 Kettle、Java 和 MySQL metadata 的失败项
  - 每条失败会展示文件路径、失败类型、失败原因，以及相关对象或 SQL 片段摘要，方便定位局部解析问题

## 常用接口

- `POST /api/scan`
- `GET /api/scan-runs/latest`
- `GET /api/tables/search?q=`
- `GET /api/tables/{table_key}/lineage`
- `GET /api/tables/{table_key}/impact`
- `GET /api/analysis/cycles`
- `GET /api/scan-runs/latest/failures`
- `GET /api/jobs`
- `GET /api/jobs/{job_key}`
- `GET /api/java-modules/{module_key}`

## 开发与验证

后端测试：

```bash
cd backend
.venv/bin/pytest -q
```

前端测试与构建：

```bash
cd frontend
npm test
npm run build
```

## 治理体系

仓库当前已经引入第一版治理体系，包括：

- 根目录与子目录 `AGENTS.md`
- `lefthook.yml`
- 本地 Git hooks
- AI 会话 hooks 骨架
- GitHub Actions CI

关键治理文档：

- `docs/governance/governance-foundation.md`
- `docs/governance/task-closure-and-roadmap-foundation.md`
- `docs/governance/hook-matrix.md`
- `docs/governance/commit-workflow.md`
- `docs/governance/ai-hook-integration.md`
- `docs/governance/experience-closure-foundation.md`
- `docs/governance/superpowers-collaboration-principles.md`
- `docs/experience/README.md`

### 启用本地 hooks

先确保本机已安装 `lefthook`，然后在仓库根目录执行：

```bash
bash scripts/hooks/install-hooks.sh
```

如果安装成功，后续执行 `git commit` / `git push` 时会自动触发本地门禁。

### 当前本地门禁

- `pre-commit`
  - 受保护文件检查
  - 提交粒度检查
  - 文档同步提醒
  - 模型/迁移联动提醒
- `commit-msg`
  - Conventional Commits 校验
- `post-commit`
  - 提交后同步提醒
- `pre-push`
  - 后端测试
  - 前端测试
  - 前端构建
  - API/前端同步检查

## 任务闭环与 Roadmap

当前仓库已经补充了任务闭环治理设计，用于把 spec / plan、GitHub Issues、Project、Milestone、Roadmap 和经验沉淀闭环串起来。

任务体系入口文档：

- `docs/governance/task-closure-and-roadmap-foundation.md`
- `docs/governance/github-issue-and-project-playbook.md`

这套体系的定位是：

- spec / plan 负责设计与拆解
- Epic / Task 负责执行
- GitHub Project 负责状态可视化
- Milestone / Roadmap 负责阶段推进和发展历程
- `docs/experience/` 负责执行后的经验回灌

### 推荐日常使用顺序

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm test
cd frontend && npm run build
bash tests/governance_smoke.sh
git add <明确文件列表>
git commit -m "feat: 你的中文说明"
git push origin main
```
