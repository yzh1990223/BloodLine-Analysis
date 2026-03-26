# 数据血缘分析工具 MVP 设计

## 1. 背景与目标

目标是为一个已稳定运行的成熟系统构建一个数据血缘分析 MVP。被分析对象的技术栈为：

- MySQL
- Kettle
- Java

本工具的第一阶段只解决最核心的问题：打通 `Kettle + Java -> MySQL` 的表级血缘，并支持基础影响分析。

MVP 的输入范围已经明确为：

- 融合了全部 `ktr/kjb` 的一个 `.repo` 文件
- Java 源代码目录
- 直连 MySQL 读取元数据

MVP 的输出形态已经明确为：

- 一个轻量 Web 页面
- 支持搜索表、查看上下游、查看涉及的 Kettle 作业和 Java 模块

MVP 的实现方式已经明确为：

- Python 为主
- 前后端分离
- 逻辑上拆模块，部署上单体运行

## 2. 成功标准

MVP 完成后，应满足以下标准：

1. 能导入并解析 `.repo` 文件中的主要 Job、Transformation、Step 关系。
2. 能扫描 Java 源码目录并识别主要静态 SQL 的读写表。
3. 能连接 MySQL 获取表和字段元数据，并用于表名归一化与页面展示。
4. 能围绕任意一张表展示其直接上游表与直接下游表。
5. 能展示与该表相关的 Kettle Job、Transformation、Step 和 Java 模块。
6. 能执行基础影响分析，即从某张表出发查看其影响到的表、作业和模块。

MVP 不要求：

- 字段级血缘
- 实时采集
- 调度联动
- 权限体系
- 多环境对比
- 对复杂动态 SQL 的完整还原

## 3. 总体方案

采用“插件式多解析器 + 统一图模型”的架构方向，但以 MVP 的节奏推进。

整体思路如下：

1. 分别从 `.repo`、Java 源码目录和 MySQL 提取原始事实。
2. 将这些事实统一映射到同一套血缘图模型。
3. 将图模型持久化到关系库存储中。
4. 通过 API 提供查询能力。
5. 通过轻量前端页面完成搜索、血缘查看和影响分析。

部署形态采用“单体部署、模块可拆”：

- 代码结构拆分为多个独立模块
- 运行时先作为一个 Python 后端服务启动
- 后续如解析量、并发或团队协作需要，再把解析器拆为独立 worker 或服务

## 4. 模块边界

### 4.1 Repo 解析器

职责：

- 解析融合后的 `.repo` 文件
- 提取 Job、Transformation、Step 的结构关系
- 提取 Job 调用 Job、Job 调用 Transformation 的关系
- 识别和数据库交互的关键 Step
- 提取 SQL 类 Step 中涉及的表

MVP 重点覆盖：

- Job 与 Transformation 的调用关系
- Step 的主要顺序和依赖关系
- 常见数据库输入输出类 Step
- SQL 脚本类 Step 中直接出现的表名

MVP 暂不重点覆盖：

- 自定义插件 Step
- 依赖复杂运行时变量才能解析出的表名
- 字段级映射关系

### 4.2 Java 解析器

职责：

- 扫描 Java 源码目录
- 提取类或文件级别的 SQL 归属
- 识别 Java 模块与 MySQL 表之间的读写关系

MVP 重点覆盖：

- JDBC 模板
- MyBatis 显式 SQL
- JPA 原生 SQL
- 硬编码 SQL 字符串
- 可以还原的字符串拼接 SQL

MVP 暂不重点覆盖：

- 高度动态化的 SQL 拼接
- ORM 自动生成 SQL 的完整还原
- 方法级、参数级和字段级链路

### 4.3 元数据加载器

职责：

- 连接 MySQL
- 拉取数据库、表、字段、视图等元数据
- 为解析结果做表名归一化和校验
- 为前端展示提供基础信息

MVP 重点读取：

- 库表清单
- 字段清单
- 视图定义（可选）
- 表注释和字段注释

### 4.4 统一血缘图模型

职责：

- 将 Kettle、Java、MySQL 三类来源统一成节点和边
- 区分“原始事实”和“推导结果”
- 支撑前端查询和影响分析

这是整个 MVP 的核心抽象层。

## 5. 图模型设计

### 5.1 节点类型

- `DataSource`
  - 表示一个逻辑数据源
  - 用于区分不同 MySQL 连接或实例

- `Table`
  - 表示数据库表
  - 唯一标识建议采用 `instance.database.table`

- `KettleJob`
  - 表示 Kettle Job

- `KettleTransformation`
  - 表示 Kettle Transformation

- `KettleStep`
  - 表示 Transformation 内部的具体 Step

- `JavaModule`
  - 表示 Java 模块
  - MVP 先按类名、文件路径或 mapper 文件归属建模

### 5.2 边类型

- `CONTAINS`
  - `KettleJob -> KettleTransformation`
  - `KettleTransformation -> KettleStep`

- `CALLS`
  - `KettleJob -> KettleJob`
  - `KettleJob -> KettleTransformation`

- `READS`
  - `KettleStep -> Table`
  - `JavaModule -> Table`

- `WRITES`
  - `KettleStep -> Table`
  - `JavaModule -> Table`

- `FLOWS_TO`
  - `Table -> Table`
  - 表示推导出的表级血缘边

### 5.3 事实边与推导边

必须将“事实边”和“推导边”分开存储：

- 事实边：
  - `CALLS`
  - `READS`
  - `WRITES`
  - `CONTAINS`

- 推导边：
  - `FLOWS_TO`

原因如下：

1. 方便调试错误来源。
2. 方便后续优化推导规则而不破坏原始采集结果。
3. 方便将来增加字段级血缘时复用底层事实。

## 6. 血缘推导规则

MVP 仅生成表级血缘。

推导规则建议如下：

1. 如果某个 Kettle Step 读取表 A 并写入表 B，则生成 `A -> B` 的 `FLOWS_TO`。
2. 如果同一条 Transformation 链路中存在多个 Step，且前序 Step 读取表 A、后序 Step 写入表 B，则在可确认链路连通时生成 `A -> B`。
3. 如果某个 Java 模块读取表 A 并写入表 B，则生成 `A -> B`。
4. 如果某张表被 Kettle 写入、又被 Java 模块读取，则保留事实边，不强行推导跨技术边界的二次业务语义，只在查询时展示关联对象。

MVP 阶段不做复杂语义推理，例如：

- 多分支汇聚后的字段传播
- 临时表生命周期分析
- 动态变量替换后的跨库跨表推理

## 7. 技术选型

### 7.1 后端

- `FastAPI`
  - 提供 REST API
  - 适合任务触发、查询接口和后续扩展

- `SQLAlchemy`
  - 管理持久化模型

- `SQLite`
  - 作为 MVP 的默认存储
  - 优点是部署简单、无额外依赖
  - 模型设计时保留切换 PostgreSQL 的空间

- `sqlglot` 或同类 SQL 解析库
  - 用于提取 SQL 中出现的表

- Python XML 解析能力
  - 用于读取 `.repo` 结构

### 7.2 前端

- React
  - 实现轻量查询页面

- 轻量图展示库
  - 用于展示表上下游关系
  - 只需支持小规模关系浏览

## 8. 存储设计

MVP 存储建议使用关系型结构，而不是一开始引入图数据库。

核心原因：

1. MVP 更轻，部署成本低。
2. 节点和边结构可以自然映射到关系表。
3. 表级上下游和影响分析在 MVP 阶段可通过递归查询或后端遍历实现。
4. 后续若确有需要，可迁移到图数据库或双写。

建议最小表结构包括：

- `scan_runs`
  - 记录每次扫描任务

- `nodes`
  - 存储节点
  - 字段包括：`id`、`type`、`key`、`name`、`payload`

- `edges`
  - 存储边
  - 字段包括：`id`、`type`、`src_node_id`、`dst_node_id`、`is_derived`、`payload`

- `artifacts`
  - 记录解析来源，如 repo 文件、Java 文件、数据源信息

## 9. API 设计

MVP 建议提供以下接口：

- `POST /api/scan`
  - 触发一次全量扫描

- `GET /api/scan/{scan_id}`
  - 查看扫描状态和统计信息

- `GET /api/tables/search?q=`
  - 按表名模糊搜索

- `GET /api/tables/{table_id}/lineage`
  - 返回该表的直接上游表、直接下游表、相关 Kettle 对象、相关 Java 模块

- `GET /api/tables/{table_id}/impact`
  - 返回从该表出发的影响范围
  - MVP 支持 1 到 3 跳

- `GET /api/jobs/{job_id}`
  - 返回 Job 的详情和关联对象

- `GET /api/java-modules/{module_id}`
  - 返回 Java 模块详情和关联表

## 10. 前端页面设计

MVP 页面只做三类核心视图。

### 10.1 搜索页

功能：

- 输入表名关键字
- 返回匹配表列表
- 展示库名、表名、注释等基础信息

### 10.2 表详情页

功能：

- 展示表基础信息
- 展示直接上游表
- 展示直接下游表
- 展示相关 Kettle Job、Transformation、Step
- 展示相关 Java 模块

### 10.3 影响分析页

功能：

- 从某张表出发
- 展示向外扩散的影响对象
- 支持限制跳数

## 11. 非功能性要求

MVP 阶段的非功能要求如下：

1. 解析过程允许全量扫描，不要求实时增量。
2. 分析结果允许按扫描批次重建。
3. 页面优先保证信息清晰，不追求复杂交互。
4. 系统出现解析失败时，应保留错误信息和未识别对象，以便后续修正规则。

## 12. 风险与边界

### 12.1 主要风险

1. `.repo` 的内部结构复杂度可能高于预期，导致部分 Step 难以统一解析。
2. Java 代码中的动态 SQL 可能导致表识别率不足。
3. 不同数据源配置下的表名归一化可能出现误合并。
4. 若 Kettle 链路中依赖大量变量替换，表级推导准确率会下降。

### 12.2 缓解策略

1. 优先覆盖主干 Step 类型和主干 SQL 场景。
2. 统一保留原始解析片段，便于人工核查。
3. 引入 `DataSource` 维度，避免同名表误合并。
4. 将无法确定的关系标记为“未归一化”或“低置信度”，避免错误推导污染主图。

## 13. 演进路径

MVP 之后的自然演进方向如下：

1. 增加字段级血缘
2. 增加复杂动态 SQL 的还原能力
3. 增加更多 Kettle Step 类型支持
4. 引入增量扫描与变更比较
5. 评估是否迁移到 PostgreSQL 或图数据库
6. 接入调度平台、存储过程、视图展开等更多来源

## 14. 最终结论

本项目的 MVP 推荐方案为：

- 技术路线选择“插件式多解析器 + 统一图模型”
- 实现栈选择 Python 后端 + 前后端分离
- 部署方式选择单体部署、模块可拆
- 输入选择 `.repo` + Java 源码目录 + MySQL 元数据
- 输出选择轻量 Web 页面
- 能力边界聚焦于表级血缘和基础影响分析

第一阶段的核心工作不是追求全覆盖，而是先建立一条可验证、可扩展、可调试的主路径：

`Repo 解析 -> Java 解析 -> MySQL 元数据归一化 -> 统一图模型 -> 表级血缘推导 -> Web 查询展示`

只要这条主路径跑通，并能稳定支持搜索、上下游查看和影响分析，这个 MVP 就达到了预期目标。
