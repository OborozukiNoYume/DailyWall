# DailyWall

Bing 多国壁纸本地归档 API 服务。

突破 Bing 壁纸 8 天时效限制，提供轻量化只读 API，支持筛选、浏览、预览、下载全场景。

## 技术栈

- **FastAPI** — API 服务框架
- **SQLite (WAL)** — 单文件本地存储
- **Pillow** — 图片预处理（缩略图/预览图）
- **httpx** — HTTP 客户端（采集与下载）
- **SQLAlchemy** — ORM 与数据库管理
- **UV** — 环境管理与依赖隔离

## 快速开始

```bash
# 安装依赖
uv sync --dev

# 配置环境变量
cp .env.example .env

# 按需设置代理，位于中国大陆或需要访问国际 Bing 市场时建议填写
# PROXY_URL=http://127.0.0.1:7890

# 首次采集（拉取最近 8 天壁纸，自动初始化数据库和运行目录）
uv run python scripts/crawl.py

# 启动 API 服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 健康检查
curl http://127.0.0.1:8000/api/health
```

API 文档：`http://localhost:8000/redoc`

免责声明：本项目仅作为 Bing 壁纸归档抓取只读 API 的工具。

说明：
- JSON 接口统一返回 `{ "code": 状态码, "msg": "说明", "data": ... }`
- 图片文件接口成功时仍直接返回文件流

如果希望由 `systemd` 常驻管理 API：

```bash
sudo install -D -m 0644 deploy/systemd/dailywall-api.service /etc/systemd/system/dailywall-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now dailywall-api.service
systemctl status dailywall-api.service --no-pager
curl http://127.0.0.1:8000/api/health
```

说明：

- API service 文件位于 `deploy/systemd/dailywall-api.service`
- 默认以 `ops` 用户运行，工作目录为项目根目录
- 启动命令使用项目虚拟环境中的 `python -m app.main`
- 运行日志可通过 `journalctl -u dailywall-api.service -n 50 --no-pager` 查看
- 停止或重启服务可使用 `sudo systemctl stop dailywall-api.service`、`sudo systemctl restart dailywall-api.service`

## 项目结构

```
DailyWall/
├── app/
│   ├── main.py              # FastAPI 入口，lifespan 管理
│   ├── config.py            # pydantic-settings 配置管理
│   ├── database.py          # SQLite 连接（API 只读 / 爬虫读写）
│   ├── models.py            # SQLAlchemy 模型（4 张表）
│   ├── schemas.py           # Pydantic 请求/响应模式
│   ├── api/
│   │   ├── router.py        # /api 路由聚合
│   │   ├── filters.py       # GET /api/filters
│   │   ├── wallpapers.py    # GET /api/wallpapers, GET /api/wallpapers/random
│   │   ├── images.py        # GET /api/images/{id}, GET /api/images/{id}/download
│   │   └── health.py        # GET /api/health
│   ├── services/
│   │   ├── wallpaper_service.py  # 壁纸查询、筛选、分页
│   │   ├── filter_service.py     # 筛选选项（24h 内存缓存）
│   │   ├── image_service.py      # 图片文件服务
│   │   └── health_service.py     # 健康检测
│   └── utils/
│       └── image_utils.py        # SHA256、校验、缩放
├── crawler/
│   ├── bing_fetcher.py      # Bing HPImageArchive API 客户端
│   ├── downloader.py        # 图片下载与预处理
│   └── crawler.py           # 采集编排器（双重去重、文件锁、状态追踪）
├── scripts/
│   ├── crawl.py             # Cron 采集入口（含日志轮转）
│   ├── backup.py            # SQLite 备份（30 天轮转）
│   └── check.py             # 巡检脚本（daily/weekly/status）
├── tests/                   # 自动化测试
├── docs/                    # 详细文档
├── pyproject.toml
└── .env.example
```

## 测试

运行完整自动化测试：

```bash
uv run pytest
```

当前测试目录：

```text
tests/
├── conftest.py           # 测试 fixtures（内存 DB、TestClient）
├── test_api.py           # API 端点测试
├── test_bing_fetcher.py  # Bing API 客户端与 URL 构造测试
├── test_crawler.py       # 采集编排、去重与状态更新测试
├── test_downloader.py    # 下载、落盘与图片预处理测试
├── test_image_service.py # 图片文件服务测试
├── test_image_utils.py   # 图片工具测试
├── test_responses.py     # 统一响应与参数错误格式测试
├── test_scripts.py       # 脚本入口与巡检/备份测试
└── test_services.py      # 服务层测试
```

说明：

- 测试依赖通过 `uv sync --dev` 安装。
- `pytest` 配置位于 `pyproject.toml`，默认会从 `tests/` 目录收集用例。
- README 和运维文档中提到的 `dailywall-crawl-test.service`、`dailywall-crawl-test.timer` 属于 `systemd` 定时任务验证单元，不属于 `pytest` 自动化测试套件。

## API 概览

JSON 接口统一返回 `{ "code": 状态码, "msg": "说明", "data": ... }`，业务数据位于 `data` 字段内。

| 端点 | 说明 |
|------|------|
| `GET /api/filters` | 获取筛选选项（地区/年份/月份） |
| `GET /api/wallpapers` | 壁纸分页列表（支持筛选+关键词） |
| `GET /api/wallpapers/random` | 随机返回一张壁纸的可引用图片 URL |
| `GET /api/images/{id}?size=thumbnail\|preview` | 图片访问 |
| `GET /api/images/{id}/download` | 原图下载（UHD 4K） |
| `GET /api/health` | 服务健康检测 |

## API 的 systemd 管理

```bash
# 启动并设为开机自启
sudo systemctl enable --now dailywall-api.service

# 查看状态
systemctl status dailywall-api.service --no-pager

# 查看最近日志
journalctl -u dailywall-api.service -n 50 --no-pager

# 重启服务
sudo systemctl restart dailywall-api.service

# 停止服务
sudo systemctl stop dailywall-api.service
```

健康检查返回 `code=200`、`data.status=healthy` 且 `data.db_ok=true` 时，表示 API 服务和数据库连接正常：

```bash
curl http://127.0.0.1:8000/api/health
```

## 定时采集

```bash
crontab -e
# 示例：每日 00:33 采集（按机器本地时区执行）
33 0 * * * cd /path/to/DailyWall || exit 1; echo "[$(date --iso-8601=seconds)] cron crawl start" >> logs/cron.log 2>&1; .venv/bin/python scripts/crawl.py >> logs/cron.log 2>&1; code=$?; echo "[$(date --iso-8601=seconds)] cron crawl exit=$code" >> logs/cron.log 2>&1; exit $code
# 每日采集后备份
30 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/backup.py >> logs/backup.log 2>&1
```

说明：`cron` 使用机器本地时区；可通过 `timedatectl` 或 `date -Iseconds` 确认当前时区。`logs/cron.log` 中若同时出现 `Crawl finished: status=success ...` 和 `cron crawl exit=0`，可视为该次定时抓取成功。

如果希望使用 `systemd` 管理采集任务，可安装项目自带的测试用单元文件：

```bash
sudo install -D -m 0644 deploy/systemd/dailywall-crawl-test.service /etc/systemd/system/dailywall-crawl-test.service
sudo install -D -m 0644 deploy/systemd/dailywall-crawl-test.timer /etc/systemd/system/dailywall-crawl-test.timer
sudo systemctl daemon-reload
sudo systemctl enable --now dailywall-crawl-test.timer
systemctl status dailywall-crawl-test.timer --no-pager
```

说明：

- 相关文件位于 `deploy/systemd/dailywall-crawl-test.service` 和 `deploy/systemd/dailywall-crawl-test.timer`
- 当前定时计划为每天 `00:33` 和 `11:11`
- 抓取任务由 `scripts/run_crawl_job.sh` 执行，日志写入 `logs/systemd-crawl.log`
- 可通过 `journalctl -u dailywall-crawl-test.service -n 50 --no-pager` 查看最近一次执行日志
- 建议启用 `systemd timer` 前停用同类 `cron` 抓取任务，避免重复执行

## 文档

- [安装部署](docs/INSTALL.md)
- [数据库结构](docs/STRUCTURE.md)
- [采集流程](docs/CRAWL.md)
- [API 文档](docs/API.md)
- [运维手册](docs/MAINTENANCE.md)
- [错误记录](docs/ERROR_RECORD.md)

## License

MIT
