# MySQL 元数据接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让扫描流程真实接入 MySQL 元数据，并通过独立 metadata 表把表/视图与字段信息接入对象归一化、详情展示和回归测试。

**Architecture:** 先固定 metadata connector 的输入输出边界，再实现 `information_schema` 读取、独立 metadata 持久化与扫描归一化，最后补前端展示与文档收口。第一版保持同步加载和保守合并，不做字段级血缘和缓存式元数据同步。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PyMySQL, pytest, React, TypeScript

---

## File Structure

### Existing files that will be modified

- `backend/src/bloodline_api/api/routes_scan.py`
  - 扩展扫描输入，接入 `metadata_databases`
- `backend/src/bloodline_api/services/lineage_query.py`
  - 扫描流程接入 metadata loader、归一化与 metadata 持久化
- `backend/src/bloodline_api/models.py`
  - 增加独立 metadata 主表与字段表模型
- `backend/src/bloodline_api/api/routes_tables.py`
  - 对象详情与相关查询返回 metadata 摘要
- `backend/tests/test_scan_api.py`
  - 覆盖扫描输入与 metadata 路径
- `backend/tests/test_tables_api.py`
  - 覆盖详情页 metadata 返回与归一化
- `frontend/src/types.ts`
  - 增加 metadata 返回类型
- `frontend/src/api.ts`
  - 接住 metadata 字段
- `frontend/src/pages/TableDetailPage.tsx`
  - 展示数据库名、view 标识、字段摘要
- `frontend/src/__tests__/TableDetailChainGraph.test.tsx`
  - 或对应详情页测试，验证 metadata 展示
- `README.md`
  - 更新输入与能力边界
- `docs/deployment/uat-deployment-guide.md`
  - 增加 MySQL 权限与连接要求
- `docs/uat/uat-user-manual.md`
  - 增加 metadata 验证路径

### New files likely to be created

- `backend/src/bloodline_api/connectors/mysql_metadata.py`
  - metadata 请求建模、错误类型、`information_schema` 读取
- `backend/tests/test_mysql_metadata.py`
  - metadata connector 单测
- `backend/alembic/versions/0002_object_metadata_tables.py`
  - metadata 主表与字段表迁移

---

### Task 1: 固定 metadata connector 边界

**Files:**
- Create: `backend/src/bloodline_api/connectors/mysql_metadata.py`
- Modify: `backend/src/bloodline_api/api/routes_scan.py`
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Test: `backend/tests/test_mysql_metadata.py`
- Test: `backend/tests/test_scan_api.py`

- [x] **Step 1: Write failing tests for connector boundary**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Introduce `MySQLMetadataRequest` / error types**
- [x] **Step 4: Extend scan request with `metadata_databases`**
- [x] **Step 5: Run targeted tests and full backend suite**
- [x] **Step 6: Commit**

### Task 2: 读取 `information_schema` 元数据

**Files:**
- Modify: `backend/src/bloodline_api/connectors/mysql_metadata.py`
- Test: `backend/tests/test_mysql_metadata.py`

- [ ] **Step 1: Write failing tests for table/view/column loading**

```python
def test_mysql_metadata_loader_reads_tables_views_and_columns():
    loader = MySQLMetadataLoader(engine_factory=fake_engine_factory(...))
    objects = loader.load(request)
    assert {item.object_name for item in objects} == {"orders", "order_view"}
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_mysql_metadata.py::test_mysql_metadata_loader_reads_tables_views_and_columns`
Expected: FAIL because loader is not implemented yet

- [ ] **Step 3: Implement loader query path**

```python
class MySQLMetadataLoader:
    def load(self, request: MySQLMetadataRequest) -> list[MySQLMetadataObject]:
        ...
```

- [ ] **Step 4: Support whitelist filtering and default-db fallback**

```python
WHERE c.table_schema IN :schemas
```

- [ ] **Step 5: Run connector suite and full backend tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_mysql_metadata.py tests/test_scan_api.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/connectors/mysql_metadata.py backend/tests/test_mysql_metadata.py
git commit -m "feat: load mysql information schema metadata #13"
```

### Task 3: 增加独立 metadata 表持久化

**Files:**
- Modify: `backend/src/bloodline_api/models.py`
- Create: `backend/alembic/versions/0002_object_metadata_tables.py`
- Test: `backend/tests/test_models.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write failing persistence test**

```python
def test_object_metadata_tables_persist_latest_metadata(db_session):
    ...
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_models.py::test_object_metadata_tables_persist_latest_metadata`
Expected: FAIL because models do not exist yet

- [ ] **Step 3: Add `ObjectMetadata` and `ObjectMetadataColumn` models**
- [ ] **Step 4: Add Alembic migration**
- [ ] **Step 5: Run model tests and migration-related backend suite**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_models.py tests/test_tables_api.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/models.py backend/alembic/versions/0002_object_metadata_tables.py backend/tests/test_models.py backend/tests/test_tables_api.py
git commit -m "feat: persist metadata in dedicated tables #14"
```

### Task 4: 扫描流程接入 metadata 与保守归一化

**Files:**
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `backend/src/bloodline_api/connectors/mysql_metadata.py`
- Test: `backend/tests/test_tables_api.py`
- Test: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Write failing scan regression for metadata-assisted normalization**

```python
def test_scan_uses_metadata_to_mark_views_and_normalize_tables(client):
    ...
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_scan_uses_metadata_to_mark_views_and_normalize_tables`
Expected: FAIL because metadata is not consumed by scan yet

- [ ] **Step 3: Load metadata during scan and map by database/object**
- [ ] **Step 4: Apply conservative merge rules**
- [ ] **Step 5: Persist metadata rows and refresh latest snapshot**
- [ ] **Step 6: Run scan/API/full backend tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/bloodline_api/services/lineage_query.py backend/src/bloodline_api/connectors/mysql_metadata.py backend/tests/test_tables_api.py backend/tests/test_scan_api.py
git commit -m "feat: integrate mysql metadata into scan normalization #15"
```

### Task 5: 前端展示 metadata 摘要

**Files:**
- Modify: `backend/src/bloodline_api/api/routes_tables.py`
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/pages/TableDetailPage.tsx`
- Test: `frontend/src/__tests__/DetailNavigation.test.tsx`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write failing detail payload / UI tests**
- [ ] **Step 2: Run targeted tests**
- [ ] **Step 3: Expose metadata summary from backend detail routes**
- [ ] **Step 4: Render database name、view 标识和字段摘要**
- [ ] **Step 5: Run backend + frontend targeted tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py && cd ../frontend && npm test -- --run src/__tests__/DetailNavigation.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/api/routes_tables.py backend/src/bloodline_api/services/lineage_query.py frontend/src/types.ts frontend/src/api.ts frontend/src/pages/TableDetailPage.tsx
git commit -m "feat: surface metadata summaries in detail views #16"
```

### Task 6: 文档与回归测试收口

**Files:**
- Modify: `README.md`
- Modify: `docs/deployment/uat-deployment-guide.md`
- Modify: `docs/uat/uat-user-manual.md`
- Modify: `backend/tests/test_mysql_metadata.py`
- Modify: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Add missing metadata regression cases**
- [ ] **Step 2: Update README / deployment / UAT docs**
- [ ] **Step 3: Run governance smoke, backend tests, frontend build**

Run:
- `bash tests/governance_smoke.sh`
- `cd backend && PYTHONPATH=src .venv/bin/pytest -q`
- `cd frontend && npm test && npm run build`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md docs/deployment/uat-deployment-guide.md docs/uat/uat-user-manual.md backend/tests/test_mysql_metadata.py backend/tests/test_tables_api.py
git commit -m "docs: finalize mysql metadata integration coverage #17"
```
