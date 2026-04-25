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

如果部署环境位于中国大陆，或需要稳定访问国际 Bing 市场，建议在 `.env` 中设置代理，例如：

```env
PROXY_URL=http://127.0.0.1:7890
```

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

脚本会自动创建运行所需目录，无需手动创建 `data/`、`wallpaper/` 或 `logs/`。

推荐顺序：

```bash
uv sync --dev
cp .env.example .env
uv run python scripts/crawl.py
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://127.0.0.1:8000/api/health
```

健康检查返回 `code=200`、`data.status=healthy` 且 `data.db_ok=true` 时，表示 API 已正常连接本地数据库。

如果希望使用 `systemd` 常驻管理 API，可安装项目自带单元文件：

```bash
sudo install -D -m 0644 deploy/systemd/dailywall-api.service /etc/systemd/system/dailywall-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now dailywall-api.service
systemctl status dailywall-api.service --no-pager
curl http://127.0.0.1:8000/api/health
```

补充说明：

- `dailywall-api.service` 默认以 `ops` 用户运行，工作目录固定为项目根目录。
- 启动命令使用项目虚拟环境中的 `python -m app.main`，会读取项目根目录下的 `.env`，并沿用 `API_HOST`、`API_PORT` 等配置。
- API 正式日志会写入 `logs/api.log`，同时标准输出仍会进入 `journald`，可通过 `journalctl -u dailywall-api.service -n 50 --no-pager` 查看。
- 所有模块的错误日志还会额外汇总到 `logs/error.log`，便于集中排查失败任务。
- 若 `.venv` 尚未创建或依赖未安装，服务会启动失败；先执行 `uv sync --dev`。

### 6. 配置定时采集

推荐使用项目自带的 `systemd timer` 管理定时采集：

```bash
sudo install -D -m 0644 deploy/systemd/dailywall-crawl.service /etc/systemd/system/dailywall-crawl.service
sudo install -D -m 0644 deploy/systemd/dailywall-crawl.timer /etc/systemd/system/dailywall-crawl.timer
sudo systemctl daemon-reload
sudo systemctl enable --now dailywall-crawl.timer
systemctl list-timers dailywall-crawl.timer
```

默认计划时间按 11 个 Bing 市场的公开接口更新时间推算，并在对应时间后 10 分钟触发：

```text
00:10, 02:40, 06:10, 07:10, 11:10, 12:10, 15:10, 23:10
```

当前 `scripts/crawl.py` 每次会遍历全部 `MARKETS`，重复数据依靠数据库唯一约束和 SHA256 去重跳过。

如果更倾向使用 `cron`，也可以手动配置：

```bash
crontab -e
```

添加定时采集任务和备份（需替换为实际路径）。下例使用每天本地时间 `00:10` 抓取一次：

```cron
10 0 * * * cd /path/to/DailyWall || exit 1; echo "[$(date --iso-8601=seconds)] cron crawl start" >> logs/cron.log 2>&1; .venv/bin/python scripts/crawl.py >> logs/cron.log 2>&1; code=$?; echo "[$(date --iso-8601=seconds)] cron crawl exit=$code" >> logs/cron.log 2>&1; exit $code
30 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/backup.py >/dev/null 2>&1
```

补充说明：

- `cron` 按机器本地时区执行，不会自动换算北京时间或 UTC。部署后建议先运行 `timedatectl` 或 `date -Iseconds` 确认时区。
- 不要同时启用 `cron` 和 `systemd timer` 的同类抓取任务，避免重复调度干扰日志判断。
- 抓取脚本的正式业务日志写入 `logs/crawl.log`，`cron.log` 只作为调度层辅助日志。
- 备份和巡检脚本的正式日志写入 `logs/maintenance.log`；上面的备份 `cron` 示例采用静默重定向，避免重复生成额外日志文件。
- 抓取脚本退出码约定：
  - `0`：完全成功
  - `2`：部分成功
  - `1`：失败或未成功执行
- 验证定时任务是否成功时，建议同时检查：
  - `logs/crawl.log` 中存在 `Crawl finished: status=success ...`
  - `logs/cron.log` 末尾存在 `cron crawl exit=0`

## 停止服务

如果使用 uvicorn 前台运行，直接 `Ctrl+C` 停止。

后台运行时：

```bash
# 查找进程
ps aux | grep uvicorn
# 终止进程
kill <PID>
```

如果使用 `systemd` 管理 API：

```bash
sudo systemctl stop dailywall-api.service
sudo systemctl disable dailywall-api.service
```
