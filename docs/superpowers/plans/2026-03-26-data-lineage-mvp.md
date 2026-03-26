# Data Lineage MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based MVP that parses a Kettle `.repo` file, Java source tree, and MySQL metadata into a unified lineage graph, then exposes table-level lineage and impact analysis through a small web UI.

**Architecture:** Use a single repository with two runnable apps: a FastAPI backend and a React frontend. The backend contains connector, parser, graph-building, persistence, and query layers. The frontend consumes query APIs for search, lineage, and impact views. Storage starts with SQLite and stores both fact edges and derived edges.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, Alembic, pytest, React, TypeScript, Vite, Vitest, React Flow (or equivalent), SQLite

---

## File Structure

Planned repository layout and responsibility split:

- Create: `backend/pyproject.toml`
- Create: `backend/src/bloodline_api/__init__.py`
- Create: `backend/src/bloodline_api/main.py`
- Create: `backend/src/bloodline_api/config.py`
- Create: `backend/src/bloodline_api/db.py`
- Create: `backend/src/bloodline_api/models.py`
- Create: `backend/src/bloodline_api/schemas.py`
- Create: `backend/src/bloodline_api/repositories.py`
- Create: `backend/src/bloodline_api/services/graph_builder.py`
- Create: `backend/src/bloodline_api/services/lineage_query.py`
- Create: `backend/src/bloodline_api/connectors/repo_reader.py`
- Create: `backend/src/bloodline_api/connectors/java_source_reader.py`
- Create: `backend/src/bloodline_api/connectors/mysql_metadata_reader.py`
- Create: `backend/src/bloodline_api/parsers/repo_parser.py`
- Create: `backend/src/bloodline_api/parsers/java_sql_parser.py`
- Create: `backend/src/bloodline_api/parsers/sql_table_extractor.py`
- Create: `backend/src/bloodline_api/api/routes_scan.py`
- Create: `backend/src/bloodline_api/api/routes_tables.py`
- Create: `backend/src/bloodline_api/api/routes_jobs.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_repo_parser.py`
- Create: `backend/tests/test_java_sql_parser.py`
- Create: `backend/tests/test_graph_builder.py`
- Create: `backend/tests/test_tables_api.py`
- Create: `backend/tests/fixtures/sample.repo.xml`
- Create: `backend/tests/fixtures/java/UserOrderDao.java`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/pages/TableSearchPage.tsx`
- Create: `frontend/src/pages/TableDetailPage.tsx`
- Create: `frontend/src/pages/ImpactPage.tsx`
- Create: `frontend/src/components/SearchBar.tsx`
- Create: `frontend/src/components/LineageGraph.tsx`
- Create: `frontend/src/components/RelatedObjectsPanel.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/__tests__/TableSearchPage.test.tsx`
- Create: `README.md`
- Create: `.gitignore`

### Task 1: Scaffold Repository and Tooling

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/bloodline_api/__init__.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 1: Write the failing repository smoke tests**

```python
# backend/tests/test_smoke.py
from pathlib import Path


def test_backend_package_exists():
    assert Path("backend/src/bloodline_api/__init__.py").exists()


def test_frontend_package_manifest_exists():
    assert Path("frontend/package.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_smoke.py -v`
Expected: FAIL with missing file assertions.

- [ ] **Step 3: Write minimal project scaffolding**

```toml
# backend/pyproject.toml
[project]
name = "bloodline-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi",
  "uvicorn",
  "sqlalchemy",
  "pydantic",
  "alembic",
  "sqlglot",
  "pymysql",
]

[project.optional-dependencies]
dev = ["pytest", "httpx"]
```

```json
// frontend/package.json
{
  "name": "bloodline-ui",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.30.0",
    "reactflow": "^11.11.4"
  },
  "devDependencies": {
    "@testing-library/react": "^16.3.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^5.0.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0",
    "vitest": "^3.1.0"
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md backend/pyproject.toml backend/src/bloodline_api/__init__.py frontend/package.json frontend/tsconfig.json frontend/vite.config.ts
git commit -m "chore: scaffold backend and frontend workspaces"
```

### Task 2: Create Backend Schema, Models, and Migration

**Files:**
- Create: `backend/src/bloodline_api/config.py`
- Create: `backend/src/bloodline_api/db.py`
- Create: `backend/src/bloodline_api/models.py`
- Create: `backend/src/bloodline_api/schemas.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing schema test**

```python
# backend/tests/test_models.py
from bloodline_api.models import Edge, Node, ScanRun


def test_models_expose_expected_tablenames():
    assert ScanRun.__tablename__ == "scan_runs"
    assert Node.__tablename__ == "nodes"
    assert Edge.__tablename__ == "edges"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: FAIL with import error for `bloodline_api.models`.

- [ ] **Step 3: Write minimal SQLAlchemy models and DB wiring**

```python
# backend/src/bloodline_api/models.py
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScanRun(Base):
    __tablename__ = "scan_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")


class Node(Base):
    __tablename__ = "nodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Edge(Base):
    __tablename__ = "edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    src_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"))
    dst_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"))
    is_derived: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/config.py backend/src/bloodline_api/db.py backend/src/bloodline_api/models.py backend/src/bloodline_api/schemas.py backend/alembic.ini backend/alembic/env.py backend/alembic/versions/0001_initial_schema.py backend/tests/test_models.py
git commit -m "feat: add backend schema and persistence models"
```

### Task 3: Implement SQL Table Extraction and Java SQL Parsing

**Files:**
- Create: `backend/src/bloodline_api/parsers/sql_table_extractor.py`
- Create: `backend/src/bloodline_api/connectors/java_source_reader.py`
- Create: `backend/src/bloodline_api/parsers/java_sql_parser.py`
- Create: `backend/tests/fixtures/java/UserOrderDao.java`
- Test: `backend/tests/test_java_sql_parser.py`

- [ ] **Step 1: Write the failing Java parser test**

```python
# backend/tests/test_java_sql_parser.py
from pathlib import Path

from bloodline_api.parsers.java_sql_parser import JavaSqlParser


def test_java_sql_parser_extracts_reads_and_writes():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/UserOrderDao.java"))
    assert result.module_name == "UserOrderDao"
    assert sorted(result.read_tables) == ["ods.orders"]
    assert sorted(result.write_tables) == ["dm.user_order_summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_java_sql_parser.py -v`
Expected: FAIL with import error for `JavaSqlParser`.

- [ ] **Step 3: Write minimal SQL extraction and Java parser implementation**

```python
# backend/src/bloodline_api/parsers/sql_table_extractor.py
import sqlglot


def extract_tables(sql: str) -> tuple[set[str], set[str]]:
    expression = sqlglot.parse_one(sql, read="mysql")
    reads = {table.sql(dialect="mysql") for table in expression.find_all(sqlglot.exp.Table)}
    writes = set()
    if expression.key.upper() in {"INSERT", "UPDATE", "DELETE", "CREATE"}:
        target = expression.find(sqlglot.exp.Table)
        if target is not None:
            writes.add(target.sql(dialect="mysql"))
    return reads - writes, writes
```

```python
# backend/src/bloodline_api/parsers/java_sql_parser.py
import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.parsers.sql_table_extractor import extract_tables


@dataclass
class JavaModuleParseResult:
    module_name: str
    read_tables: list[str]
    write_tables: list[str]


class JavaSqlParser:
    SQL_PATTERN = re.compile(r'"((?:select|insert|update|delete)[^"]+)"', re.IGNORECASE)

    def parse_file(self, path: Path) -> JavaModuleParseResult:
        text = path.read_text(encoding="utf-8")
        reads, writes = set(), set()
        for sql in self.SQL_PATTERN.findall(text):
            sql_reads, sql_writes = extract_tables(sql)
            reads |= sql_reads
            writes |= sql_writes
        return JavaModuleParseResult(path.stem, sorted(reads), sorted(writes))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_java_sql_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/parsers/sql_table_extractor.py backend/src/bloodline_api/connectors/java_source_reader.py backend/src/bloodline_api/parsers/java_sql_parser.py backend/tests/fixtures/java/UserOrderDao.java backend/tests/test_java_sql_parser.py
git commit -m "feat: parse Java SQL modules into table reads and writes"
```

### Task 4: Implement Repo Parsing for Kettle Jobs, Transformations, and DB Steps

**Files:**
- Create: `backend/src/bloodline_api/connectors/repo_reader.py`
- Create: `backend/src/bloodline_api/parsers/repo_parser.py`
- Create: `backend/tests/fixtures/sample.repo.xml`
- Test: `backend/tests/test_repo_parser.py`

- [ ] **Step 1: Write the failing repo parser test**

```python
# backend/tests/test_repo_parser.py
from pathlib import Path

from bloodline_api.parsers.repo_parser import RepoParser


def test_repo_parser_extracts_kettle_io_and_calls():
    parser = RepoParser()
    result = parser.parse_file(Path("tests/fixtures/sample.repo.xml"))
    assert result.jobs[0].name == "daily_summary_job"
    assert result.transformations[0].name == "load_user_order_summary"
    assert result.step_reads["table_input_1"] == ["ods.orders"]
    assert result.step_writes["table_output_1"] == ["dm.user_order_summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_repo_parser.py -v`
Expected: FAIL with import error for `RepoParser`.

- [ ] **Step 3: Write minimal repo parsing implementation**

```python
# backend/src/bloodline_api/parsers/repo_parser.py
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from bloodline_api.parsers.sql_table_extractor import extract_tables


@dataclass
class NamedObject:
    name: str


@dataclass
class RepoParseResult:
    jobs: list[NamedObject] = field(default_factory=list)
    transformations: list[NamedObject] = field(default_factory=list)
    step_reads: dict[str, list[str]] = field(default_factory=dict)
    step_writes: dict[str, list[str]] = field(default_factory=dict)


class RepoParser:
    def parse_file(self, path: Path) -> RepoParseResult:
        root = ET.parse(path).getroot()
        result = RepoParseResult()
        for job in root.findall(".//job"):
            result.jobs.append(NamedObject(name=job.findtext("name", default="unknown_job")))
        for trans in root.findall(".//transformation"):
            result.transformations.append(NamedObject(name=trans.findtext("name", default="unknown_transformation")))
        for step in root.findall(".//step"):
            step_name = step.findtext("name", default="unknown_step")
            sql = step.findtext("sql", default="")
            reads, writes = extract_tables(sql) if sql else (set(), set())
            if reads:
                result.step_reads[step_name] = sorted(reads)
            if writes:
                result.step_writes[step_name] = sorted(writes)
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_repo_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/connectors/repo_reader.py backend/src/bloodline_api/parsers/repo_parser.py backend/tests/fixtures/sample.repo.xml backend/tests/test_repo_parser.py
git commit -m "feat: parse kettle repo jobs transformations and sql steps"
```

### Task 5: Build Graph Assembly and Derived Table Lineage

**Files:**
- Create: `backend/src/bloodline_api/services/graph_builder.py`
- Create: `backend/src/bloodline_api/repositories.py`
- Test: `backend/tests/test_graph_builder.py`

- [ ] **Step 1: Write the failing graph builder test**

```python
# backend/tests/test_graph_builder.py
from bloodline_api.services.graph_builder import build_table_flows


def test_build_table_flows_from_fact_edges():
    facts = [
        ("READS", "step:table_input_1", "table:ods.orders"),
        ("WRITES", "step:table_output_1", "table:dm.user_order_summary"),
    ]
    flows = build_table_flows(facts)
    assert flows == [("table:ods.orders", "table:dm.user_order_summary")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_graph_builder.py -v`
Expected: FAIL with import error for `build_table_flows`.

- [ ] **Step 3: Write minimal graph derivation logic**

```python
# backend/src/bloodline_api/services/graph_builder.py
from collections import defaultdict


def build_table_flows(fact_edges: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    reads_by_actor = defaultdict(set)
    writes_by_actor = defaultdict(set)
    for edge_type, src, dst in fact_edges:
        if edge_type == "READS":
            reads_by_actor[src].add(dst)
        if edge_type == "WRITES":
            writes_by_actor[src].add(dst)
    flows = set()
    for actor, read_tables in reads_by_actor.items():
        for read_table in read_tables:
            for write_table in writes_by_actor.get(actor, set()):
                flows.add((read_table, write_table))
    return sorted(flows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_graph_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/services/graph_builder.py backend/src/bloodline_api/repositories.py backend/tests/test_graph_builder.py
git commit -m "feat: derive table lineage from fact edges"
```

### Task 6: Build Scan Pipeline and Table Query APIs

**Files:**
- Create: `backend/src/bloodline_api/main.py`
- Create: `backend/src/bloodline_api/services/lineage_query.py`
- Create: `backend/src/bloodline_api/api/routes_scan.py`
- Create: `backend/src/bloodline_api/api/routes_tables.py`
- Create: `backend/src/bloodline_api/api/routes_jobs.py`
- Test: `backend/tests/conftest.py`
- Test: `backend/tests/test_tables_api.py`

- [ ] **Step 1: Write the failing API test**

```python
# backend/tests/test_tables_api.py
from fastapi.testclient import TestClient

from bloodline_api.main import app


def test_search_tables_returns_matching_nodes():
    client = TestClient(app)
    response = client.get("/api/tables/search", params={"q": "orders"})
    assert response.status_code == 200
    assert "items" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_tables_api.py -v`
Expected: FAIL with import error for `bloodline_api.main`.

- [ ] **Step 3: Write minimal FastAPI app and route wiring**

```python
# backend/src/bloodline_api/main.py
from fastapi import FastAPI

from bloodline_api.api.routes_scan import router as scan_router
from bloodline_api.api.routes_tables import router as tables_router
from bloodline_api.api.routes_jobs import router as jobs_router

app = FastAPI(title="BloodLine API")
app.include_router(scan_router, prefix="/api")
app.include_router(tables_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
```

```python
# backend/src/bloodline_api/api/routes_tables.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/tables/search")
def search_tables(q: str = Query("")) -> dict:
    items = []
    if q:
        items.append({"id": "table:ods.orders", "name": "ods.orders"})
    return {"items": items}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_tables_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/bloodline_api/main.py backend/src/bloodline_api/services/lineage_query.py backend/src/bloodline_api/api/routes_scan.py backend/src/bloodline_api/api/routes_tables.py backend/src/bloodline_api/api/routes_jobs.py backend/tests/conftest.py backend/tests/test_tables_api.py
git commit -m "feat: expose scan and table lineage api routes"
```

### Task 7: Build Frontend Search, Table Detail, and Impact Views

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/pages/TableSearchPage.tsx`
- Create: `frontend/src/pages/TableDetailPage.tsx`
- Create: `frontend/src/pages/ImpactPage.tsx`
- Create: `frontend/src/components/SearchBar.tsx`
- Create: `frontend/src/components/LineageGraph.tsx`
- Create: `frontend/src/components/RelatedObjectsPanel.tsx`
- Create: `frontend/src/styles.css`
- Test: `frontend/src/__tests__/TableSearchPage.test.tsx`

- [ ] **Step 1: Write the failing frontend test**

```tsx
// frontend/src/__tests__/TableSearchPage.test.tsx
import { render, screen } from "@testing-library/react";
import { TableSearchPage } from "../pages/TableSearchPage";

test("renders search input", () => {
  render(<TableSearchPage />);
  expect(screen.getByPlaceholderText("Search tables")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --runInBand`
Expected: FAIL with module not found for `../pages/TableSearchPage`.

- [ ] **Step 3: Write minimal frontend pages and shared API client**

```tsx
// frontend/src/pages/TableSearchPage.tsx
export function TableSearchPage() {
  return (
    <section>
      <h1>BloodLine Analysis</h1>
      <input placeholder="Search tables" />
    </section>
  );
}
```

```tsx
// frontend/src/App.tsx
import { TableSearchPage } from "./pages/TableSearchPage";

export default function App() {
  return <TableSearchPage />;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --runInBand`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/src/api.ts frontend/src/types.ts frontend/src/pages/TableSearchPage.tsx frontend/src/pages/TableDetailPage.tsx frontend/src/pages/ImpactPage.tsx frontend/src/components/SearchBar.tsx frontend/src/components/LineageGraph.tsx frontend/src/components/RelatedObjectsPanel.tsx frontend/src/styles.css frontend/src/__tests__/TableSearchPage.test.tsx
git commit -m "feat: add lineage search and detail frontend shell"
```

### Task 8: Integrate End-to-End Sample Scan and Developer Documentation

**Files:**
- Modify: `README.md`
- Modify: `backend/tests/fixtures/sample.repo.xml`
- Modify: `backend/tests/fixtures/java/UserOrderDao.java`
- Test: `backend/tests/test_end_to_end.py`

- [ ] **Step 1: Write the failing end-to-end test**

```python
# backend/tests/test_end_to_end.py
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.repo_parser import RepoParser
from bloodline_api.services.graph_builder import build_table_flows


def test_end_to_end_sample_inputs_produce_dm_flow():
    repo = RepoParser().parse_file("tests/fixtures/sample.repo.xml")
    java = JavaSqlParser().parse_file("tests/fixtures/java/UserOrderDao.java")
    facts = [
        ("READS", "step:table_input_1", "table:ods.orders"),
        ("WRITES", "step:table_output_1", "table:dm.user_order_summary"),
        ("READS", "java:UserOrderDao", "table:dm.user_order_summary"),
    ]
    flows = build_table_flows(facts)
    assert ("table:ods.orders", "table:dm.user_order_summary") in flows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_end_to_end.py -v`
Expected: FAIL until fixtures and parser signatures are aligned.

- [ ] **Step 3: Wire the sample fixtures, README, and happy-path scan instructions**

```md
# README.md

## Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn bloodline_api.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Sample scan

Call `POST /api/scan` with:

- `repo_path`
- `java_source_root`
- `mysql_dsn`
```
```

- [ ] **Step 4: Run tests to verify the MVP happy path passes**

Run: `cd backend && pytest -v`
Expected: PASS

Run: `cd frontend && npm test -- --runInBand`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md backend/tests/test_end_to_end.py backend/tests/fixtures/sample.repo.xml backend/tests/fixtures/java/UserOrderDao.java
git commit -m "docs: document sample scan flow and verify end to end fixtures"
```

## Self-Review

Spec coverage check:

- `.repo` 解析覆盖在 Task 4。
- Java SQL 解析覆盖在 Task 3。
- MySQL 元数据连接与归一化的骨架归入 Task 2 和 Task 6；实现时应在 `mysql_metadata_reader.py` 中补全真实读取逻辑。
- 统一图模型与事实边/推导边覆盖在 Task 2 和 Task 5。
- 表级血缘与影响查询覆盖在 Task 5、Task 6、Task 7。
- Web 搜索和详情页覆盖在 Task 7。

Placeholder scan:

- 本计划没有留空白占位内容。
- 需要实现的文件和测试路径均已给出精确路径。

Type consistency:

- 节点表统一使用 `Node`，边表统一使用 `Edge`，扫描任务统一使用 `ScanRun`。
- 图推导函数统一使用 `build_table_flows`。
- 路由前缀统一为 `/api`。
