# 数据血缘分析工具 MVP 设计

> 本文档最初用于定义 MVP 范围。当前已按 `MVP1.1` 的实际落地结果更新，既保留设计意图，也反映当前代码中的真实边界。

## 1. 背景与目标

目标是为一个成熟运行系统构建数据血缘分析工具，分析对象技术栈为：

- MySQL
- Kettle
- Java

当前 MVP 的核心目标已经收敛为：

- 打通 `Kettle + Java -> 对象级 / 表级血缘`
- 支持基础影响分析
- 支持闭环分析
- 提供可用于 UAT 的 Web 查询与可视化界面

## 2. 当前输入与输出边界

### 2.1 当前实际输入

- 融合了全部 `ktr/kjb` 的 `.repo` 文件
- Java 源码目录
- `mysql_dsn` 作为接口字段保留，但尚未真正接入元数据解析

### 2.2 当前实际输出

- 首页扫描控制面板
- 首页对象概览、搜索与局部预览
- 对象列表页
- 对象详情页
- 影响分析页
- 闭环分析页

## 3. 当前成功标准

截至 `MVP1.1`，当前版本已满足：

1. 能解析 `.repo` 文件中的主要 Job、Transformation、数据库输入输出步骤，以及部分 Job SQL。
2. 能扫描 Java 源码目录并识别主要静态 SQL 的读写表。
3. 能将来源对象区分为 `data_table`、`source_table`、`source_file`。
4. 能围绕任意对象展示其直接上游和直接下游对象。
5. 能展示与该对象相关的 Job、Transformation 和 Java 模块。
6. 能执行最多 3 跳的下游影响分析。
7. 能识别至少 2 张表参与的闭环组并在页面中展示。

当前版本尚未满足：

- MySQL 元数据直连读取
- 字段级血缘
- 异步扫描
- 权限体系
- 多环境对比

## 4. 总体方案

整体仍采用“多解析器 + 统一图模型”的思路，但实现上已经偏向轻量务实：

1. 从 `.repo` 与 Java 源码提取事实边。
2. 将不同来源对象统一为图中的节点和边。
3. 通过关系库存储图实体。
4. 派生 `FLOWS_TO` 关系用于对象级 / 表级查询。
5. 通过 FastAPI 提供查询 API。
6. 通过 React 页面提供查询、分析与可视化。

部署上保持单体部署、模块可拆：

- 一个 Python 后端服务
- 一个 React 前端
- 默认 SQLite 持久化

## 5. 模块边界

### 5.1 Repo 解析器

当前重点覆盖：

- Job 与 Transformation 的调用关系
- `TableInput`
- `TableOutput`
- `ExecSQL`
- `InsertUpdate`
- `AccessInput`
- `ExcelInput`
- 部分 Job SQL

当前仍弱覆盖或未覆盖：

- 自定义插件 Step
- 复杂脚本 Step
- 高度依赖运行时变量的目标表
- 字段级映射

### 5.2 Java 解析器

当前重点覆盖：

- JDBC / 模板类静态 SQL
- MyBatis 或硬编码 SQL
- 可还原的简单字符串 SQL

当前仍弱覆盖：

- 高动态 SQL
- ORM 自动生成 SQL 的完整还原
- 方法级、字段级链路

### 5.3 元数据加载器

当前状态：

- 设计中预留
- 接口中保留 `mysql_dsn`
- 尚未真正接入 MySQL 元数据加载能力

已确认的后续设计方向：

- 通过独立 MySQL metadata loader 读取 `information_schema`
- 使用库白名单控制读取范围
- 采用独立元数据表承载最新库表与字段信息
- `data_table / table_view` 节点通过关联元数据表读取详情

### 5.4 统一图模型

当前项目真正依赖的是统一图模型，它负责：

- 承载对象节点和技术对象节点
- 区分事实边与推导边
- 支撑搜索、详情、影响分析和闭环分析

## 6. 图模型设计

### 6.1 当前节点类型

- `data_object`
  - 细分对象类型保存在 `object_type`
- `job`
- `transformation`
- `java_module`

### 6.2 当前对象类型

- `data_table`
- `source_table`
- `source_file`
- `table_view`
  - 目前仅为预留类型，当前实现中尚未稳定产出

### 6.3 当前边类型

- `CALLS`
- `READS`
- `WRITES`
- `FLOWS_TO`

### 6.4 事实边与推导边

当前实现仍坚持分离：

- 事实边：
  - `CALLS`
  - `READS`
  - `WRITES`
- 推导边：
  - `FLOWS_TO`

这使得：

- 可以单独调试解析问题
- 可以复算 `FLOWS_TO`
- 可以对闭环、自环做二次分析

## 7. 当前推导规则

MVP 当前只生成对象级 / 表级 `FLOWS_TO`。

实际推导原则包括：

1. 同一处理 actor 既读又写时，生成来源对象到目标对象的 `FLOWS_TO`。
2. Java 解析按语句边界处理，避免同一类中无关 SQL 被错误串成直接流向。
3. Repo 中的外部来源可被折叠为：
   - `source_table`
   - `source_file`
4. 每次重新扫描前先清空旧图，再全量重建。

## 8. 当前前端设计

### 8.1 首页

首页不再默认渲染全量大图，而是强调：

- 扫描控制面板
- 对象概览卡片
- 搜索
- 局部预览

这样可以避免大型图首屏拖慢页面。

### 8.2 对象详情页

详情页包含：

- 对象基础信息
- 直接上下游列表
- 完整链路图
- 关联对象高亮筛选

### 8.3 影响分析页

当前展示最多 3 跳下游影响对象。

### 8.4 闭环分析页

当前展示多表闭环组，不展示单表自环组。

## 9. 当前技术选型

### 9.1 后端

- FastAPI
- SQLAlchemy
- Alembic
- SQLite
- sqlglot

### 9.2 前端

- React
- TypeScript
- Vite
- React Router
- React Flow

## 10. 当前 SQLite 表设计

当前实现使用 SQLite 持久化，核心表只有 3 张：

- `scan_runs`
- `nodes`
- `edges`

设计原则是：

- 用最少表结构承载扫描批次、节点和边
- 事实边与推导边通过 `edges.is_derived` 区分
- 业务类型和值更多放在 `type` 与 `payload` 中，保证后续扩展空间

注意：

- 以上是**当前实际实现**
- `#3 MySQL 元数据接入` 已另有设计，计划后续新增元数据表，但尚未落地到当前代码

### 10.1 `scan_runs`

用于记录每一次扫描任务的执行情况。

主要字段：

- `id`
  - 主键，整数
- `status`
  - 扫描状态
  - 非空
  - 有索引 `ix_scan_runs_status`
- `started_at`
  - 扫描开始时间
- `finished_at`
  - 扫描结束时间
- `created_at`
  - 记录创建时间

当前用途：

- 首页扫描控制面板展示最近一次扫描状态
- 后端保留扫描历史记录
- 注意：当前重新扫描时会清空图数据，但不会清空 `scan_runs`

### 10.2 `nodes`

用于存储血缘图中的所有节点。

主要字段：

- `id`
  - 主键，整数
- `type`
  - 节点大类
  - 非空
  - 有索引 `ix_nodes_type`
- `key`
  - 节点业务唯一键
  - 非空
  - 唯一索引 `ix_nodes_key`
- `name`
  - 节点显示名称
  - 非空
- `payload`
  - JSON 扩展字段
  - 默认 `{}`
- `created_at`
  - 创建时间
  - 默认值为当前时间

当前典型节点包括：

- 数据对象节点
- Job 节点
- Transformation 节点
- Java 模块节点

### 10.4 已设计但未落地的元数据扩展

围绕 `#3 MySQL 元数据接入`，当前已确定的扩展方向是：

- 新增 `object_metadata`
  - 保存对象级最新元数据
  - 与 `nodes.id` 一对一关联
- 新增 `object_metadata_columns`
  - 保存字段级最新元数据
  - 与 `object_metadata.id` 一对多关联

设计意图：

- `nodes` 继续承担图模型主键职责
- 完整数据库元数据从 `nodes.payload` 中剥离
- `data_table / table_view` 的详情、库名、字段摘要通过元数据表读取
- 第一版只保存“当前最新元数据”，不保存按 `scan_run` 的历史快照

### 10.3 `edges`

用于存储图中的关系边。

主要字段：

- `id`
  - 主键，整数
- `type`
  - 边类型
  - 非空
  - 有索引 `ix_edges_type`
- `src_node_id`
  - 起点节点 ID
  - 外键指向 `nodes.id`
  - 有索引 `ix_edges_src_node_id`
- `dst_node_id`
  - 终点节点 ID
  - 外键指向 `nodes.id`
  - 有索引 `ix_edges_dst_node_id`
- `is_derived`
  - 是否为推导边
  - `false` 表示事实边
  - `true` 表示推导边
- `payload`
  - JSON 扩展字段
  - 默认 `{}` 
- `created_at`
  - 创建时间
  - 默认值为当前时间

当前用途：

- `READS / WRITES / CALLS` 存储原始事实
- `FLOWS_TO` 存储推导后的对象级 / 表级关系

### 10.4 当前约束与说明

- 当前没有单独的“码表”或维表
- 当前没有单独的扫描输入表、任务配置表、异常表
- 节点和边的业务语义主要靠：
  - `nodes.type`
  - `nodes.key`
  - `nodes.payload`
  - `edges.type`
  - `edges.is_derived`

## 11. 当前码值说明

### 11.1 `scan_runs.status`

当前代码中涉及的状态值包括：

- `pending`
  - 初始或默认状态
- `running`
  - 扫描执行中
- `completed`
  - 扫描成功完成
- `failed`
  - 扫描失败
  - 当前前端和接口语义已预留该值，但后端当前主流程里主要落地的是 `running` 和 `completed`

### 11.2 `nodes.type`

当前节点大类包括：

- `data_object`
  - 数据对象统一节点
  - 具体属于表、源表还是源文件，要继续看 `payload.object_type`
- `job`
  - Kettle Job
- `transformation`
  - Kettle Transformation
- `java_module`
  - Java 模块

### 11.3 `nodes.payload.object_type`

当前对象细分类包括：

- `data_table`
  - 数据表
  - 当前最常见的对象类型
  - 默认对象类型
- `source_table`
  - 外部来源表
  - 例如 AccessInput 这类来源步骤识别出的表对象
- `source_file`
  - 外部来源文件
  - 例如 ExcelInput 识别出的文件对象
- `table_view`
  - 预留类型
  - 当前实现中尚未稳定产出

### 11.4 `edges.type`

当前边类型包括：

- `CALLS`
  - 调用关系
  - 例如 `job -> transformation`
- `READS`
  - 读取关系
  - 例如 `job / transformation / java_module -> data_object`
- `WRITES`
  - 写入关系
  - 例如 `job / transformation / java_module -> data_object`
- `FLOWS_TO`
  - 推导出的流向关系
  - 例如 `source_table -> data_table`
  - 或 `data_table -> data_table`

### 11.5 `edges.is_derived`

- `false`
  - 事实边
  - 当前主要对应 `CALLS / READS / WRITES`
- `true`
  - 推导边
  - 当前主要对应 `FLOWS_TO`

### 11.6 `nodes.key` 当前命名规则

当前 `key` 同时承担了业务唯一标识和前端路由参数的作用。

主要规则如下：

- `table:{name}`
  - `data_table`
  - 例如 `table:ods.orders`
- `source_table:{name}`
  - `source_table`
- `source_file:{name}`
  - `source_file`
- `view:{name}`
  - `table_view` 预留
- `job:{name}`
  - Job 节点
- `transformation:{name}`
  - Transformation 节点
- `java_module:{name}`
  - Java 模块节点

### 11.7 `payload` 当前常见补充字段

当前 `payload` 不是严格固定结构，但在现有实现中常见字段包括：

- `source`
  - 节点或边来源
  - 如 `repo`
- `object_type`
  - 仅数据对象节点使用
- `step`
  - Repo 中步骤级读写关系的补充信息
- `entry`
  - Job SQL 或 Job entry 的补充信息

## 12. 当前已知限制

- `mysql_dsn` 尚未真正接入
- 扫描同步执行，耗时大时请求会阻塞
- 仅支持对象级 / 表级血缘
- 闭环分析仅展示闭环组，不枚举所有具体环路
- 部分复杂 Kettle Step、动态 SQL 仍然无法完整还原

## 13. 后续演进方向

后续如继续增强，优先级建议为：

1. 接入 MySQL 元数据
2. 优化大型真实 `.repo` 的覆盖率
3. 增加闭环组内具体环路展示
4. 增加异步扫描任务与进度管理
5. 逐步探索字段级血缘
