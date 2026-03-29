# AI hooks 不应重复 superpowers

## 1. 类型

governance

## 2. 背景

在设计四层治理架构时，AI hooks 与 `superpowers` 工作流都在影响 AI 的行为，容易让人感觉两者重复。

## 3. 现象

如果不明确边界，AI hooks 很容易被误设计成：

- 第二套 workflow
- 第二套设计 / 调试 / 验证规则

## 4. 根因

两者都服务于“AI 怎么工作”，但服务层级不同：

- `superpowers` 管方法
- AI hooks 管事件提醒和守卫

## 5. 影响

如果边界不清：

- 文档会重复
- 规则会打架
- AI 读取上下文成本会上升

## 6. 处理

在治理文档里明确定位：

- `AGENTS.md`：仓库事实与规则
- `superpowers`：工作方法
- AI hooks：事件辅助层
- Git hooks / CI：门禁

## 7. 可复用结论

- AI hooks 最适合做提醒、轻守卫、风险预警
- 不适合承担完整 workflow 决策
- 不应替代 `superpowers`

## 8. 回灌动作

- 文档：已回灌到 `superpowers-collaboration-principles.md`、`ai-hook-integration.md`、治理相关总结文档
- 测试：不适合写成行为测试
- hooks / CI：不直接进入门禁
- AGENTS：通过入口级说明提醒，不把方法论全文塞入 AGENTS
- backlog：后续如接入固定客户端，应继续坚持此边界
