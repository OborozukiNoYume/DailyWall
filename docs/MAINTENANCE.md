# 运维手册

## 备份策略

### 自动备份

```bash
# 添加到 crontab，每日采集后执行（如凌晨 2:30）
30 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/backup.py >> logs/backup.log 2>&1
```

备份文件存储在 `data/backups/` 目录，自动保留最近 30 天。

### 手动备份

```bash
uv run python scripts/backup.py
```

### 恢复

```bash
# 1. 停止 API 服务
kill <PID>

# 2. 恢复数据库文件
cp data/backups/dailywall_YYYYMMDD_HHMMSS.db data/dailywall.db

# 3. 启动 API 服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. 执行文件系统一致性巡检
uv run python scripts/check.py weekly
```

## 巡检

巡检脚本为 `scripts/check.py`（注意：不与 Python 标准库 `inspect` 模块冲突）。

### 日常巡检（每日低峰）

检查所有图片文件存在性、大小 > 0、可被 Pillow 打开：

```bash
uv run python scripts/check.py daily
```

### 周级巡检

日常巡检 + 原图 SHA256 深度校验：

```bash
uv run python scripts/check.py weekly
```

### 状态查看

查看采集运行记录和各地区采集状态：

```bash
uv run python scripts/check.py status
```

输出示例：

```
Resources: 19
Metadata entries: 89

Last 1 crawl runs:
  2026-04-18 success success=89 fail=0

Crawl states:
  zh-CN: last_success=2026-04-18 failures=0
  en-US: last_success=2026-04-18 failures=0
  en-GB: last_success=2026-04-18 failures=0
  en-IN: last_success=2026-04-18 failures=0
  en-CA: last_success=2026-04-18 failures=0
  ja-JP: last_success=2026-04-18 failures=0
  de-DE: last_success=2026-04-18 failures=0
  fr-FR: last_success=2026-04-18 failures=0
  it-IT: last_success=2026-04-18 failures=0
  es-ES: last_success=2026-04-18 failures=0
  pt-BR: last_success=2026-04-18 failures=0
```

## 日志管理

### 日志目录

```
logs/
├── crawl.log          # 采集日志（自动轮转，10MB × 5 个备份）
├── cron.log           # Cron 执行日志
└── backup.log         # 备份日志
```

### API 访问日志

由 uvicorn 自动输出到标准输出/日志。

## 软删除与文件清理

### 软删除规则

API 查询自动过滤 `is_deleted=0` 的记录。设置 `is_deleted=1` 后记录对 API 不可见，但本地文件保留。

### 物理清理

仅通过巡检/维护脚本执行。清理前校验文件是否仍被 `metadata(is_deleted=0)` 引用。

```sql
-- 查询无引用的资源
SELECT r.sha256, r.base_path
FROM resources r
LEFT JOIN metadata m ON r.sha256 = m.sha256 AND m.is_deleted = 0
WHERE r.is_deleted = 1 AND m.sha256 IS NULL;
```

## 常见问题

### 数据库锁定

- API 使用只读连接（`mode=ro`），爬虫使用读写连接
- `busy_timeout=3000ms` 自动等待
- 避免手动操作数据库时运行爬虫

### 磁盘空间不足

- 检查 `wallpaper/` 目录大小
- 运行 `scripts/check.py status` 查看资源总数
- 清理软删除资源的物理文件

### 采集失败

- 检查 `crawl_runs` 表最近记录的 `message` 字段
- 检查网络连接
- 检查 `crawl_state` 表 `consecutive_failures` 字段
- 手动执行 `uv run python scripts/crawl.py` 观察日志输出

### Swagger UI 无法加载

通过反向代理或非 localhost 访问 `/docs` 时，浏览器可能因 iframe 安全策略阻止加载。改用 `/redoc` 即可。

### 首次运行采集脚本报 "no such table"

采集脚本已内置 `init_db()` 调用，会自动创建数据库和表。如仍报错，检查 `data/` 目录权限。
