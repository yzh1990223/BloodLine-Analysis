# Java 代码解析增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提升 Java 代码解析在 Spring 风格调用链和部分 MyBatis 风格下的表级血缘覆盖率与对象归并准确性。

**Architecture:** 采用三层解析方案：先增强字符串 SQL / 注解 SQL 抽取，再补方法级调用图，最后把方法级事实归并回现有 `java_module -> table` 图模型。第一版坚持保守识别，只支持稳定模式，不追求完整 Java AST 或完整 MyBatis 动态 SQL。

**Tech Stack:** Python, sqlglot, pytest, GitHub Project / Issues

---

## File Structure

### Existing files that will be modified

- `backend/src/bloodline_api/parsers/java_sql_parser.py`
  - 继续负责字符串 SQL 抽取，并为方法归属信息预留结构
- `backend/src/bloodline_api/services/lineage_query.py`
  - 消费 Java 解析结果并写入图模型
- `backend/tests/test_java_sql_parser.py`
  - 覆盖 Java 解析器单测
- `backend/tests/test_tables_api.py`
  - 覆盖 Java 解析增强后的接口级回归
- `README.md`
  - 更新 Java 解析能力边界
- `docs/superpowers/specs/2026-03-26-data-lineage-mvp-design.md`
  - 补充 Java 解析能力边界
- `docs/deployment/uat-deployment-guide.md`
  - 更新 UAT 说明

### New files likely to be created

- `backend/src/bloodline_api/parsers/java_symbol_parser.py`
  - 解析类、方法、注解与最小方法关系
- `backend/src/bloodline_api/parsers/java_call_graph.py`
  - 生成方法级调用关系
- `backend/src/bloodline_api/parsers/java_mapper_parser.py`
  - 支持 MyBatis 注解 SQL 和最小 XML Mapper
- `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
  - 将方法级事实归并成模块级 / 表级结果
- `backend/tests/fixtures/java/spring_repo/`
  - Spring 风格 fixture
- `backend/tests/fixtures/java/mybatis_mapper/`
  - MyBatis 风格 fixture

---

### Task 1: 固定方法级中间事实模型

**Files:**
- Create: `backend/src/bloodline_api/parsers/java_symbol_parser.py`
- Modify: `backend/src/bloodline_api/parsers/java_sql_parser.py`
- Test: `backend/tests/test_java_sql_parser.py`

- [ ] **Step 1: Write the failing parser model test**

```python
def test_java_parser_emits_method_scoped_statement_facts():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/spring_repo/OrderService.java"))
    assert result.methods["syncOrderSummary"].statement_ids == ["sql_0"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_parser_emits_method_scoped_statement_facts`
Expected: FAIL because `methods` or method-scoped facts do not exist yet

- [ ] **Step 3: Introduce minimal method fact structures**

```python
@dataclass(slots=True)
class JavaMethodFact:
    method_name: str
    statement_ids: list[str]
    calls: list[str]
```

- [ ] **Step 4: Extend `JavaModuleParseResult` with method-scoped facts**

```python
@dataclass(slots=True)
class JavaModuleParseResult:
    module_name: str
    read_tables: list[str]
    write_tables: list[str]
    statements: list["JavaSqlStatement"]
    methods: dict[str, JavaMethodFact]
```

- [ ] **Step 5: Run parser tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS for updated parser tests

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_sql_parser.py backend/src/bloodline_api/parsers/java_symbol_parser.py backend/tests/test_java_sql_parser.py
git commit -m "feat: add java method fact model #10"
```

### Task 2: 增强字符串 SQL 与注解 SQL 抽取

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_sql_parser.py`
- Create: `backend/src/bloodline_api/parsers/java_mapper_parser.py`
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/fixtures/java/mybatis_mapper/AnnotatedMapper.java`

- [ ] **Step 1: Write failing tests for annotation SQL**

```python
def test_java_parser_extracts_tables_from_mybatis_annotations():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/mybatis_mapper/AnnotatedMapper.java"))
    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
```

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_parser_extracts_tables_from_mybatis_annotations`
Expected: FAIL because annotation SQL is not parsed yet

- [ ] **Step 3: Add minimal annotation extraction**

```python
ANNOTATION_SQL_PATTERN = re.compile(r"@(Select|Insert|Update|Delete)\\(\"([^\"]+)\"\\)")
```

- [ ] **Step 4: Route annotation SQL through existing table extractor**

```python
for sql in extracted_annotation_sql:
    sql_reads, sql_writes = extract_tables(sql)
```

- [ ] **Step 5: Run parser suite**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS with new annotation coverage

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_sql_parser.py backend/src/bloodline_api/parsers/java_mapper_parser.py backend/tests/test_java_sql_parser.py backend/tests/fixtures/java/mybatis_mapper/AnnotatedMapper.java
git commit -m "feat: extract annotation sql facts #10"
```

### Task 3: 建立最小方法调用图

**Files:**
- Create: `backend/src/bloodline_api/parsers/java_call_graph.py`
- Modify: `backend/src/bloodline_api/parsers/java_symbol_parser.py`
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/fixtures/java/spring_repo/OrderService.java`

- [ ] **Step 1: Write failing call-graph test**

```python
def test_java_parser_tracks_simple_service_to_repository_calls():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/spring_repo/OrderService.java"))
    assert "orderRepository.syncSummary" in result.methods["syncOrderSummary"].calls
```

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_parser_tracks_simple_service_to_repository_calls`
Expected: FAIL because method calls are not detected yet

- [ ] **Step 3: Add minimal method signature and invocation detection**

```python
METHOD_DEF_PATTERN = re.compile(r"(public|private|protected)\\s+[\\w<>\\[\\]]+\\s+(\\w+)\\s*\\(")
METHOD_CALL_PATTERN = re.compile(r"(this\\.|\\w+\\.)?(\\w+)\\s*\\(")
```

- [ ] **Step 4: Emit method-level `calls` facts for stable invocation patterns**

```python
calls.append(f"{receiver}.{callee}" if receiver else callee)
```

- [ ] **Step 5: Run parser tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS with basic call graph coverage

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_symbol_parser.py backend/src/bloodline_api/parsers/java_call_graph.py backend/tests/test_java_sql_parser.py backend/tests/fixtures/java/spring_repo/OrderService.java
git commit -m "feat: add minimal java call graph #10"
```

### Task 4: 将方法级事实归并回表级血缘

**Files:**
- Create: `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- Modify: `backend/src/bloodline_api/services/lineage_query.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write failing API regression for service-chain lineage**

```python
def test_tables_api_uses_java_call_chain_to_reduce_lineage(client):
    response = client.post("/api/scan", json={"java_source_root": "tests/fixtures/java/spring_repo"})
    assert response.status_code == 202
    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage").json()
    assert any(node["name"] == "ods.orders" for node in lineage["upstream_tables"])
```

- [ ] **Step 2: Run the targeted API test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_tables_api.py::test_tables_api_uses_java_call_chain_to_reduce_lineage`
Expected: FAIL because method-chain reduction is not implemented yet

- [ ] **Step 3: Add reducer that walks method facts before creating `READS` / `WRITES` edges**

```python
def reduce_java_module_tables(module_fact: JavaModuleParseResult) -> tuple[set[str], set[str]]:
    ...
```

- [ ] **Step 4: Keep statement-level isolation to avoid false direct downstream edges**

```python
for statement in module_fact.statements:
    for read_table in statement.read_tables:
        ...
```

- [ ] **Step 5: Run backend regression tests**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py tests/test_tables_api.py`
Expected: PASS with no direct-edge regression

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_lineage_reducer.py backend/src/bloodline_api/services/lineage_query.py backend/tests/test_tables_api.py
git commit -m "feat: reduce java method facts into table lineage #10"
```

### Task 5: 增加 MyBatis XML 的最小稳定支持

**Files:**
- Modify: `backend/src/bloodline_api/parsers/java_mapper_parser.py`
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/fixtures/java/mybatis_mapper/OrderMapper.xml`

- [ ] **Step 1: Write failing test for static XML mapper SQL**

```python
def test_java_parser_extracts_static_tables_from_xml_mapper():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/mybatis_mapper/OrderMapper.java"))
    assert "ods.orders" in result.read_tables
```

- [ ] **Step 2: Run the test**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py::test_java_parser_extracts_static_tables_from_xml_mapper`
Expected: FAIL because XML mapper support is missing

- [ ] **Step 3: Parse minimal XML mapper constructs**

```python
for statement in root.findall(".//select") + root.findall(".//insert") + root.findall(".//update") + root.findall(".//delete"):
    sql = "".join(statement.itertext()).strip()
```

- [ ] **Step 4: Ignore dynamic tags that cannot be stably flattened**

```python
if any(tag in sql for tag in ("<if", "<foreach", "<choose")):
    continue
```

- [ ] **Step 5: Run parser suite**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q tests/test_java_sql_parser.py`
Expected: PASS with conservative XML coverage

- [ ] **Step 6: Commit**

```bash
git add backend/src/bloodline_api/parsers/java_mapper_parser.py backend/tests/test_java_sql_parser.py backend/tests/fixtures/java/mybatis_mapper/OrderMapper.xml
git commit -m "feat: add minimal mybatis xml support #10"
```

### Task 6: 文档、样例与回归收口

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-03-26-data-lineage-mvp-design.md`
- Modify: `docs/deployment/uat-deployment-guide.md`
- Modify: `docs/reports/2026-03-29-mvp1-summary.md`
- Test: `backend/tests/test_java_sql_parser.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Add documentation deltas for Java parsing boundaries**

```markdown
- 支持 Spring 风格 `DAO / Repository / Service` 调用链的最小归并
- 支持注解 SQL 与保守的 MyBatis XML 最小支持
- 仍不支持复杂动态 SQL 还原与字段级血缘
```

- [ ] **Step 2: Run full backend verification**

Run: `cd backend && PYTHONPATH=src .venv/bin/pytest -q`
Expected: PASS

- [ ] **Step 3: Run governance verification**

Run: `bash tests/governance_smoke.sh`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/specs/2026-03-26-data-lineage-mvp-design.md docs/deployment/uat-deployment-guide.md docs/reports/2026-03-29-mvp1-summary.md backend/tests/test_java_sql_parser.py backend/tests/test_tables_api.py
git commit -m "docs: sync java parsing enhancement boundaries #10"
```

## Spec Coverage Check

- 字符串 SQL 抽取增强：Task 1, Task 2
- 方法调用图：Task 3
- 表级归并：Task 4
- Spring 风格支持：Task 3, Task 4
- MyBatis 最小支持：Task 2, Task 5
- 保守策略与避免误连：Task 4, Task 5
- 文档与回归测试：Task 6

没有发现未覆盖的 spec 要求。

## Self-Review Notes

- 未保留 `TBD / TODO / implement later` 之类占位语句
- 任务名称与 spec 的三层方案保持一致
- 所有代码改动任务都给出了明确文件路径、最小代码骨架和验证命令
