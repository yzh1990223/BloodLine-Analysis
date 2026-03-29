# 与 Superpowers 协同原则

## 目的

本文档用于固定 BloodLine Analysis 的仓库治理体系与 `superpowers` 的协同边界，确保：

- 项目规则不会削弱 `superpowers` 的方法能力
- `superpowers` 不会绕开仓库真实约束
- 文档、hooks、CI 与 AI 工作流保持一致

## 一句话原则

`AGENTS.md` 负责定义仓库事实与仓库规则，`superpowers` 负责定义工作方法，hooks 与 CI 负责把规则变成可验证的门禁。

## 角色分工

### 1. `AGENTS.md`

`AGENTS.md` 只负责回答下面这些问题：

- 这个仓库当前真实支持什么
- 当前明确不支持什么
- 标准开发命令是什么
- 修改哪些区域必须联动哪些文档
- 哪些提交或操作方式被禁止

它不负责定义完整开发方法论。

### 2. `superpowers`

`superpowers` 负责回答下面这些问题：

- 新功能应该先设计还是先实现
- bug 应该怎么系统化排查
- 什么时候必须先验证再声称完成
- 多步骤任务如何拆计划和执行

它不负责替代仓库特有规则。

### 3. Git hooks

Git hooks 只负责客观、可自动判断的检查，例如：

- 提交信息格式
- 提交粒度
- 是否误提交 `.db` / `.env`
- 是否遗漏基础测试或构建

Git hooks 不负责做主观设计判断。

### 4. GitHub Actions

GitHub Actions 负责远端兜底，原则上应与本地 `pre-push` 核心检查保持一致。

## 协同规则

### 规则 1：仓库规则优先于通用习惯

如果 `AGENTS.md` 和通用工作习惯冲突，以 `AGENTS.md` 为准。

例如：

- 仓库明确定义 `mysql_dsn` 仍是预留字段
- 那么 AI 不应把它描述成已接入能力

### 规则 2：`AGENTS.md` 不重复 `superpowers`

为了避免冲突，`AGENTS.md` 不应重复写：

- brainstorming 流程
- debugging 流程
- verification 方法
- 通用代码评审方法

这些内容交给 `superpowers`。

### 规则 3：hooks 只兜底，不取代思考

hooks 的目标是防止明显错误，不是替代分析与设计。

例如：

- `pre-push` 可以要求跑测试
- 但不应该试图判断“方案是否优雅”

### 规则 4：CI 与本地门禁保持同向

本地门禁与远端 CI 不应定义两套互相冲突的标准。

当前推荐关系：

- 本地 `pre-commit`：轻检查
- 本地 `pre-push`：重检查
- GitHub Actions：远端兜底

### 规则 5：AI 会话 hooks 只做提醒与守卫

AI 会话 hooks 适合做：

- 语言提醒
- 危险命令提醒
- 文档同步提醒
- 结束前自审提醒

不适合做：

- 自动修改业务代码
- 自动决定设计方案
- 自动跳过验证

## BloodLine Analysis 当前实践

当前仓库已经按以下方式协同：

- 根 `AGENTS.md`
  - 定义项目边界、验证命令、文档联动和禁止事项
- `backend/AGENTS.md` / `frontend/AGENTS.md`
  - 定义局部规则
- `scripts/hooks/`
  - 定义 commit / push 门禁与专项守卫
- `.github/workflows/ci.yml`
  - 运行后端测试、前端测试和前端构建

## 后续优化方向

后续如果继续增强，推荐顺序为：

1. 保持 `AGENTS.md` 简短且事实化
2. 把更多提醒型规则放到 hooks，而不是堆进 `AGENTS.md`
3. 让 AI 会话 hooks 真正接入常用客户端
4. 避免在多个地方重复定义同一条规则

## 判断标准

如果未来新增一条治理规则，优先问这 3 个问题：

1. 这是仓库事实，还是工作方法？
2. 这是提醒，还是必须门禁？
3. 这条规则应放在 `AGENTS.md`、hooks、还是 CI？

只要这 3 个问题能答清楚，这套四层治理就不会和 `superpowers` 打架。

