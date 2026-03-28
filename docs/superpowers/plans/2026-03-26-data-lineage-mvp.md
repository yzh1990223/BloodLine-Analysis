# Data Lineage MVP Implementation Plan

> 本文档最初是实施计划。当前已更新为 `MVP1.1` 的“实施回顾 + 后续计划”，用于让文档与现有代码保持一致。

## 1. 实施结果概览

当前仓库已经落地为一个前后端分离的单仓项目：

- `backend`
  - FastAPI
  - SQLAlchemy + Alembic + SQLite
  - `.repo` 解析
  - Java SQL 解析
  - 图构建、搜索、影响分析、闭环分析
- `frontend`
  - React + TypeScript + Vite
  - 首页扫描控制面板
  - 对象概览与对象列表
  - 详情页完整链路图
  - 影响分析页
  - 闭环分析页

## 2. 已完成的核心能力

### 2.1 后端

已完成：

- 扫描接口 `POST /api/scan`
- 最近扫描状态接口 `GET /api/scan-runs/latest`
- 对象搜索 `GET /api/tables/search`
- 详情血缘 `GET /api/tables/{table_key}/lineage`
- 影响分析 `GET /api/tables/{table_key}/impact`
- 闭环分析 `GET /api/analysis/cycles`
- Job 详情与 Java 模块详情接口

已实现的解析与推导：

- `.repo` 解析：
  - Job / Transformation 调用关系
  - 常见数据库读写 Step
  - 部分 Job SQL
  - `AccessInput` / `ExcelInput` 的对象化建模
- Java SQL 解析：
  - 静态 SQL 读写识别
  - 按语句边界保存事实边，避免错误拼接
- 图推导：
  - `READS / WRITES / CALLS`
  - `FLOWS_TO`
  - 多表闭环组分析

### 2.2 前端

已完成：

- 顶部导航与面包屑
- 首页扫描控制面板
- 首页对象概览卡片
- 搜索与局部预览
- 对象列表页
- 对象详情页
- 影响分析页
- 闭环分析页

已完成的重要交互：

- 首页卡片跳转到对象列表或闭环分析
- 节点双击进入详情页
- 详情页完整链路图支持方向性裁剪
- 点击关联对象时，链路图高亮该对象涉及的节点和边

## 3. 与最初计划相比的主要变化

### 3.1 已收缩的部分

- MySQL 元数据读取仍未接入
- 字段级血缘尚未启动
- 全量首页大图被替换为“概览 + 搜索 + 局部预览”

### 3.2 已扩展的部分

- 增加了扫描控制面板
- 增加了对象类型体系
- 增加了对象列表页
- 增加了闭环分析页
- 增强了详情页链路图和关联对象筛选

## 4. 当前仓库关键文件

### 4.1 后端

- `backend/src/bloodline_api/main.py`
- `backend/src/bloodline_api/api/routes_scan.py`
- `backend/src/bloodline_api/api/routes_tables.py`
- `backend/src/bloodline_api/api/routes_jobs.py`
- `backend/src/bloodline_api/services/lineage_query.py`
- `backend/src/bloodline_api/services/graph_builder.py`
- `backend/src/bloodline_api/parsers/repo_parser.py`
- `backend/src/bloodline_api/parsers/java_sql_parser.py`

### 4.2 前端

- `frontend/src/App.tsx`
- `frontend/src/components/AppLayout.tsx`
- `frontend/src/components/ScanControlPanel.tsx`
- `frontend/src/pages/TableSearchPage.tsx`
- `frontend/src/pages/ObjectListPage.tsx`
- `frontend/src/pages/TableDetailPage.tsx`
- `frontend/src/pages/ImpactPage.tsx`
- `frontend/src/pages/SelfLoopAnalysisPage.tsx`

## 5. 当前验证方式

后端：

```bash
cd backend
.venv/bin/pytest -q
```

前端：

```bash
cd frontend
npm test
npm run build
```

## 6. 当前遗留事项

仍待完成或增强：

- MySQL 元数据读取
- 异步扫描与进度条
- 更细的闭环路径展示
- 大规模图的进一步性能优化
- 更广泛的真实 `.repo` 兼容性
- 字段级血缘

## 7. 后续迭代建议

### Phase A：解析精度增强

- 接入 MySQL 元数据
- 扩展更多 Kettle Step
- 提升复杂 SQL 覆盖率

### Phase B：分析能力增强

- 增加闭环组详情
- 增加异常链路统计
- 增加版本对比能力

### Phase C：运行方式增强

- 扫描异步化
- 增加任务队列
- 优化大规模图的后端裁剪与前端渲染
