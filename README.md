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
├── tests/
│   ├── conftest.py          # 测试 fixtures（内存 DB、TestClient）
│   ├── test_api.py          # API 端点测试
│   ├── test_services.py     # 服务层测试
│   ├── test_crawler.py      # 去重逻辑测试
│   └── test_image_utils.py  # 图片工具测试
├── docs/                    # 详细文档
├── pyproject.toml
└── .env.example
```

## API 概览

| 端点 | 说明 |
|------|------|
| `GET /api/filters` | 获取筛选选项（地区/年份/月份） |
| `GET /api/wallpapers` | 壁纸分页列表（支持筛选+关键词） |
| `GET /api/wallpapers/random` | 随机返回一张壁纸的可引用图片 URL |
| `GET /api/images/{id}?size=thumbnail\|preview` | 图片访问 |
| `GET /api/images/{id}/download` | 原图下载（UHD 4K） |
| `GET /api/health` | 服务健康检测 |

## 定时采集

```bash
crontab -e
# 每日凌晨 2 点采集
0 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/crawl.py >> logs/cron.log 2>&1
# 每日采集后备份
30 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/backup.py >> logs/backup.log 2>&1
```

## 文档

- [安装部署](docs/INSTALL.md)
- [数据库结构](docs/STRUCTURE.md)
- [采集流程](docs/CRAWL.md)
- [API 文档](docs/API.md)
- [运维手册](docs/MAINTENANCE.md)
- [错误记录](docs/ERROR_RECORD.md)

## License

MIT
