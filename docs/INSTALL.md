# 安装与部署指南

## 环境要求

- Python >= 3.12
- [UV](https://docs.astral.sh/uv/) 包管理器

## 安装步骤

### 1. 克隆项目

```bash
git clone <repo-url>
cd DailyWall
```

### 2. 初始化 UV 虚拟环境并安装依赖

```bash
uv sync --dev
```

### 3. 配置环境变量（可选）

复制示例配置并按需修改：

```bash
cp .env.example .env
```

主要配置项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MARKETS` | `["zh-CN","en-US","en-GB","en-IN","en-CA","ja-JP","de-DE","fr-FR","it-IT","es-ES","pt-BR"]` | 采集地区编码（JSON 数组格式，11 个经验证的完整本地化市场） |
| `PROXY_URL` | _(空)_ | HTTP 代理地址，用于突破 Bing IP 地理限制获取多语言元数据 |
| `THUMBNAIL_WIDTH` | `200` | 缩略图宽度（像素） |
| `PREVIEW_MAX_WIDTH` | `1920` | 预览图最大宽度（像素） |
| `API_HOST` | `0.0.0.0` | API 监听地址 |
| `API_PORT` | `8000` | API 监听端口 |

### 4. 启动 API 服务

```bash
uv run python -m app.main
```

或使用 uvicorn：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务启动后访问 API 文档：
- Swagger UI：`http://localhost:8000/docs`（如通过反向代理访问遇到 iframe 限制，请使用 ReDoc）
- ReDoc：`http://localhost:8000/redoc`

### 5. 首次采集：拉取历史数据

首次运行时，爬虫会自动拉取 Bing 最近 8 天的壁纸数据（同时完成数据库初始化）：

```bash
uv run python scripts/crawl.py
```

### 6. 配置定时采集

```bash
crontab -e
```

添加每日凌晨 2 点采集任务和备份（需替换为实际路径）：

```cron
0 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/crawl.py >> logs/cron.log 2>&1
30 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/backup.py >> logs/backup.log 2>&1
```

## 停止服务

如果使用 uvicorn 前台运行，直接 `Ctrl+C` 停止。

后台运行时：

```bash
# 查找进程
ps aux | grep uvicorn
# 终止进程
kill <PID>
```
