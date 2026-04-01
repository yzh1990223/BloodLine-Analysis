# 视图定义血缘解析 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 MySQL `table_view` 节点从 `INFORMATION_SCHEMA.VIEWS.VIEW_DEFINITION` 解析底层依赖，并接入表级血缘、详情完整链路图和失败信息展示。

**Architecture:** 先扩展 MySQL metadata connector 和对象元数据存储，让视图定义、解析状态和错误信息有稳定落点；再把 view definition 解析接入扫描流程，生成 `underlying object -> table_view` 依赖边；最后补详情页失败状态展示、回归测试和文档。默认采用“分层严格”模式：视图解析失败不阻断整次扫描，但必须落库并在详情页可见。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, sqlglot, PyMySQL, pytest, React, TypeScript

---

## File Structure

### Existing files that will be modified

- `backend/src/bloodline_api/connectors/mysql_metadata.py`
  - 增加 `information_schema.views` 读取与 `view_definition` 中间结构
- `backend/src/bloodline_api/models.py`
  - 扩展 `object_metadata` 的视图定义、解析状态、错误信息字段
- `backend/src/bloodline_api/services/lineage_query.py`
  - 视图 metadata 落库、view definition 解析、视图血缘入图
- `backend/src/bloodline_api/parsers/sql_table_extractor.py`
  - 复用并加强 view definition 的对象抽取容错
- `backend/src/bloodline_api/api/routes_tables.py`
  - 详情返回中暴露视图解析状态与失败信息
- `backend/tests/test_mysql_metadata.py`
  - 覆盖 views 读取和 connector 行为
- `backend/tests/test_tables_api.py`
  - 覆盖视图血缘、详情页失败信息
- `backend/tests/test_scan_api.py`
  - 覆盖失败视图不阻断扫描
- `frontend/src/types.ts`
  - 扩展视图 metadata 摘要类型
- `frontend/src/pages/TableDetailPage.tsx`
  - 展示视图解析状态与失败信息
- `frontend/src/__tests__/DetailNavigation.test.tsx`
  - 覆盖失败信息展示
- `README.md`
  - 更新视图定义血缘能力与边界
- `docs/deployment/uat-deployment-guide.md`
  - 增加视图解析边界说明
- `docs/uat/uat-user-manual.md`
  - 增加视图失败信息查看路径

### New files likely to be created

- `backend/alembic/versions/0004_view_definition_metadata.py`
  - 为 `object_metadata` 增加视图定义与解析状态字段

---

### Task 1: 扩展 metadata connector 读取 `VIEW_DEFINITION`

**Files:**
- Modify: `backend/src/bloodline_api/connectors/mysql_metadata.py`
- Test: `backend/tests/test_mysql_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
def test_mysql_metadata_loader_reads_view_definition():
    request = MySQLMetadataRequest(
        dsn="mysql+pymysql://user:pass@127.0.0.1:3306/default_db",
        databases=["dm"],
        default_database="default_db",
    )
    loader = MySQLMetadataLoader(
        row_fetcher=lambda _: [
            {
                "database_name": "dm",
                "object_name": "order_view",
                "object_kind": "view",
                "comment": "订单视图",
                "view_definition": "select * from ods.orders",
                "column_name": "order_id",
                "data_type": "bigint",
                "ordinal_position": 1,
                "is_nullable": "NO",
                "column_comment": None,
            }
        ]
    )

    objects = loader.load(request)

    assert objects[0].object_kind == "view"
    assert objects[0].view_definition == "select * from ods.orders"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_mysql_metadata.py::test_mysql_metadata_loader_reads_view_definition`
Expected: FAIL because `MySQLMetadataObject` and query rows do not yet carry `view_definition`

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class MySQLMetadataObject:
    database_name: str
    object_name: str
    object_kind: str
    comment: str | None
    columns: list[MySQLMetadataColumn]
    view_definition: str | None = None
```

并把 SQL 扩展为同时读取：

```sql
LEFT JOIN information_schema.views v
  ON v.table_schema = c.table_schema
 AND v.table_name = c.table_name
```

以及：

```sql
v.view_definition AS view_definition
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_mysql_metadata.py::test_mysql_metadata_loader_reads_view_definition`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/connectors/mysql_metadata.py backend/tests/test_mysql_metadata.py
git commit -m "feat: load mysql view definitions #39"
```

### Task 2: 扩展 object_metadata 存储视图解析状态

**Files:**
- Modify: `backend/src/bloodline_api/models.py`
- Create: `backend/alembic/versions/0004_view_definition_metadata.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_object_metadata_persists_view_parse_status(db_session):
    node = Node(
        type="data_object",
        key="view:dm.order_view",
        name="dm.order_view",
        payload={"object_type": "table_view"},
    )
    db_session.add(node)
    db_session.flush()

    metadata = ObjectMetadata(
        node_id=node.id,
        database_name="dm",
        object_name="order_view",
        object_kind="view",
        comment="订单视图",
        metadata_source="mysql_information_schema",
        view_definition="select * from ods.orders",
        view_parse_status="failed",
        view_parse_error="ParseError: unexpected token",
    )
    db_session.add(metadata)
    db_session.commit()

    saved = db_session.get(ObjectMetadata, metadata.id)
    assert saved.view_parse_status == "failed"
    assert "unexpected token" in saved.view_parse_error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_object_metadata_persists_view_parse_status`
Expected: FAIL because model fields do not exist yet

- [ ] **Step 3: Write minimal implementation**

在 `ObjectMetadata` 中增加字段：

```python
view_definition: Mapped[str | None]
view_parse_status: Mapped[str | None]
view_parse_error: Mapped[str | None]
```

并增加 Alembic 迁移。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_object_metadata_persists_view_parse_status`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/models.py backend/alembic/versions/0004_view_definition_metadata.py backend/tests/test_tables_api.py
git commit -m "feat: persist view definition parse state #39"
```

### Task 3: 解析视图定义并建立视图血缘

**Files:**
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `backend/src/bloodline_api/parsers/sql_table_extractor.py`
- Test: `backend/tests/test_tables_api.py`
- Test: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_scan_builds_lineage_from_view_definition(client):
    response = client.post(
        "/api/scan",
        json={
            "mysql_dsn": "mysql+pymysql://user:pass@127.0.0.1:3306/default_db",
            "metadata_databases": ["dm", "ods"],
        },
    )

    assert response.status_code == 202

    lineage = client.get("/api/tables/view:dm.order_view/lineage")
    payload = lineage.json()
    upstream_keys = {item["key"] for item in payload["upstream_tables"]}
    assert "table:ods.orders" in upstream_keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_scan_builds_lineage_from_view_definition`
Expected: FAIL because view definition is not yet parsed into edges

- [ ] **Step 3: Write minimal implementation**

在 metadata 接入扫描流程中：

```python
if metadata_object.object_kind == "view" and metadata_object.view_definition:
    try:
        reads, _ = extract_sql_tables(metadata_object.view_definition)
        metadata.view_parse_status = "parsed"
        metadata.view_parse_error = None
    except Exception as exc:
        metadata.view_parse_status = "failed"
        metadata.view_parse_error = str(exc)
        reads = set()
```

并为每个读到的对象建立：

```python
underlying_node -> view_node
```

- [ ] **Step 4: Add failure-path regression**

```python
def test_failed_view_definition_does_not_break_scan(client):
    response = client.post("/api/scan", json={...})
    assert response.status_code == 202
    assert response.json()["status"] == "completed"
```

并断言：

```python
payload["table"]["metadata"]["view_parse_status"] == "failed"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py tests/test_scan_api.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/services/lineage_query.py backend/src/bloodline_api/parsers/sql_table_extractor.py backend/tests/test_tables_api.py backend/tests/test_scan_api.py
git commit -m "feat: derive lineage from mysql view definitions #39"
```

### Task 4: 在详情页展示视图解析失败信息

**Files:**
- Modify: `backend/src/bloodline_api/api/routes_tables.py`
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/TableDetailPage.tsx`
- Test: `frontend/src/__tests__/DetailNavigation.test.tsx`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write the failing tests**

```tsx
test("table detail page shows view parse failure details", async () => {
  expect(await screen.findByText("视图解析状态：失败")).toBeTruthy();
  expect(screen.getByText(/unexpected token/)).toBeTruthy();
});
```

和后端断言：

```python
assert payload["table"]["metadata"]["view_parse_status"] == "failed"
assert "unexpected token" in payload["table"]["metadata"]["view_parse_error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_table_detail_exposes_view_parse_failure && cd ../frontend && npm test -- --run src/__tests__/DetailNavigation.test.tsx`
Expected: FAIL because parse fields are not returned/rendered yet

- [ ] **Step 3: Write minimal implementation**

后端在 metadata summary 中增加：

```python
"view_parse_status": metadata.view_parse_status,
"view_parse_error": metadata.view_parse_error,
```

前端在视图详情页元数据区增加：

```tsx
<p>视图解析状态：失败</p>
<p>失败原因：{metadata.view_parse_error}</p>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_table_detail_exposes_view_parse_failure && cd ../frontend && npm test -- --run src/__tests__/DetailNavigation.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/api/routes_tables.py backend/src/bloodline_api/services/lineage_query.py frontend/src/types.ts frontend/src/pages/TableDetailPage.tsx frontend/src/__tests__/DetailNavigation.test.tsx backend/tests/test_tables_api.py
git commit -m "feat: surface view parse failures in detail page #39"
```

### Task 5: 文档与回归测试收口

**Files:**
- Modify: `README.md`
- Modify: `docs/deployment/uat-deployment-guide.md`
- Modify: `docs/uat/uat-user-manual.md`
- Modify: `backend/tests/test_mysql_metadata.py`
- Modify: `backend/tests/test_tables_api.py`
- Modify: `backend/tests/test_scan_api.py`

- [ ] **Step 1: Add final regression coverage**

补齐：

- 成功视图解析
- 失败视图解析但扫描完成
- 详情页错误信息返回

- [ ] **Step 2: Update docs**

README 与 UAT/部署文档写清：

- 视图定义来自 `INFORMATION_SCHEMA.VIEWS`
- 解析失败不会中断整次扫描
- 失败信息可在视图详情页查看

- [ ] **Step 3: Run full verification**

Run:
- `bash tests/governance_smoke.sh`
- `cd backend && PYTHONPATH=src .venv/bin/pytest -q`
- `cd frontend && npm test && npm run build`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md docs/deployment/uat-deployment-guide.md docs/uat/uat-user-manual.md backend/tests/test_mysql_metadata.py backend/tests/test_tables_api.py backend/tests/test_scan_api.py
git commit -m "docs: finalize view definition lineage rollout #39"
```

