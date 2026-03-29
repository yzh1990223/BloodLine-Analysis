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

## 启用方式

### 1. 安装本地 hooks

确保本机已安装 `lefthook` 后，在仓库根目录执行：

```bash
bash scripts/hooks/install-hooks.sh
```

### 2. 验证本地工具链

建议先保证以下命令在本机可运行：

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm test
cd frontend && npm run build
```

### 3. 日常提交流程

推荐顺序：

1. 先手动跑测试和构建
2. 再 `git add` 明确文件列表
3. 再 `git commit`
4. 最后 `git push`

## 第二轮增强内容

相比第一版骨架，当前第二轮增强补充了：

- `install-hooks.sh`
  - 用于安装 `lefthook`
- README 中的治理体系说明
- 本地 hooks 的启用与使用说明
- 更完整的日常提交流程建议
- `commit-workflow.md`
  - 用于说明仓库里的轻量提交分组和 hooks 处理方式
- `ai-hook-integration.md`
  - 用于说明 AI 会话 hooks 当前如何接入
- `tests/governance_smoke.sh`
  - 用于做治理文件与关键脚本的最小 smoke 校验

## 后续建议

下一轮如继续增强，可考虑：

- 在 CI 中补专项脚本校验
- 给 `pre-commit` 增加更细的文档路径映射
- 引入格式化工具后再接入自动格式化
- 结合你的 AI 客户端，把 `scripts/hooks/ai-session/` 真正接到事件钩子上
