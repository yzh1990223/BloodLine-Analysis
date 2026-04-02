# MyBatis-Plus CRUD Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `BaseMapper<Entity>` + `@TableName` 场景增加静态 CRUD 表血缘推导，让没有显式 SQL 的 MyBatis-Plus 常见 CRUD 也能稳定挂回 `api_endpoint -> table`。

**Architecture:** 先锁定真实回归 fixture，再建立 `Entity -> @TableName`、`Mapper -> Entity`、`Mapper -> Table` 三层静态索引，随后在 Java reduction 阶段对白名单 CRUD 方法直接产出 `READS/WRITES` 表事实。整个过程坚持保守推导：只有证据链完整时才产出表，否则只记录诊断原因，不猜表名。

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, React (消费既有诊断), GitHub Project / Issues

---

## File Structure

### Existing files that will be modified

- `backend/src/bloodline_api/parsers/java_symbol_parser.py`
  - 补 `@TableName`、`BaseMapper<Entity>`、实体类型索引提取
- `backend/src/bloodline_api/parsers/java_sql_parser.py`
  - 在模块解析结果上挂实体/mapper 静态元信息
- `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
  - 为 CRUD 白名单方法增加 `Mapper -> Table` 直接推导
- `backend/src/bloodline_api/services/lineage_query.py`
  - 消费新增的 CRUD 表事实，并补充更细的诊断原因
- `backend/tests/test_java_sql_parser.py`
  - 低层静态索引、实体注解、CRUD 方法识别回归
- `backend/tests/test_tables_api.py`
  - API 端点是否通过 CRUD 推导挂到表上的端到端回归
- `README.md`
  - 更新 Java / MyBatis-Plus 支持范围
- `docs/uat/uat-user-manual.md`
  - 更新 UAT 说明，写明 CRUD 推导支持边界

### New files likely to be created

- `backend/tests/fixtures/java_mybatis_plus_crud/`
  - `ProductAnalysisController.java`
  - `ProductAnalysisService.java`
  - `ProductAnalysisTidbService.java`
  - `ProductAnalysisServiceImpl.java`
  - `ProductAnalysisTidbServiceImpl.java`
  - `RpAmFundRiskprofitMapper.java`
  - `RpAmFundRiskprofitTidbMapper.java`
  - `RpAmFundRiskprofitEntity.java`
  - `RpAmFundRiskprofitTidbEntity.java`
  - `BaseMapper.java`
  - `Page.java`
  - `LambdaQueryWrapper.java`

---

### Task 1: 锁定 BaseMapper CRUD 的真实回归样例

**Files:**
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/ProductAnalysisController.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/ProductAnalysisService.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/ProductAnalysisTidbService.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/ProductAnalysisServiceImpl.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/ProductAnalysisTidbServiceImpl.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitMapper.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitTidbMapper.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitEntity.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitTidbEntity.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/BaseMapper.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/Page.java`
- Create: `backend/tests/fixtures/java_mybatis_plus_crud/LambdaQueryWrapper.java`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write the failing fixture files**

```java
@TableName("RP_AM_FUND_RISKPROFIT")
public class RpAmFundRiskprofitEntity {}

@TableName("frms.am_product_riskprofit")
public class RpAmFundRiskprofitTidbEntity {}

public interface RpAmFundRiskprofitMapper extends BaseMapper<RpAmFundRiskprofitEntity> {}
public interface RpAmFundRiskprofitTidbMapper extends BaseMapper<RpAmFundRiskprofitTidbEntity> {}
```

- [ ] **Step 2: Add the failing API regression**

```python
def test_api_endpoint_lineage_reads_tables_through_mybatis_plus_crud(client):
    response = client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_mybatis_plus_crud"},
    )

    assert response.status_code == 202

    payload = client.get("/api/tables/search", params={"q": "/assetManagement/selectAMProductNetWorthAnalysis"})
    assert payload.status_code == 200
    api_item = next(
        item
        for item in payload.json()["items"]
        if item["key"] == "api:GET /assetManagement/selectAMProductNetWorthAnalysis"
    )
    assert api_item["payload"]["diagnostics"]["read_table_count"] == 2
```

- [ ] **Step 3: Run the targeted test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py -k mybatis_plus_crud`

Expected: FAIL because current parser cannot derive CRUD tables without explicit SQL.

- [ ] **Step 4: Commit the regression fixture**

```bash
git add backend/tests/fixtures/java_mybatis_plus_crud backend/tests/test_tables_api.py
git commit -m "test: add mybatis plus crud lineage regression #41"
```

### Task 2: 建立 Entity 和 Mapper 的静态索引

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_symbol_parser.py`
- Modify: `backend/src/bloodline_api/parsers/java_sql_parser.py`
- Test: `backend/tests/test_java_sql_parser.py`

- [ ] **Step 1: Write failing parser-level tests**

```python
def test_java_symbol_parser_extracts_table_name_annotation():
    source = read_java_source(Path("tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitEntity.java"))
    assert parse_table_name(source) == "RP_AM_FUND_RISKPROFIT"

def test_java_symbol_parser_extracts_basemapper_entity_binding():
    source = read_java_source(Path("tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitMapper.java"))
    assert parse_basemapper_entity(source) == "RpAmFundRiskprofitEntity"
```

- [ ] **Step 2: Run targeted tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py -k "table_name_annotation or basemapper_entity_binding"`

Expected: FAIL because parser does not yet extract these static facts.

- [ ] **Step 3: Add minimal symbol helpers**

```python
TABLE_NAME_PATTERN = re.compile(r'@TableName\\("([^"]+)"\\)')
BASE_MAPPER_PATTERN = re.compile(r"extends\\s+BaseMapper<\\s*([\\w\\.]+)\\s*>")

def parse_table_name(source: str) -> str | None:
    ...

def parse_basemapper_entity(source: str) -> str | None:
    ...
```

- [ ] **Step 4: Extend parse results with mapper/entity metadata**

```python
@dataclass(slots=True)
class JavaModuleParseResult:
    ...
    table_name: str | None
    basemapper_entity: str | None
```

- [ ] **Step 5: Run parser suite**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`

Expected: PASS with static metadata extraction covered.

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_symbol_parser.py backend/src/bloodline_api/parsers/java_sql_parser.py backend/tests/test_java_sql_parser.py
git commit -m "feat: index mybatis plus mapper entities #41"
```

### Task 3: 为 CRUD 白名单方法推导 READS / WRITES

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- Test: `backend/tests/test_java_sql_parser.py`

- [ ] **Step 1: Write failing reducer tests**

```python
def test_java_lineage_reducer_reads_table_from_selectpage_crud():
    reduced = reduce_java_api_endpoints(...)
    endpoint = next(item for item in reduced if item.endpoint_key == "api:GET /assetManagement/selectAMProductNetWorthAnalysis")
    assert "RP_AM_FUND_RISKPROFIT" in endpoint.read_tables
    assert "frms.am_product_riskprofit" in endpoint.read_tables
```

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py -k selectpage_crud`

Expected: FAIL because CRUD methods currently produce no table facts.

- [ ] **Step 3: Add CRUD method white-lists**

```python
CRUD_READ_METHODS = {
    "selectPage",
    "selectList",
    "selectOne",
    "selectById",
    "selectBatchIds",
    "selectMaps",
    "selectCount",
}

CRUD_WRITE_METHODS = {
    "insert",
    "updateById",
    "update",
    "deleteById",
    "delete",
    "deleteBatchIds",
}
```

- [ ] **Step 4: Add mapper-to-table fallback in call resolution**

```python
if callee in CRUD_READ_METHODS and mapper_table_name:
    return ReducedJavaMethodFact(method_name=callee, read_tables=[mapper_table_name], write_tables=[])
if callee in CRUD_WRITE_METHODS and mapper_table_name:
    return ReducedJavaMethodFact(method_name=callee, read_tables=[], write_tables=[mapper_table_name])
```

- [ ] **Step 5: Run parser/reducer tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`

Expected: PASS with CRUD-derived table facts.

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_lineage_reducer.py backend/tests/test_java_sql_parser.py
git commit -m "feat: derive crud tables from basemapper bindings #41"
```

### Task 4: 接入 `this.baseMapper` 和 `getBaseMapper()` 变体

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write failing regression for `this.baseMapper` and `getBaseMapper()`**

```python
def test_api_endpoint_lineage_reads_tables_through_base_mapper_variants(client):
    response = client.post("/api/scan", json={"java_source_root": "tests/fixtures/java_mybatis_plus_crud"})
    assert response.status_code == 202
    payload = client.get("/api/tables/search", params={"q": "/assetManagement/selectAMProductNetWorthAnalysis"}).json()
    api_item = next(item for item in payload["items"] if item["key"] == "api:GET /assetManagement/selectAMProductNetWorthAnalysis")
    assert api_item["payload"]["diagnostics"]["resolved_calls"] >= 2
```

- [ ] **Step 2: Run targeted regression**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py -k base_mapper_variants`

Expected: FAIL because current reducer only partly bridges `getBaseMapper()` custom methods.

- [ ] **Step 3: Normalize synthetic receivers**

```python
if receiver in {"baseMapper", "this.baseMapper"}:
    mapper_target = current_module.mapper_type
elif receiver == "getBaseMapper()":
    mapper_target = current_module.mapper_type
```

- [ ] **Step 4: Reuse CRUD table fallback for these targets**

```python
if mapper_target and callee in CRUD_READ_METHODS | CRUD_WRITE_METHODS:
    ...
```

- [ ] **Step 5: Run focused API tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py`

Expected: PASS with `baseMapper` and `getBaseMapper()` variants covered.

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_lineage_reducer.py backend/tests/test_java_sql_parser.py backend/tests/test_tables_api.py
git commit -m "feat: support baseMapper crud receiver variants #41"
```

### Task 5: 补诊断信息并同步文档

**Files:**
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Modify: `README.md`
- Modify: `docs/uat/uat-user-manual.md`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write failing diagnostics regression**

```python
def test_api_endpoint_payload_reports_missing_mybatis_plus_evidence(client):
    ...
    assert api_item["payload"]["diagnostics"]["unresolved_reasons"] == [
        {"call": "mapper.selectPage", "reason": "entity_without_table_name"}
    ]
```

- [ ] **Step 2: Run targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py -k missing_mybatis_plus_evidence`

Expected: FAIL because these diagnostics are not emitted yet.

- [ ] **Step 3: Add new reason labels**

```python
MYBATIS_PLUS_UNRESOLVED_REASONS = {
    "mapper_without_basemapper_entity",
    "entity_without_table_name",
    "crud_method_without_table_binding",
}
```

- [ ] **Step 4: Update public docs**

```markdown
- 支持 `BaseMapper<Entity>` + `@TableName` 的常见 CRUD 表血缘推导
- 当前不支持没有 `@TableName` 时猜测物理表
```

- [ ] **Step 5: Run full relevant verification**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py tests/test_tables_api.py`

Expected: PASS with CRUD lineage and diagnostics fully covered.

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/services/lineage_query.py README.md docs/uat/uat-user-manual.md backend/tests/test_tables_api.py
git commit -m "docs: finalize mybatis plus crud lineage rollout #41"
```

## Self-Review

- Spec coverage:
  - `BaseMapper<Entity>` + `@TableName` 证据链：Task 2
  - 读查询优先准确：Task 3
  - 写操作保守覆盖：Task 3
  - `this.baseMapper` / `getBaseMapper()`：Task 4
  - API 同时挂出两张表：Task 1 + Task 3 + Task 4
  - 新诊断原因：Task 5
  - 文档同步：Task 5
- Placeholder scan:
  - 所有任务都给了实际文件路径、测试、命令和预期结果，没有留 TODO/TBD
- Type consistency:
  - 统一使用 `table_name`、`basemapper_entity`、`CRUD_READ_METHODS`、`CRUD_WRITE_METHODS` 这些命名

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-02-mybatis-plus-crud-lineage.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
