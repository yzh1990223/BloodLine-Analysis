# BloodLine Analysis UAT 部署指南

## 1. 适用范围

本文档适用于 `MVP1.1` 版本的 BloodLine Analysis 在 UAT 环境中的部署与联调。

当前版本已经支持：

- 解析 Kettle `.repo` 文件
- 解析 Java 源码目录中的静态 SQL
- 支持最小 Java 方法调用图归并
- 支持一部分 MyBatis 场景：
  - 注解 SQL
  - 同 stem XML Mapper 的最小静态 SQL
- 生成对象级 / 表级血缘和最多 3 跳影响分析
- 区分 `data_table`、`source_table`、`source_file`
- 页面化触发扫描、对象浏览、详情查看和闭环分析

当前版本暂未支持：

- MySQL 元数据直连读取
- 字段级血缘
- 异步扫描任务队列
- 权限与多用户管理
- 高动态 MyBatis XML 与 ORM 自动生成 SQL 的完整还原

因此本轮 UAT 的重点仍然是：

- `.repo + Java` 输入能否稳定产出可用血缘
- 页面和查询流程是否满足测试使用
- 真实数据下是否存在异常闭环、自环或明显误连

## 2. 推荐部署架构

建议采用单机两进程部署：

- 前端：React 构建产物，由 Nginx 托管
- 后端：FastAPI + Uvicorn
- 存储：SQLite
- 反向代理：Nginx

推荐访问路径：

- `/` -> 前端静态站点
- `/api` -> 后端 API

## 3. 环境要求

- Linux x86_64
- Python 3.12 及以上
- Node.js 18 及以上
- Nginx 1.20 及以上
- `uv` 可用

推荐目录：

```bash
/opt/bloodline-analysis
/opt/bloodline-analysis/backend
/opt/bloodline-analysis/frontend
```

## 4. 代码部署

```bash
cd /opt
git clone <你的仓库地址> bloodline-analysis
cd /opt/bloodline-analysis
```

更新仓库：

```bash
cd /opt/bloodline-analysis
git pull origin main
```

## 5. 后端部署

### 5.1 安装依赖

```bash
cd /opt/bloodline-analysis/backend
uv sync --project . --extra dev
```

### 5.2 初始化数据库

```bash
cd /opt/bloodline-analysis/backend
.venv/bin/alembic upgrade head
```

### 5.3 手工启动后端

```bash
cd /opt/bloodline-analysis/backend
BLOODLINE_DATABASE_URL=sqlite+pysqlite:///./bloodline.db \
PYTHONPATH=src \
.venv/bin/uvicorn bloodline_api.main:app --host 127.0.0.1 --port 8000
```

说明：

- 当前扫描是同步执行
- 每次扫描都会先清空旧图，再全量重建
- `mysql_dsn` 当前不会真正参与元数据读取

### 5.4 systemd 部署方式

`/etc/systemd/system/bloodline-api.service`

```ini
[Unit]
Description=BloodLine API
After=network.target

[Service]
WorkingDirectory=/opt/bloodline-analysis/backend
Environment="BLOODLINE_DATABASE_URL=sqlite+pysqlite:///./bloodline.db"
Environment="PYTHONPATH=src"
ExecStart=/opt/bloodline-analysis/backend/.venv/bin/uvicorn bloodline_api.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bloodline-api
sudo systemctl status bloodline-api
```

查看日志：

```bash
sudo journalctl -u bloodline-api -f
```

## 6. 前端部署

### 6.1 安装依赖并构建

```bash
cd /opt/bloodline-analysis/frontend
npm install
npm run build
```

构建目录：

```bash
/opt/bloodline-analysis/frontend/dist
```

## 7. Nginx 配置

`/etc/nginx/conf.d/bloodline.conf`

```nginx
server {
    listen 80;
    server_name your-uat-domain;

    root /opt/bloodline-analysis/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri /index.html;
    }
}
```

重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 8. UAT 数据准备

当前版本只真正消费以下输入：

- `.repo` 文件
- Java 源码目录

建议放在服务器固定目录，例如：

```bash
/data/bloodline-uat/repo/merged.repo
/data/bloodline-uat/java-src/
```

要求：

- 运行后端的系统用户对上述路径有读取权限
- 路径必须是服务器本地路径
- `repo_path` 与 `java_source_root` 至少提供一个

## 9. 触发扫描

### 9.1 通过接口触发

同时传两类输入：

```bash
curl -X POST http://your-uat-domain/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "/data/bloodline-uat/repo/merged.repo",
    "java_source_root": "/data/bloodline-uat/java-src"
  }'
```

只传 `.repo`：

```bash
curl -X POST http://your-uat-domain/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "/data/bloodline-uat/repo/merged.repo"
  }'
```

成功返回示例：

```json
{
  "scan_run_id": 12,
  "status": "completed",
  "inputs": {
    "repo_path": "/data/bloodline-uat/repo/merged.repo"
  }
}
```

### 9.2 通过页面触发

首页有“扫描控制面板”，支持：

- 查看最近一次扫描状态
- 点击“重新扫描解析”
- 展开“高级配置”填写：
  - `Repo 文件路径`
  - `Java 源码目录`
  - `MySQL DSN（预留）`

注意：

- 两个输入路径至少填写一个
- 路径中如果包含空格，后端兼容 shell 风格的 `\ ` 转义

## 10. 健康检查

### 10.1 后端接口

```bash
curl http://127.0.0.1:8000/api/tables/search
curl http://127.0.0.1:8000/api/scan-runs/latest
curl http://127.0.0.1:8000/api/analysis/cycles
```

### 10.2 前端页面

确认以下路径可打开：

- `/`
- `/objects`
- `/analysis/cycles`

### 10.3 关键功能检查

- 首页扫描控制面板可加载
- 首页对象概览卡片有数据
- 点击对象概览卡片能进入对象列表
- 对象详情页能显示完整链路图
- 闭环分析页能显示闭环组列表

## 11. 常用接口清单

- `POST /api/scan`
- `GET /api/scan-runs/latest`
- `GET /api/tables/search?q=`
- `GET /api/tables/{table_key}/lineage`
- `GET /api/tables/{table_key}/impact`
- `GET /api/analysis/cycles`
- `GET /api/jobs`
- `GET /api/jobs/{job_key}`
- `GET /api/java-modules/{module_key}`

## 12. 问题排查建议

### 12.1 扫描按钮报错

优先检查：

- 后端进程是否仍在运行
- 输入路径是否为服务器本地真实路径
- 服务进程是否有读权限

### 12.2 页面数据和接口不一致

优先检查：

- 前端是否连到正确的后端地址
- 后端是否已重启到最新代码
- 最近一次扫描是否成功完成

### 12.3 闭环分析为空

优先检查：

- 本次扫描是否确实产出了 `FLOWS_TO` 边
- 数据中是否存在多表闭环
- 不要把单表自环误认为“闭环组”，当前闭环页只统计至少 2 张表参与的闭环

## 13. 上线前提示

当前版本适合 UAT 和小范围业务验证，不建议直接作为生产高并发服务使用。主要原因：

- SQLite 仅适合轻量单机场景
- 扫描为同步执行
- MySQL 元数据和字段级血缘尚未接入
