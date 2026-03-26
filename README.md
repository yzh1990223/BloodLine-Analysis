# BloodLine Analysis

Data lineage MVP for Kettle `.repo` files, Java source trees, and MySQL-oriented table lineage queries.

## Workspaces

- `backend`: FastAPI service and Python lineage pipeline
- `frontend`: React + Vite user interface

## Backend

```bash
cd backend
UV_CACHE_DIR='/Users/nathan/Documents/GithubProjects/BloodLine Analysis/.uv-cache' uv sync --project . --extra dev
.venv/bin/alembic upgrade head
.venv/bin/uvicorn bloodline_api.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Sample scan

Start the backend, then trigger a scan with the bundled fixtures:

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "tests/fixtures/sample.repo.xml",
    "java_source_root": "tests/fixtures/java"
  }'
```

The sample data builds this lineage chain:

- `ods.orders -> dm.user_order_summary`
- `dm.user_order_summary -> app.order_dashboard`

Useful follow-up endpoints:

- `GET /api/tables/table:dm.user_order_summary/lineage`
- `GET /api/tables/table:ods.orders/impact`
- `GET /api/jobs/job:daily_summary_job`
- `GET /api/java-modules/java_module:UserOrderDao`
