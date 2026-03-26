# BloodLine Analysis

一个面向 Kettle `.repo` 文件、Java 源码目录和 MySQL 表级血缘查询的 MVP 工具。

## 项目结构

- `backend`：FastAPI 服务与 Python 血缘分析流水线
- `frontend`：基于 React + Vite 的查询界面

## 启动后端

```bash
cd backend
UV_CACHE_DIR='/Users/nathan/Documents/GithubProjects/BloodLine Analysis/.uv-cache' uv sync --project . --extra dev
.venv/bin/alembic upgrade head
.venv/bin/uvicorn bloodline_api.main:app --reload
```

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 样例扫描

启动后端后，使用仓库内置的样例文件触发一次扫描：

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "tests/fixtures/sample.repo.xml",
    "java_source_root": "tests/fixtures/java"
  }'
```

样例数据会构建出这条血缘链路：

- `ods.orders -> dm.user_order_summary`
- `dm.user_order_summary -> app.order_dashboard`

常用查询接口：

- `GET /api/tables/table:dm.user_order_summary/lineage`
- `GET /api/tables/table:ods.orders/impact`
- `GET /api/jobs/job:daily_summary_job`
- `GET /api/java-modules/java_module:UserOrderDao`
