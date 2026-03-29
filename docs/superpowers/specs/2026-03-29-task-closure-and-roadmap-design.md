# 任务闭环与 GitHub Project / Roadmap 设计

## 1. 目标

为 BloodLine Analysis 增加一套可执行的任务闭环体系，把当前仓库里已有的：

- spec
- plan
- hooks / CI
- 经验沉淀闭环
- 阶段总结

进一步串到 GitHub 的任务系统中，使项目可以直观呈现：

- 当前有哪些任务
- 任务处于什么状态
- 哪些任务属于哪个阶段
- 项目是如何沿 Roadmap 演进的

## 2. 设计原则

1. 不另起平行系统
   - 新体系必须接入现有文档与治理架构
2. Epic 承接计划，Task 承接执行
   - spec / plan 不直接替代任务单
3. Project 负责状态可视化
   - 任务状态应在 GitHub Project 中直观看到
4. Roadmap 负责演进留痕
   - 用 Milestone 和时间线展示阶段推进
5. 经验闭环继续保留
   - 任务完成后产生的经验应继续回灌

## 3. 核心模型

### 3.1 文档层

- `docs/superpowers/specs/`
  - 记录设计背景、范围、方案
- `docs/superpowers/plans/`
  - 记录实施拆解

### 3.2 任务层

- `Epic`
  - 对应一个较大功能或阶段主题
- `Task`
  - Epic 下的实际执行项
- `Bug / Governance / Docs / Experience`
  - 补偿型、治理型和文档型任务

### 3.3 可视化层

- `GitHub Project`
  - 展示状态、优先级、区域、日期和阻塞情况
- `Roadmap`
  - 展示 Epic / 关键任务的时间线
- `Milestone`
  - 展示阶段锚点与阶段收口

## 4. Project 字段建议

- `Status`
  - `Backlog`
  - `Planned`
  - `In Progress`
  - `Blocked`
  - `In Review`
  - `Done`
- `Type`
  - `Epic`
  - `Task`
  - `Bug`
  - `Governance`
  - `Docs`
  - `Experience`
- `Priority`
  - `P0`
  - `P1`
  - `P2`
  - `P3`
- `Area`
  - `Backend`
  - `Frontend`
  - `Lineage`
  - `Governance`
  - `Docs`
- `Start date`
- `Target date`
- `Iteration`

## 5. 视图建议

### 5.1 Task Board

按 `Status` 看任务流转。

### 5.2 Task Table

按字段查看、筛选和排序。

### 5.3 Roadmap

按时间线查看 Epic 和关键任务，展示阶段推进。

### 5.4 Blocked

只看阻塞项。

## 6. 闭环主线

推荐闭环：

`Spec / Plan -> Epic -> Sub-issues -> Project 状态变化 -> PR / commit 关联 -> 经验沉淀 -> Milestone 收口 -> Roadmap 留痕`

## 7. 与现有治理体系的关系

- `AGENTS.md`
  - 定义项目事实与规则
- `task-closure-and-roadmap-foundation.md`
  - 定义任务执行和阶段管理
- `superpowers`
  - 负责工作方法
- hooks / CI
  - 负责门禁
- `docs/experience/`
  - 负责执行后的经验回灌

## 8. 第一版范围

第一版只落地到文档层和治理入口层，不直接修改 GitHub 远端配置。

包括：

- 新增治理基础文档
- 更新 README 与 AGENTS 入口
- 把该体系纳入 governance smoke

不包括：

- 自动创建 Issues
- 自动同步 Project 字段
- 自动生成 Roadmap

## 9. 后续演进方向

- 增加 issue 模板
- 增加 Project 字段与使用规范草案
- 增加 Epic / Task / Bug 的协作约定
- 让阶段总结和 Milestone 更紧密联动
