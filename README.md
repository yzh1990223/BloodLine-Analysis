# BloodLine Analysis

一个面向 Kettle `.repo` 文件与 Java 源码目录的数据血缘分析工具，当前聚焦对象级与表级血缘、影响分析、闭环分析和 Web 查询体验。

## 当前能力

- 解析 Kettle `.repo` 文件中的 Job、Transformation、数据库输入输出步骤和部分 Job SQL
- 解析 Java 源码中的静态 SQL，识别读写表关系
- 统一构建对象级血缘图，并派生 `FLOWS_TO` 表级关系
- 支持对象类型区分：
  - `data_table`
  - `source_table`
  - `source_file`
- 提供 Web 页面：
  - 扫描控制面板
  - 首页对象概览
  - 按类型对象列表
  - 对象详情与完整链路图
  - 影响分析
  - 闭环分析

## 当前限制

- `mysql_dsn` 目前仅保留在扫描接口中，尚未真正接入 MySQL 元数据读取
- 当前只做到对象级 / 表级血缘，未实现字段级血缘
- 扫描是同步执行的，每次重新扫描都会先清空旧图，再全量重建
- 动态 SQL、自定义 Step、复杂脚本类处理仍然是部分覆盖

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
- `mysql_dsn` 目前不会真正参与解析

## 主要页面

- `/`
  - 扫描控制面板
  - 对象概览卡片
  - 搜索与局部预览
- `/objects`
  - 按类型浏览对象
- `/tables/:tableKey`
  - 详情页、直接上下游、完整链路图、关联对象高亮
- `/tables/:tableKey/impact`
  - 最多 3 跳影响分析
- `/analysis/cycles`
  - 多表闭环分组分析

## 常用接口

- `POST /api/scan`
- `GET /api/scan-runs/latest`
- `GET /api/tables/search?q=`
- `GET /api/tables/{table_key}/lineage`
- `GET /api/tables/{table_key}/impact`
- `GET /api/analysis/cycles`
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
