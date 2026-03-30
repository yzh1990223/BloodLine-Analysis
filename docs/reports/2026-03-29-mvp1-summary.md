# BloodLine Analysis MVP1 阶段总结

## 1. 阶段结论

截至 `MVP1.1`，BloodLine Analysis 已完成 `MVP1` 的核心目标，并达到可用于 UAT 和真实样本验证的状态。

当前系统已经具备：

- `.repo` 与 Java 源码的血缘解析能力
- 对象级 / 表级血缘图构建能力
- 详情查询、影响分析、闭环分析能力
- 基础可用的 Web 交互界面
- 部署、UAT 和设计文档支持

因此，本阶段可以认定为：

- `MVP1`：完成
- `MVP1.1`：完成并形成稳定增强版基线

## 1.1 阶段锚点

本阶段对应的治理锚点如下：

- Milestone：
  - `MVP1.2`
- 关键 Epic：
  - [#1 epic: 扫描任务与可观测性增强](https://github.com/yzh1990223/BloodLine-Analysis/issues/1)
  - [#10 epic: Java 代码解析增强](https://github.com/yzh1990223/BloodLine-Analysis/issues/10)
- 关键治理 Epic：
  - [#4 epic: GitHub 任务闭环落地](https://github.com/yzh1990223/BloodLine-Analysis/issues/4)

说明：

- `MVP1.1` 是能力基线的收口口径
- `MVP1.2` 是当前 GitHub Project 中承接后续增强与治理推进的阶段 Milestone

## 2. MVP1 已完成范围

### 2.1 后端能力

已完成：

- 解析 Kettle `.repo` 文件
- 解析 Java 源码中的静态 SQL
- 构建统一图模型
- 持久化 `scan_runs / nodes / edges`
- 生成 `FLOWS_TO` 推导边
- 查询直接上下游
- 查询最多 3 跳影响分析
- 查询 Job 与 Java 模块详情
- 计算多表闭环组

当前支持的主要 API：

- `POST /api/scan`
- `GET /api/scan-runs/latest`
- `GET /api/tables/search`
- `GET /api/tables/{table_key}/lineage`
- `GET /api/tables/{table_key}/impact`
- `GET /api/analysis/cycles`
- `GET /api/jobs`
- `GET /api/jobs/{job_key}`
- `GET /api/java-modules/{module_key}`

### 2.2 解析能力

当前已覆盖的重点场景：

- Repo 中的 Job / Transformation 调用关系
- 常见数据库输入输出步骤
- 部分 Job SQL
- Java 中静态 SQL 的读写关系

当前已支持的对象类型：

- `data_table`
- `source_table`
- `source_file`

### 2.3 前端能力

已完成页面：

- 首页
- 对象列表页
- 对象详情页
- 影响分析页
- 闭环分析页

已完成主要交互：

- 顶部导航与面包屑
- 首页扫描控制面板
- 首页对象概览统计卡
- 搜索与局部预览
- 详情页完整链路图
- 详情页关联对象点击高亮
- 影响分析跳数展示
- 闭环分析分组展示

### 2.4 工程与文档

已完成：

- SQLite 持久化与 Alembic 迁移
- 后端 pytest 测试
- 前端 Vitest 测试
- README
- 部署指南
- UAT 操作手册
- 设计文档与实施计划同步更新

## 3. 当前实现边界

当前真正作为输入参与解析的是：

- `.repo` 文件
- Java 源码目录

当前仍然只是预留、尚未真正接入的是：

- `mysql_dsn`
- MySQL 元数据读取
- 字段级血缘

当前运行方式：

- 扫描是同步执行
- 每次重新扫描都会先清空旧图，再全量重建
- 首页不再默认渲染全量大图，而是采用“概览 + 搜索 + 局部预览”的轻量结构

## 4. 当前已知限制

### 4.1 解析限制

- 复杂动态 SQL 覆盖有限
- 自定义 Kettle Step 覆盖有限
- 脚本类步骤覆盖有限
- 无法提供字段级映射

### 4.2 运行限制

- 扫描是同步任务，大输入下响应会变慢
- SQLite 适合 UAT 和轻量部署，不适合高并发正式场景
- 没有异步任务队列和更细粒度进度展示

### 4.3 分析限制

- 闭环分析当前按闭环组展示，不枚举所有具体环路
- 单表自环没有纳入闭环组页
- 详情图已经过裁剪，更强调可读性而非完整过程展开

## 5. 阶段价值

`MVP1` 的价值已经不只是“证明能做”，而是：

- 可以拿真实 `.repo` 和 Java 样本做 UAT
- 可以作为业务、数据、开发一起讨论血缘问题的可见基线
- 可以沉淀出异常链路、闭环、误判样本，为下一阶段增强提供真实输入

## 5.1 本阶段关键经验

本阶段已经沉淀或验证的代表性经验包括：

- [路径带空格导致扫描失败](/Users/nathan/Documents/GithubProjects/BloodLine%20Analysis/docs/experience/incidents/2026-03-29-path-with-space-breaks-scan.md)
- [首页全量总览图不适合大图场景](/Users/nathan/Documents/GithubProjects/BloodLine%20Analysis/docs/experience/implementation/2026-03-29-full-overview-graph-does-not-scale.md)
- [双前端 dev server 导致验证混乱](/Users/nathan/Documents/GithubProjects/BloodLine%20Analysis/docs/experience/operations/2026-03-29-dual-vite-dev-servers-cause-validation-confusion.md)
- [GitHub Project 需要显式建模层级与状态](/Users/nathan/Documents/GithubProjects/BloodLine%20Analysis/docs/experience/governance/2026-03-29-github-project-needs-explicit-hierarchy-and-status-model.md)

其中与阶段治理直接相关、已形成 follow-up 的经验有：

- [#11 docs: 补 Project 初始化检查清单](https://github.com/yzh1990223/BloodLine-Analysis/issues/11)

## 6. 推荐收口口径

对外可以这样描述当前阶段成果：

> BloodLine Analysis 已完成 `MVP1`，实现了基于 Kettle `.repo` 与 Java 源码的数据对象级 / 表级血缘分析，支持对象查询、完整链路查看、影响分析、闭环分析与手动重新扫描，当前版本可用于 UAT 和真实样本验证。

## 7. MVP2 建议方向

建议下一阶段按以下优先级推进。

### 7.1 优先级一：解析精度增强

- 接入 MySQL 元数据
- 提升真实 `.repo` 的 Step 覆盖率
- 提升复杂 SQL 解析准确率

### 7.2 优先级二：运行能力增强

- 扫描异步化
- 增加任务队列
- 增加更细粒度的扫描进度展示

### 7.3 优先级三：分析能力增强

- 展示闭环组内的具体环路
- 增加异常链路统计
- 提供更丰富的筛选和聚焦方式

### 7.4 优先级四：深度血缘增强

- 字段级血缘
- 存储过程 / 视图展开
- 多环境比较

## 8. 建议下一步

当前最合适的动作不是继续无边界加功能，而是：

1. 把 `MVP1.1` 作为稳定基线继续做 UAT
2. 收集真实样本中的误判、漏判、闭环异常案例
3. 基于这些真实案例定义 `MVP2` 的第一批需求

这样可以保证后续增强是“被真实问题驱动”的，而不是功能堆砌。

## 8.1 下一阶段承接关系

建议以下阶段关系保持显式引用：

- 当前阶段收口：
  - `MVP1.1`
- 当前执行 Milestone：
  - `MVP1.2`
- 下一阶段主 Milestone：
  - `MVP2.0`
  - `MVP2.1`
- 当前已进入下一阶段执行层的 Epic：
  - [#3 epic: MVP2 - MySQL 元数据接入](https://github.com/yzh1990223/BloodLine-Analysis/issues/3)
  - [#2 epic: MVP2 - 字段级血缘基础能力](https://github.com/yzh1990223/BloodLine-Analysis/issues/2)
