# DailyWall

DailyWall 是一个 **Bing 多国壁纸本地归档 + 轻量化只读 API 服务**。

核心亮点：**突破 Bing 壁纸仅保留最近 8 天的时效限制**，把图片和元数据长期保存到本地，支持筛选、浏览、预览和下载。

## 项目介绍

这个项目适合想要长期保存 Bing 壁纸、按地区归档、或给前端/个人工具提供壁纸数据接口的用户。

- 抓取 Bing 多市场壁纸并本地归档
- 自动生成缩略图和预览图
- 提供统一格式的只读 API
- 使用 SQLite 和本地文件系统，部署简单

更详细的设计与使用说明请查看 [docs/](docs/)。

## 核心功能

- 多国市场采集：支持 `zh-CN`、`en-US`、`en-GB`、`ja-JP` 等多个 Bing 市场
- 本地长期归档：保存原图、缩略图、预览图及元数据
- 去重存储：同一张图片按 SHA256 去重，减少重复占用
- 只读 API：支持筛选、分页、随机返回、图片访问与下载
- 轻量部署：单机即可运行，无需额外数据库服务

## 技术栈

- **FastAPI**：API 服务框架
- **SQLite**：本地单文件数据库
- **SQLAlchemy**：数据模型与数据库访问
- **httpx**：Bing 数据抓取与图片下载
- **Pillow**：图片校验与缩略图生成
- **UV**：依赖与虚拟环境管理

## 快速开始

要求：

- Python `>= 3.12`
- 已安装 `uv`

30 秒跑起来：

```bash
uv sync --dev
cp .env.example .env
uv run python scripts/crawl.py
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后可访问：

- API 文档：`http://127.0.0.1:8000/redoc`
- 健康检查：`http://127.0.0.1:8000/api/health`

说明：

- 首次采集会自动初始化数据库和运行目录
- 如果部署环境位于中国大陆，通常需要在 `.env` 中配置 `PROXY_URL`
- 更完整的安装、配置与采集说明见 [docs/INSTALL.md](docs/INSTALL.md) 和 [docs/CRAWL.md](docs/CRAWL.md)

## API 概览

JSON 接口统一返回：

```json
{ "code": 200, "msg": "success", "data": {} }
```

主要端点：

| 端点 | 说明 |
|------|------|
| `GET /api/filters` | 获取筛选项 |
| `GET /api/wallpapers` | 壁纸列表、分页、筛选 |
| `GET /api/wallpapers/random` | 随机返回一张壁纸 |
| `GET /api/images/{id}` | 获取缩略图或预览图 |
| `GET /api/images/{id}/download` | 下载原图 |
| `GET /api/health` | 健康检查 |

完整接口说明见 [docs/API.md](docs/API.md)。

## 项目结构

```text
DailyWall/
├── app/          # FastAPI 应用、路由、服务、模型
├── crawler/      # Bing 抓取、下载、去重、入库
├── scripts/      # 采集、巡检、备份脚本
├── docs/         # 详细文档
├── tests/        # 自动化测试
├── .env.example  # 配置示例
└── pyproject.toml
```

模块和数据结构说明见：

- [docs/STRUCTURE.md](docs/STRUCTURE.md)
- [docs/CRAWL.md](docs/CRAWL.md)
- [docs/MAINTENANCE.md](docs/MAINTENANCE.md)

## 文档

- [安装部署](docs/INSTALL.md)
- [API 文档](docs/API.md)
- [数据库结构](docs/STRUCTURE.md)
- [采集流程](docs/CRAWL.md)
- [运维说明](docs/MAINTENANCE.md)
- [错误记录](docs/ERROR_RECORD.md)

## 许可证

[MIT](LICENSE)
