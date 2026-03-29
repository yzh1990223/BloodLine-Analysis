# GitHub Project 需要显式建模层级与状态

## 1. 类型

governance

## 2. 背景

在为 `BloodLine Analysis` 启动 GitHub Project 任务闭环时，我们完成了 Project、字段、Milestone、Epic 和第一批 Task 的初始化，并开始把任务结构真正跑起来。

## 3. 现象

这次落地过程中暴露出 3 个典型问题：

- `Task Table` 默认看不出哪些 Task 属于哪个 Epic
- 已规划或已完成的事项，在 GitHub 内置 `Status` 上仍然显示为 `Todo`
- 自动化浏览器无法复用人工浏览器的 GitHub 登录态，导致 Project 视图配置无法完全自动化

此外，最初给 `#4 epic: GitHub 任务闭环落地` 追加子任务时，REST 子任务接口还出现了 `Priority has already been taken` 这类不直观错误。

## 4. 根因

根因主要有 3 层：

- GitHub Project 的“层级关系”不是自动从命名或 Milestone 推导出来的，必须显式建立 `parent / sub-issue`
- GitHub 内置 `Status` 只有 `Todo / In Progress / Done` 三档，无法直接表达我们设计里的 `Planned / Blocked / In Review`
- 自动化环境与人工浏览器会话隔离，浏览器自动化不能默认继承人工登录态

REST 子任务接口的优先级冲突，则说明 GitHub 在这块 API 上的约束并不透明，不能假设 REST 接口一定比 GraphQL 稳定。

## 5. 影响

如果不把这些问题显式处理掉：

- Task Table 和 Board 会缺少结构感，用户看不出任务树
- 团队会误以为状态系统设计有问题，实际上是“内置状态”和“自定义流程状态”混在了一起
- 自动化落地 GitHub Project 时，会高估浏览器自动化能覆盖的范围

进一步说，这会削弱任务闭环体系的可读性和可维护性。

## 6. 处理

这次处理方式是：

- 用 GitHub 原生子任务能力把 Task 显式挂到 Epic 下
- 对需要细化的流程状态，继续使用自定义字段 `Workflow`
- 对需要“一眼看懂”的状态，同时维护内置 `Status`
- 遇到 REST 子任务接口异常时，改用 GraphQL `addSubIssue`
- 明确接受一个现实边界：Project 视图配置更适合由已登录的人工浏览器完成

## 7. 可复用结论

- GitHub Project 里的层级关系必须显式建模，不能只靠命名规则或 Milestone
- 如果需要超过 3 档的任务流转状态，应采用“内置 `Status` + 自定义 `Workflow`”双层模型
- 自动化创建 Project、字段、Issue 没问题，但视图配置要预期可能需要人工补齐
- GitHub API 出现行为不透明时，GraphQL 往往比 REST 更适合处理结构化对象关系

## 8. 回灌动作

- 文档：应继续在 `task-closure-and-roadmap-foundation.md` 和 `github-issue-and-project-playbook.md` 中强调“父子关系显式建立”和“双层状态模型”
- 测试：当前不适合做仓库内自动化测试，但可在治理经验中保留这条实践
- hooks / CI：暂不进入门禁，避免把 GitHub 远端操作绑定到本地验证
- AGENTS：无需写进 `AGENTS.md` 正文，只需保留 GitHub Project 使用入口
- backlog：后续可考虑补一份“Project 初始化检查清单”，明确哪些步骤可自动化、哪些步骤需手动完成
