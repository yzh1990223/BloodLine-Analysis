# 最近一次扫描失败汇总页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为最近一次扫描提供一个统一的失败汇总页，按 `Kettle / Java / MySQL Metadata` 分组、按文件聚合，帮助快速排查局部失败。

**Architecture:** 先新增 `scan_failures` 结构化失败记录表，并在 metadata 视图解析失败和 SQL 抽取失败路径接入落库；然后新增 latest failures API 返回聚合结果；最后增加前端失败汇总页和首页入口。第一版只看最近一次扫描，不做历史切换。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, React, TypeScript

---

## File Structure

### Existing files that will be modified

- `backend/src/bloodline_api/models.py`
  - 新增 `ScanFailure` 模型
- `backend/src/bloodline_api/services/lineage_query.py`
  - 扫描开始时绑定 `scan_run_id`，在各解析路径记录失败项，并提供 latest failures 聚合查询
- `backend/src/bloodline_api/api/routes_scan.py`
  - 新增 `/api/scan-runs/latest/failures`
- `backend/src/bloodline_api/parsers/sql_table_extractor.py`
  - 暴露更稳定的结构化失败信息供记录
- `backend/tests/test_scan_api.py`
  - 覆盖 latest failures API 和扫描失败记录
- `frontend/src/api.ts`
  - 新增获取 latest failures 的 API 方法
- `frontend/src/App.tsx`
  - 注册 `/scan-failures` 路由
- `frontend/src/components/AppLayout.tsx`
  - 增加失败汇总页导航入口
- `frontend/src/pages/TableSearchPage.tsx`
  - 在扫描区域增加“查看最近扫描失败汇总”入口
- `README.md`
  - 增加失败汇总页说明

### New files likely to be created

- `backend/alembic/versions/0005_scan_failures.py`
  - 新增 `scan_failures` 表
- `frontend/src/pages/ScanFailureSummaryPage.tsx`
  - 失败汇总页
- `frontend/src/__tests__/ScanFailureSummaryPage.test.tsx`
  - 页面渲染与空态测试

---

### Task 1: 新增 `scan_failures` 持久化结构

**Files:**
- Modify: `backend/src/bloodline_api/models.py`
- Create: `backend/alembic/versions/0005_scan_failures.py`
- Test: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Write the failing model persistence test**

```python
def test_scan_failure_model_persists_basic_fields(db_session):
    scan_run = ScanRun(status="completed", inputs={})
    db_session.add(scan_run)
    db_session.flush()
    failure = ScanFailure(
        scan_run_id=scan_run.id,
        source_type="metadata",
        file_path="dm.order_view",
        failure_type="view_definition_parse_failed",
        message="ParseError: unexpected token",
        object_key="view:dm.order_view",
        sql_snippet="select * from ods.orders",
    )
    db_session.add(failure)
    db_session.commit()
    assert db_session.get(ScanFailure, failure.id).source_type == "metadata"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py::test_scan_failure_model_persists_basic_fields`
Expected: FAIL because `ScanFailure` model and table do not exist

- [ ] **Step 3: Add minimal model and migration**

```python
class ScanFailure(Base):
    __tablename__ = "scan_failures"
```

- [ ] **Step 4: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py::test_scan_failure_model_persists_basic_fields`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/models.py backend/alembic/versions/0005_scan_failures.py backend/tests/test_scan_api.py
git commit -m "feat: persist structured scan failures #42"
```

### Task 2: 在 metadata 与 SQL 抽取路径记录失败项

**Files:**
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `backend/src/bloodline_api/parsers/sql_table_extractor.py`
- Test: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Write failing scan test for metadata failure capture**

```python
def test_scan_records_view_definition_failures_without_aborting(client):
    response = client.post("/api/scan", json={"mysql_dsn": "mysql+pymysql://user:pass@127.0.0.1:3306/default_db"})
    assert response.status_code == 202
    failures = client.get("/api/scan-runs/latest/failures").json()
    assert failures["summary"]["failure_count"] >= 1
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py::test_scan_records_view_definition_failures_without_aborting`
Expected: FAIL because failures are not yet persisted

- [ ] **Step 3: Record structured failures during scan**

```python
self._record_scan_failure(
    db,
    scan_run_id=scan_run.id,
    source_type="metadata",
    file_path=f"{metadata.database_name}.{metadata.object_name}",
    failure_type="view_definition_parse_failed",
    message=metadata.view_parse_error or "unknown error",
    object_key=node.key,
    sql_snippet=metadata.view_definition,
)
```

- [ ] **Step 4: Reuse SQL extractor errors for Kettle/Java failure records**

```python
reads, writes, parse_error = extract_tables_with_error(sql)
if parse_error:
    ...
```

- [ ] **Step 5: Run scan API tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py`
Expected: PASS with persisted metadata/sql failure records

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/services/lineage_query.py backend/src/bloodline_api/parsers/sql_table_extractor.py backend/tests/test_scan_api.py
git commit -m "feat: capture structured scan failures during parsing #42"
```

### Task 3: 新增 latest failures API 并按文件聚合

**Files:**
- Modify: `backend/src/bloodline_api/api/routes_scan.py`
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Test: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Write failing aggregation test**

```python
def test_latest_scan_failures_groups_items_by_source_and_file(client, db_session):
    payload = client.get("/api/scan-runs/latest/failures").json()
    assert "groups" in payload
    assert payload["groups"][0]["files"][0]["items"]
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py::test_latest_scan_failures_groups_items_by_source_and_file`
Expected: FAIL because the endpoint does not exist yet

- [ ] **Step 3: Add latest failures query + route**

```python
@router.get("/scan-runs/latest/failures")
def latest_scan_failures(...):
    ...
```

- [ ] **Step 4: Return frontend-ready grouped payload**

```python
{
  "scan_run": {...},
  "summary": {...},
  "groups": [...]
}
```

- [ ] **Step 5: Run backend tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/api/routes_scan.py backend/src/bloodline_api/services/lineage_query.py backend/tests/test_scan_api.py
git commit -m "feat: add latest scan failures api #42"
```

### Task 4: 新增失败汇总页与首页入口

**Files:**
- Create: `frontend/src/pages/ScanFailureSummaryPage.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`
- Modify: `frontend/src/pages/TableSearchPage.tsx`
- Test: `frontend/src/__tests__/ScanFailureSummaryPage.test.tsx`

- [ ] **Step 1: Write failing page test**

```tsx
it("renders grouped failures by source and file", async () => {
  renderWithRouter(<ScanFailureSummaryPage />);
  expect(await screen.findByText("MySQL Metadata")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the page test**

Run: `cd frontend && npm test -- --run src/__tests__/ScanFailureSummaryPage.test.tsx`
Expected: FAIL because page, route, and API client do not exist yet

- [ ] **Step 3: Add API client and page skeleton**

```ts
export function fetchLatestScanFailures(): Promise<ScanFailureSummaryResponse> {
  return requestJson("/api/scan-runs/latest/failures");
}
```

- [ ] **Step 4: Add route and entry links**

```tsx
<Route path="/scan-failures" element={<ScanFailureSummaryPage />} />
```

- [ ] **Step 5: Run frontend test**

Run: `cd frontend && npm test -- --run src/__tests__/ScanFailureSummaryPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ScanFailureSummaryPage.tsx frontend/src/__tests__/ScanFailureSummaryPage.test.tsx frontend/src/api.ts frontend/src/App.tsx frontend/src/components/AppLayout.tsx frontend/src/pages/TableSearchPage.tsx
git commit -m "feat: add latest scan failure summary page #42"
```

### Task 5: 收口空态、文档和回归

**Files:**
- Modify: `README.md`
- Modify: `backend/tests/test_scan_api.py`
- Modify: `frontend/src/__tests__/ScanFailureSummaryPage.test.tsx`

- [ ] **Step 1: Add empty-state tests**

```python
def test_latest_scan_failures_returns_empty_state_without_scan_runs(client):
    payload = client.get("/api/scan-runs/latest/failures").json()
    assert payload["scan_run"] is None
```

```tsx
it("renders empty state when latest scan has no failures", async () => {
  ...
});
```

- [ ] **Step 2: Run focused empty-state tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py::test_latest_scan_failures_returns_empty_state_without_scan_runs`
Expected: PASS

Run: `cd frontend && npm test -- --run src/__tests__/ScanFailureSummaryPage.test.tsx`
Expected: PASS

- [ ] **Step 3: Update README**

```md
- 新增“最近一次扫描失败汇总页”，用于排查 Kettle / Java / MySQL metadata 局部失败。
```

- [ ] **Step 4: Run final regression**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_scan_api.py && cd ../frontend && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md backend/tests/test_scan_api.py frontend/src/__tests__/ScanFailureSummaryPage.test.tsx
git commit -m "docs: finalize latest scan failure summary workflow #42"
```
