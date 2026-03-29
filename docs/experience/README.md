# 经验沉淀闭环

`docs/experience/` 用于沉淀这个项目中的可复用经验。

第一版目标不是建立重型知识库，而是跑通这条主链路：

`经验出现 -> 记录 -> 分类 -> 提炼 -> 回灌 -> 后续复用`

## 适合沉淀的经验

以下内容都适合进入这里：

- bug / 故障 / 误判案例
- 实现与设计取舍
- UAT / 部署 / 运行问题
- 治理与 AI 协作经验

## 分类

当前使用 4 类：

- `incidents/`
  - 故障、bug、误判、异常链路
- `implementation/`
  - 设计取舍、实现经验、架构判断
- `operations/`
  - UAT、部署、运行、环境经验
- `governance/`
  - 文档、hooks、CI、AGENTS、AI 协作经验

## 推荐命名

统一使用：

```text
YYYY-MM-DD-<topic>.md
```

例如：

- `2026-03-29-path-with-space-breaks-scan.md`
- `2026-03-29-ai-hooks-should-not-duplicate-superpowers.md`

## 单条经验模板

每条经验至少包含：

1. 类型
2. 背景
3. 现象
4. 根因
5. 影响
6. 处理
7. 可复用结论
8. 回灌动作

其中最重要的是：

- `可复用结论`
- `回灌动作`

因为经验文档的真正目标不是“记录事件”，而是推动项目改变。

## 回灌目标

经验可以回灌到：

- 文档
- 测试
- hooks / CI
- `AGENTS.md`
- backlog / 下一阶段需求

第一版不要求所有经验都命中全部回灌目标，但至少要说明：

- 是否需要回灌
- 回灌到哪里
- 是否已经落地

## 辅助文件

- `indexes/experience-index.md`
  - 经验索引
- `digests/`
  - 阶段性经验归纳

## 与治理体系的关系

经验体系不是独立平行系统，而是当前治理体系的一部分：

- `docs/governance/experience-closure-foundation.md`
  - 说明经验闭环如何接入治理
- `AGENTS.md`
  - 给出项目级入口规则
- `tests/governance_smoke.sh`
  - 检查经验体系核心文档存在
- `scripts/hooks/post-commit`
  - 在特定提交后提醒是否值得沉淀经验

## 什么时候应新建经验条目

推荐在这些场景新建：

- 修掉一个真实 bug 后
- 发现一个反复出现的误判模式后
- 做出一个重要设计取舍后
- UAT 或部署中出现了值得复用的经验后
- 治理体系本身暴露出缺口后

如果一条经验最终既没有“可复用结论”，也没有“回灌动作”，那它通常还不够成熟，不必急着沉淀。
