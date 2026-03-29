# BloodLine Analysis 治理基线

当前仓库采用一套轻量但可执行的治理体系，目标是降低以下风险：

- 巨型提交难 review
- 文档与实现漂移
- 模型、迁移、设计文档不一致
- 前后端接口路径漂移
- 未验证代码被直接推送

## 分层

1. `AGENTS.md`
   - 定义项目规则与真实边界
2. Git hooks
   - 本地 commit / push 门禁
3. AI 会话 hooks
   - 过程提醒与危险命令守卫
4. GitHub Actions
   - 远端最终兜底

## 当前策略

- `pre-commit`
  - 轻检查
- `pre-push`
  - 重验证
- 文档不同步默认先提醒，不一开始就全量阻断

