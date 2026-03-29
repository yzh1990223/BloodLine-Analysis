# 任务闭环与 Roadmap 治理基础

本文件定义 BloodLine Analysis 在 GitHub 上的任务闭环体系，用于把当前仓库里的设计文档、实施计划、提交、经验沉淀和阶段演进统一串起来。

目标不是再引入一套平行流程，而是补上当前治理体系里相对薄弱的“任务执行层”：

- 设计文档回答“为什么做、做到哪里”
- GitHub Issues / Project 回答“当前做到哪一步”
- Milestones / Roadmap 回答“阶段如何推进、项目如何演进”
- 经验沉淀闭环回答“做完之后学到了什么、回灌了什么”

## 一、闭环主线

推荐主线如下：

`Spec / Plan -> Epic Issue -> Sub-issues -> GitHub Project 状态流转 -> PR / commit 关联 -> 经验沉淀 -> Milestone 收口 -> Roadmap 留痕`

这条主线里：

- `docs/superpowers/specs/`
  - 定义需求背景、范围、约束与方案
- `docs/superpowers/plans/`
  - 定义实施拆解和阶段顺序
- `GitHub Issues`
  - 承接实际执行任务
- `GitHub Project`
  - 承接状态、优先级、阻塞和时间线
- `docs/experience/`
  - 承接关键问题、设计取舍和治理经验

## 二、任务层级

推荐使用三层任务模型：

1. `Epic`
   - 对应一个较大能力、一个阶段目标或一轮治理升级
   - 必须关联 spec / plan
2. `Task`
   - Epic 下的可执行子任务
   - 以单一职责为主，尽量能独立完成和验证
3. `Bug / Governance / Docs / Experience Follow-up`
   - 非功能型或补偿型任务
   - 同样进入 Project，避免游离在体系外

推荐原则：

- 每个 Epic 对应 1 份主要计划
- 每个 Task 都应能明确判断完成与否
- 经验沉淀不是游离动作，必要时可以形成单独的 follow-up 任务

## 三、GitHub Project 建议模型

推荐使用一个统一 Project 承接当前仓库执行态，并至少包含以下字段：

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

推荐至少配置 4 个视图：

1. `Task Board`
   - 按 `Status` 看当前流转状态
2. `Task Table`
   - 按字段查看、筛选和排序
3. `Roadmap`
   - 按时间线查看 Epic 和关键任务
4. `Blocked`
   - 聚焦阻塞项

## 四、Milestone 与 Roadmap

Milestone 用来定义阶段锚点，例如：

- `MVP1.2`
- `MVP2.0`
- `Governance-Next`

Roadmap 用来展示：

- 每个 Epic 属于哪个阶段
- 当前阶段有哪些关键任务
- 每个阶段完成后，项目是如何推进到下一阶段的

推荐做法：

- Epic 必须归属 Milestone
- Task 尽量继承或同属对应 Milestone
- Roadmap 视图优先展示 Epic 和关键任务，不必把所有细碎任务都摊到时间线

## 五、与当前仓库治理的接入方式

这套任务闭环体系应接入当前治理，而不是独立存在。

### 1. 接入 `AGENTS.md`

项目规则层只需要声明：

- 较大功能或治理升级应有 Epic / 任务闭环承接
- spec / plan 完成后，应尽量映射到 GitHub Issues / Project
- 阶段演进应通过 Milestone / Roadmap 留痕

### 2. 接入治理文档

当以下内容发生明显变化时，应同步检查本文件：

- 任务流转规则
- Issue / Project 使用规范
- Milestone / Roadmap 约定
- 阶段管理方式

### 3. 接入经验沉淀闭环

若在任务执行过程中出现：

- bug 或误判
- 重要设计取舍
- 治理失效
- UAT 关键反馈

则应继续按 `docs/experience/` 的规则沉淀经验；必要时形成单独的 follow-up 任务，并纳入下一阶段 Milestone 或 Roadmap。

## 六、当前阶段的建议落地顺序

建议按以下顺序落地：

1. 建立 1 个统一 GitHub Project
2. 配置 `Status / Type / Priority / Area / Start date / Target date / Iteration`
3. 配置 `Board / Table / Roadmap / Blocked` 视图
4. 从当前阶段开始，为较大主题建立 Epic
5. 将现有 spec / plan 映射到 Epic 与 sub-issues
6. 用 Milestone 收口阶段
7. 用阶段总结和经验闭环记录演进痕迹

## 七、边界说明

本文件定义的是“任务执行与阶段演进”的治理基础，不负责替代：

- `superpowers`
  - 仍负责工作方法和执行节奏
- `AGENTS.md`
  - 仍负责仓库事实和项目规则
- hooks / CI
  - 仍负责自动化门禁

也就是说：

- 本文件定义“任务怎么串起来”
- `superpowers` 定义“工作怎么推进”
- hooks / CI 定义“规则怎么兜底”
