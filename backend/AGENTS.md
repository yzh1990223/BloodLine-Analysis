# Backend AGENTS

## 后端命令

- `uv sync --project . --extra dev`
- `PYTHONPATH=src .venv/bin/pytest -q`

## 后端规则

- 修改 `models.py` 后，必须检查迁移与设计文档
- 修改 `routes_*.py`、`schemas.py`、`lineage_query.py` 后，必须检查：
  - 前端 API 调用
  - README 与 UAT 文档
- 当前数据库为 SQLite，表结构文档在设计文档中维护
- `mysql_dsn` 当前仍是预留字段，不要把它描述成已生效能力
- 本文件只补充后端局部规则；通用仓库规则以根 `AGENTS.md` 为准
