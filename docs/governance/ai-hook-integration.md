# AI Hooks 接入说明

`scripts/hooks/ai-session/` 下的脚本当前不是自动生效的运行时插件，而是为不同 AI 客户端准备的可接入骨架。

这层的目标是：

- 把常见提醒沉淀为脚本
- 避免规则只存在于人脑中
- 让不同客户端后续都能复用同一套仓库约束

## 当前有哪些脚本

- `lang-guard.sh`
  - 语言约束提醒
- `post-edit-reminder.sh`
  - 编辑后规则提醒
- `stop-review-reminder.sh`
  - 收尾自审提醒
- `dangerous-command-guard.sh`
  - 危险命令提醒

## 当前状态

当前状态是：

- 已有脚本骨架
- 已可单独执行
- 还没有和某个特定 AI 客户端强绑定

这意味着它们更像“仓库级规则脚本”，而不是已经自动运行的黑盒插件。

## 推荐接入方式

### 1. 先用 `AGENTS.md` 提供高优先级规则

这是最基础的一层。AI 即使没有真正挂载这些脚本，也能先从：

- `AGENTS.md`
- `backend/AGENTS.md`
- `frontend/AGENTS.md`

读取仓库事实和硬规则。

### 2. 再把会话脚本挂到具体客户端事件

不同客户端做法不同，但思路一致：

- 用户发消息前：
  - 可触发 `lang-guard.sh`
- 编辑后：
  - 可触发 `post-edit-reminder.sh`
- 执行危险命令前：
  - 可触发 `dangerous-command-guard.sh`
- 本轮准备结束时：
  - 可触发 `stop-review-reminder.sh`

## 推荐接入顺序

1. `lang-guard.sh`
2. `dangerous-command-guard.sh`
3. `post-edit-reminder.sh`
4. `stop-review-reminder.sh`

这样可以先把“语言”和“危险操作”这两类最稳定的规则接起来。

## 设计原则

接入时建议遵守这些原则：

- 只做提醒、守卫和提示
- 不做黑盒业务代码改写
- 不复制 `superpowers` 的方法论
- 不和 Git hooks 重复做同一件事

正确分工应该是：

- `AGENTS.md`
  - 定义仓库事实和规则
- AI hooks
  - 在会话过程中提醒和守卫
- Git hooks / CI
  - 在入库前后做门禁
- `superpowers`
  - 负责工作方法与执行流程

## 什么时候值得真正接入

当你满足下面任一条件时，就值得把这层真正接入某个客户端：

- 已经长期固定使用某个 AI 编码客户端
- 团队里多人在同一仓库中复用 AI 工作流
- 你希望把危险命令守卫和会话提醒做成自动化动作

在那之前，保留脚本骨架 + 明确接入说明，已经是一个很好的治理起点。
