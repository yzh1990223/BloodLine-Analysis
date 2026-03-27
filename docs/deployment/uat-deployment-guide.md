# BloodLine Analysis UAT 部署指南

## 1. 适用范围

本指南适用于当前 BloodLine Analysis MVP 版本在 UAT 服务器上的部署。

当前版本能力边界：

- 支持解析 Kettle `.repo` 文件
- 支持解析 Java 源码目录中的静态 SQL
- 支持生成表级血缘关系与影响分析
- 支持 Web 页面查询、总览图、详情页、影响分析页

当前版本未包含：

- MySQL 元数据直连读取
- 字段级血缘
- 异步扫描任务队列
- 权限与多用户管理

因此，本次 UAT 的重点是验证：

- `.repo + Java` 的表级血缘是否正确
- 图形展示与查询页面是否满足使用预期

## 2. 推荐部署架构

建议采用单机两进程部署：

- 前端：React 构建后的静态文件，由 Nginx 托管
- 后端：FastAPI + Uvicorn
- 存储：SQLite
- 反向代理：Nginx

推荐访问路径：

- `/` -> 前端静态页面
- `/api` -> 后端接口

## 3. 环境要求

建议服务器环境：

- Linux x86_64
- Python 3.12 及以上
- Node.js 18 及以上
- Nginx 1.20 及以上

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

如果仓库已存在，则更新：

```bash
cd /opt/bloodline-analysis
git pull origin main
```

## 5. 后端部署

### 5.1 安装依赖

项目后端当前使用 `uv` 管理 Python 环境，推荐按以下方式安装：

```bash
cd /opt/bloodline-analysis/backend
uv sync --project . --extra dev
```

### 5.2 初始化数据库

当前默认使用本地 SQLite：

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

### 5.4 systemd 部署方式

创建文件：

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

启用并启动：

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

构建产物输出目录：

```bash
/opt/bloodline-analysis/frontend/dist
```

## 7. Nginx 配置

创建配置文件：

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

校验并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 8. UAT 数据准备

当前版本不读取 MySQL 元数据，因此 UAT 需要准备以下输入：

- 一份 `.repo` 文件
- 一份 Java 源码目录

建议将 UAT 数据统一放在服务器固定目录下，例如：

```bash
/data/bloodline-uat/repo/merged.repo
/data/bloodline-uat/java-src/
```

要求：

- `bloodline-api` 运行用户对上述目录有读取权限
- 路径必须是服务器本机可访问路径

## 9. 触发扫描

后端启动后，调用扫描接口：

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "/data/bloodline-uat/repo/merged.repo",
    "java_source_root": "/data/bloodline-uat/java-src"
  }'
```

如果通过 Nginx 域名访问：

```bash
curl -X POST http://your-uat-domain/api/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "/data/bloodline-uat/repo/merged.repo",
    "java_source_root": "/data/bloodline-uat/java-src"
  }'
```

成功返回示例：

```json
{
  "scan_run_id": 1,
  "status": "completed",
  "inputs": {
    "repo_path": "/data/bloodline-uat/repo/merged.repo",
    "java_source_root": "/data/bloodline-uat/java-src"
  }
}
```

## 10. 健康检查与验证

### 10.1 接口检查

```bash
curl http://127.0.0.1:8000/api/tables/search
```

### 10.2 页面检查

打开：

```text
http://your-uat-domain/
```

检查内容：

- 首页能正常打开
- 顶部导航栏正常显示
- 总览图能加载
- 单击节点高亮直接上下游
- 双击节点进入详情页
- 详情页和影响分析页的面包屑、返回按钮正常

## 11. 发布与回滚建议

### 发布

```bash
cd /opt/bloodline-analysis
git pull origin main

cd backend
uv sync --project . --extra dev
.venv/bin/alembic upgrade head
sudo systemctl restart bloodline-api

cd ../frontend
npm install
npm run build
sudo systemctl reload nginx
```

### 回滚

```bash
cd /opt/bloodline-analysis
git checkout <旧版本commit>

cd backend
uv sync --project . --extra dev
sudo systemctl restart bloodline-api

cd ../frontend
npm run build
sudo systemctl reload nginx
```

## 12. 已知限制

- 当前版本的 `mysql_dsn` 参数尚未接入真实逻辑
- 目前血缘图只覆盖表级关系
- 扫描请求是同步执行，大文件场景下会占用请求时间
- SQLite 适合 UAT，不适合高并发正式环境

## 13. UAT 阶段建议

建议分三步进行：

1. 先用小规模样例数据验证部署链路
2. 再导入真实脱敏 `.repo + Java` 数据做业务验证
3. 记录误判和漏判案例，作为下一阶段增强输入

