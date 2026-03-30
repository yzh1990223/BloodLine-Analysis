# GitHub Issue 与 Project 使用规范

本文件定义 BloodLine Analysis 当前推荐的 GitHub 任务执行规范，用于把 issue 模板、Project 字段、Milestone 与 Roadmap 统一起来。

## 一、目标

当前仓库已经有：

- `docs/superpowers/specs/`
- `docs/superpowers/plans/`
- `docs/experience/`
- `docs/governance/task-closure-and-roadmap-foundation.md`

本文件补的是“执行层”：

- 什么时候用哪类 issue
- 在 Project 里怎么填字段
- 状态如何流转
- Milestone 与 Roadmap 怎么用

## 二、Issue 类型

当前推荐使用 5 类模板：

1. `Epic`
   - 用于较大能力、阶段主题、治理升级
2. `Task`
   - 用于 Epic 下的单一职责任务
3. `Bug`
   - 用于异常、误判、回归和故障
4. `Governance`
   - 用于 hooks、CI、AGENTS、治理文档增强
5. `Experience Follow-up`
   - 用于把经验沉淀条目回灌成明确后续动作

## 三、Issue 选择原则

### 1. Epic

使用场景：

- 一份 spec / plan 要拆成一组子任务
- 一个阶段主题需要持续推进
- 一个治理主题会跨多个 commit 和多个子任务

要求：

- 必须关联 spec / plan
- 应进入 Milestone
- 应拆分子任务

### 2. Task

使用场景：

- 可独立完成和验证的工作项
- 可以明确判断完成标准的执行任务

要求：

- 尽量归属某个 Epic
- 需要写清验收标准

### 3. Bug

使用场景：

- 当前行为与预期不一致
- 存在回归、500、错误结果、展示异常

要求：

- 尽量给出复现路径
- 修复后应评估是否需要沉淀 incident 经验

### 4. Governance

使用场景：

- AGENTS、hooks、CI、治理文档、协作流程增强

要求：

- 明确这次增强解决什么风险
- 明确不会做什么，避免治理过重

### 5. Experience Follow-up

使用场景：

- 已经有经验条目，但还需要继续落地回灌

要求：

- 必须关联 `docs/experience/` 中的条目
- 必须写清回灌动作和完成标准

推荐在以下情况下建立：

- 当前提交只能记录经验，无法立刻完成回灌
- 回灌动作需要进入未来阶段或未来迭代
- 需要在 Project / Roadmap 中持续展示进度
- 需要明确指定“这条经验什么时候才算闭环完成”

当前仓库里的一个真实样例：

- `#11 docs: 补 Project 初始化检查清单`
  - 来自经验条目 `docs/experience/governance/2026-03-29-github-project-needs-explicit-hierarchy-and-status-model.md`

## 四、Project 字段填写建议

推荐至少使用以下字段：

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

填写原则：

- Epic 必须有 `Type=Epic`
- Task / Bug / Governance / Experience Follow-up 应使用最贴近的 `Type`
- `Area` 按主要负责区域填写，不必重复多选
- `Priority` 由影响和紧急程度决定，不由工作量大小决定

## 五、状态流转建议

推荐状态流转：

`Backlog -> Planned -> In Progress -> In Review -> Done`

若出现阻塞，则切到：

`Blocked`

### 1. Backlog

- 已记录
- 尚未排期

### 2. Planned

- 已纳入当前阶段或迭代
- 已明确大致目标

### 3. In Progress

- 已开始实际执行

### 4. In Review

- 实现基本完成
- 等待验证、收口或合并

### 5. Done

- 代码、文档、验证和必要的经验回灌已完成

### 6. Blocked

- 当前无法继续推进
- 必须写清阻塞原因

### 7. Experience Follow-up 的特殊完成标准

`Experience Follow-up` 不应只因为“经验文档已经写好”就视为完成。

它通常应满足：

- 经验条目已存在
- issue 中定义的回灌动作已落地
- 相关文档 / hooks / 测试 / backlog 已更新
- 若属于某个 Epic 或阶段，Project 状态已同步

## 六、Milestone 与 Roadmap 约定

- Epic 应优先进入 Milestone
- Task 若属于明显阶段，也应归属对应 Milestone
- Roadmap 视图优先展示 Epic 和关键 Task
- 不建议把所有零碎任务都放进 Roadmap

推荐阶段命名：

- `MVP1.2`
- `MVP2.0`
- `MVP2.1`
- `Governance-Next`

## 七、与仓库文档的关系

### 1. Spec / Plan

- Epic 必须尽量链接 spec / plan
- Task 应尽量链接父 Epic 或对应计划

### 2. Experience

- Bug 修复后，如结论具有复用价值，应沉淀到 `docs/experience/`
- Experience Follow-up issue 用于把经验继续回灌

推荐关系：

- 经验文档负责“记录和提炼”
- Experience Follow-up issue 负责“执行和跟踪”

### 3. 阶段总结

- Milestone 收口后，建议在阶段总结文档中反向引用：
  - 本阶段 Epic
  - 关键任务
  - 关键经验

推荐补充：

- 本阶段对应的 Milestone 名称
- 下一阶段建议承接的 Milestone / Epic
- 若某条经验形成了 `Experience Follow-up`，应一并引用对应 issue

## 八、当前不做的重方案

以下内容先列入后续 TODO，不在当前版本落地：

- label 体系的完整设计与初始化脚本
- Project 初始化清单脚本化
- Milestone 模板化
- 更完整的 Project 字段、视图和自动化配置包

这些内容已进入后续 TODO，等当前最小任务闭环跑通后再继续增强。
