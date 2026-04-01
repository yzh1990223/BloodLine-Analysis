# Java API 血缘增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提升真实 Spring 工程中 `api_endpoint -> table` 的穿透率，并让 API 血缘失败原因可解释、可排查。

**Architecture:** 先补“接口/实现类”和 MyBatis-Plus 继承式 CRUD 的解析桥，再增强跨类调用目标解析和 Mapper/XML 事实桥接，最后增加 API 血缘诊断信息。整个过程坚持保守解析：唯一候选才自动绑定，多候选显式标记 unresolved，不做激进猜测。

**Tech Stack:** Python, FastAPI, sqlglot, pytest, GitHub Project / Issues

---

## File Structure

### Existing files that will be modified

- `backend/src/bloodline_api/parsers/java_symbol_parser.py`
  - 增强字段注入、声明类型、接口/实现类索引
- `backend/src/bloodline_api/parsers/java_call_graph.py`
  - 增强 receiver 目标解析与跨类调用图
- `backend/src/bloodline_api/parsers/java_sql_parser.py`
  - 增强注解 SQL 变体识别与 Mapper/XML 绑定
- `backend/src/bloodline_api/parsers/java_mapper_parser.py`
  - 增加 `resources/mapper` 搜索与更多 SQL 来源桥接
- `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
  - 把接口/实现类/Mapper 事实归并回 API 节点
- `backend/src/bloodline_api/services/lineage_query.py`
  - 消费增强后的 API 事实，并把调试信息挂到 API 节点 payload
- `backend/tests/test_java_sql_parser.py`
  - Java 解析和 SQL 事实单测
- `backend/tests/test_tables_api.py`
  - API 节点血缘和 related_objects 回归
- `README.md`
  - 更新 Java API 血缘能力边界

### New files likely to be created

- `backend/tests/fixtures/java_service_impl_bridge/`
  - `IService/ServiceImpl/BaseMapper` 继承式 CRUD fixture
- `backend/tests/fixtures/java_mapper_resources/`
  - `resources/mapper` 布局 XML fixture

---

### Task 1: 锁定首批 API 血缘回归用例

**Files:**
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/test_tables_api.py`
- Create: `backend/tests/fixtures/java_api_interface_controller/`

- [ ] **Step 1: Write failing end-to-end parser regression cases**

```python
def test_api_lineage_handles_interface_service_impl_chain():
    ...

def test_api_lineage_handles_mapper_xml_from_resources_layout():
    ...
```

- [ ] **Step 2: Write failing API regression**

```python
def test_api_endpoint_reaches_tables_through_service_impl_and_mapper(client):
    ...
```

- [ ] **Step 3: Run targeted tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py tests/test_tables_api.py`
Expected: FAIL because current parser cannot reliably bridge these real-project patterns

- [ ] **Step 4: Commit the regression fixtures and tests**

```bash
git add backend/tests/test_java_sql_parser.py backend/tests/test_tables_api.py backend/tests/fixtures/java_api_interface_controller
git commit -m "test: add java api lineage regression fixtures #41"
```

### Task 2: 固化接口注入与实现类绑定

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_symbol_parser.py`
- Modify: `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- Test: `backend/tests/test_java_sql_parser.py`

- [ ] **Step 1: Write the failing binding test**

```python
def test_java_symbol_parser_binds_service_interface_to_unique_impl():
    results = parse_java_directory(Path("tests/fixtures/java_service_impl_bridge"))
    service = results["UserController"].methods["listUsers"]
    assert "IUserService" in service.field_types["userService"]
    assert service.calls == ["userService.listUsers"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_symbol_parser_binds_service_interface_to_unique_impl`
Expected: FAIL because parser does not yet build reliable interface/impl bindings

- [ ] **Step 3: Implement minimal interface/impl index**

```python
@dataclass(slots=True)
class JavaTypeIndex:
    interface_to_impls: dict[str, list[str]]
    class_methods: dict[str, set[str]]
```

- [ ] **Step 4: Use unique implementation as the first-class resolution target**

```python
if declared_type in index.interface_to_impls and len(index.interface_to_impls[declared_type]) == 1:
    resolved_type = index.interface_to_impls[declared_type][0]
```

- [ ] **Step 5: Run focused parser tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS with new interface binding coverage

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_symbol_parser.py backend/src/bloodline_api/parsers/java_lineage_reducer.py backend/tests/test_java_sql_parser.py
git commit -m "feat: bind java service interfaces to implementations #41"
```

### Task 3: 补 MyBatis-Plus 继承式 CRUD 桥

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/fixtures/java_service_impl_bridge/*`

- [ ] **Step 1: Write the failing inherited CRUD test**

```python
def test_java_lineage_reducer_maps_serviceimpl_crud_to_base_mapper_tables():
    reduced = reduce_java_modules(load_fixture_results("java_service_impl_bridge"))
    endpoint = reduce_java_api_endpoints(load_fixture_endpoints("java_service_impl_bridge"), reduced)[0]
    assert "dm.user_info" in endpoint.read_tables
```

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_lineage_reducer_maps_serviceimpl_crud_to_base_mapper_tables`
Expected: FAIL because inherited CRUD methods are not yet bridged to mapper facts

- [ ] **Step 3: Add CRUD fallback mapping for `ServiceImpl<Mapper, Entity>`**

```python
CRUD_METHODS = {"getById", "list", "page", "save", "updateById", "removeById"}
```

- [ ] **Step 4: Resolve mapper fact source when service method comes from inherited CRUD**

```python
if method_name in CRUD_METHODS and service_impl.mapper_type:
    return mapper_facts.get(service_impl.mapper_type, EmptyFact())
```

- [ ] **Step 5: Run parser suite**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS with inherited CRUD coverage

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_lineage_reducer.py backend/tests/test_java_sql_parser.py backend/tests/fixtures/java_service_impl_bridge
git commit -m "feat: bridge inherited service crud into api lineage #41"
```

### Task 4: 增强 Mapper / XML 事实桥接

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_sql_parser.py`
- Modify: `backend/src/bloodline_api/parsers/java_mapper_parser.py`
- Test: `backend/tests/test_java_sql_parser.py`

- [ ] **Step 1: Write failing tests for `value=` 注解和 `resources/mapper` XML**

```python
def test_java_parser_reads_mapper_sql_from_resources_directory():
    result = JavaSqlParser().parse_file(Path("tests/fixtures/java_mapper_resources/OrderMapper.java"))
    assert "ods.orders" in result.read_tables
```

- [ ] **Step 2: Run targeted tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_parser_reads_mapper_sql_from_resources_directory`
Expected: FAIL because XML search is limited to sibling files and annotation variants are incomplete

- [ ] **Step 3: Support `@Select(value = "...")` and concatenated annotation strings**

```python
ANNOTATION_SQL_VALUE_PATTERN = re.compile(r"@(Select|Insert|Update|Delete)\s*\(\s*value\s*=\s*(.+?)\)", re.S)
```

- [ ] **Step 4: Extend XML lookup to common `resources/mapper` layout**

```python
candidate_xmls = sibling_xmls + resources_mapper_xmls
```

- [ ] **Step 5: Run parser tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS with resource-layout and annotation variant coverage

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_sql_parser.py backend/src/bloodline_api/parsers/java_mapper_parser.py backend/tests/test_java_sql_parser.py backend/tests/fixtures/java_mapper_resources
git commit -m "feat: broaden mapper sql source discovery #41"
```

### Task 5: 增强 API 节点表血缘回归

**Files:**
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write the failing API regression**

```python
def test_api_endpoint_lineage_reads_tables_through_service_impl_and_mapper(client):
    response = client.post("/api/scan", json={"java_source_root": "tests/fixtures/java_service_impl_bridge"})
    assert response.status_code == 202
    payload = client.get("/api/tables/search?q=/users").json()
    api_keys = {item["key"] for item in payload["tables"]}
    assert "api:GET /users" in api_keys
```

- [ ] **Step 2: Run targeted API test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_api_endpoint_lineage_reads_tables_through_service_impl_and_mapper`
Expected: FAIL because endpoint reduction still misses mapper-backed table facts

- [ ] **Step 3: Make reducer emit stable endpoint read/write table sets**

```python
endpoint.read_tables = sorted(endpoint.read_tables | inherited_read_tables)
```

- [ ] **Step 4: Run API regressions**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py`
Expected: PASS with API endpoint lineage improvements

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/services/lineage_query.py backend/src/bloodline_api/parsers/java_lineage_reducer.py backend/tests/test_tables_api.py
git commit -m "feat: improve api endpoint table lineage coverage #41"
```

### Task 6: 增加 API 血缘诊断信息与文档收口

**Files:**
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `README.md`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write failing diagnostic payload test**

```python
def test_api_endpoint_payload_includes_lineage_diagnostics(client):
    client.post("/api/scan", json={"java_source_root": "tests/fixtures/java_service_impl_bridge"})
    payload = client.get("/api/tables/search?q=/users").json()
    api_item = next(item for item in payload["tables"] if item["key"] == "api:GET /users")
    assert "diagnostics" in api_item["payload"]
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_api_endpoint_payload_includes_lineage_diagnostics`
Expected: FAIL because endpoint payload does not yet expose diagnostics

- [ ] **Step 3: Add minimal diagnostics summary**

```python
payload["diagnostics"] = {
    "resolved_calls": resolved_call_count,
    "unresolved_calls": unresolved_call_count,
    "read_table_count": len(endpoint.read_tables),
    "write_table_count": len(endpoint.write_tables),
}
```

- [ ] **Step 4: Update README scope notes**

```md
- 当前 API 血缘支持 Spring MVC + Service/Mapper 穿透、部分 MyBatis-Plus 继承式 CRUD、资源目录 XML。
```

- [ ] **Step 5: Run focused regressions**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py && bash tests/governance_smoke.sh`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/services/lineage_query.py backend/tests/test_tables_api.py README.md
git commit -m "docs: capture api lineage diagnostics and limits #41"
```
