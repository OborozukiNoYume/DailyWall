# 运维手册

## 备份策略

### 自动备份

```bash
# 添加到 crontab，每日采集后执行（如凌晨 2:30）
30 2 * * * cd /path/to/DailyWall && .venv/bin/python scripts/backup.py >/dev/null 2>&1
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

输出示例（当前已接入统一日志，实际输出会包含时间、级别和 logger 名称）：

```text
2026-04-25 16:30:00,000 [INFO] dailywall.maintenance.scripts.check: Resources: 19
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: Metadata entries: 89
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: Last 1 crawl runs:
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: 2026-04-18 success success=89 fail=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: Crawl states:
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: zh-CN: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: en-US: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: en-GB: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: en-IN: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: en-CA: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: ja-JP: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: de-DE: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: fr-FR: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: it-IT: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: es-ES: last_success=2026-04-18 failures=0
2026-04-25 16:30:00,001 [INFO] dailywall.maintenance.scripts.check: pt-BR: last_success=2026-04-18 failures=0
```

## 日志管理

### 日志目录

```
logs/
├── api.log            # API 服务日志（自动轮转，10MB × 5 个备份）
├── crawl.log          # 采集业务日志（自动轮转，10MB × 5 个备份）
├── maintenance.log    # 备份/巡检脚本日志（自动轮转，10MB × 5 个备份）
├── error.log          # 所有 ERROR 级别日志汇总
├── cron.log           # Cron 调度辅助日志
└── systemd-crawl.log  # systemd 调度辅助日志
```

### Cron 抓取成功判定

推荐使用带开始标记和退出码的 `crontab` 写法：

```cron
33 0 * * * cd /path/to/DailyWall || exit 1; echo "[$(date --iso-8601=seconds)] cron crawl start" >> logs/cron.log 2>&1; .venv/bin/python scripts/crawl.py >> logs/cron.log 2>&1; code=$?; echo "[$(date --iso-8601=seconds)] cron crawl exit=$code" >> logs/cron.log 2>&1; exit $code
```

判断某次定时抓取是否成功时，建议检查 `logs/cron.log` 是否同时满足：

- 出现 `cron crawl start`
- 对应时间段的 `logs/crawl.log` 中出现 `Crawl finished: status=success ...`
- 出现 `cron crawl exit=0`

退出码含义：

- `0`：完全成功
- `2`：部分成功
- `1`：失败、跳过或脚本未成功执行

如果只看到 `cron crawl start`，但没有对应的 `cron crawl exit=...`，通常表示任务异常中断，应继续检查同一时间段内的报错日志。

### 业务日志与调度日志的关系

- `crawl.log`、`api.log`、`maintenance.log` 是正式业务日志，优先用于排查功能问题。
- `cron.log`、`systemd-crawl.log` 是调度层辅助日志，主要记录任务是否被触发、退出码是多少。
- `error.log` 会额外汇总所有模块的错误日志，适合先快速定位失败事件，再回到对应模块日志查看上下文。

### systemd 定时抓取

项目提供了定时抓取用单元文件：

- `deploy/systemd/dailywall-api.service`
- `deploy/systemd/dailywall-crawl.service`
- `deploy/systemd/dailywall-crawl.timer`

配套执行脚本：

- `scripts/run_crawl_job.sh`
- `scripts/systemd_menu.sh`：中文交互式 systemd 分组管理菜单

默认计划时间：

- 每天 `00:10`，对应 `zh-CN` 推算更新时间后 10 分钟
- 每天 `02:40`，对应 `en-IN` 推算更新时间后 10 分钟
- 每天 `06:10`，对应 `de-DE`、`fr-FR`、`it-IT`、`es-ES` 推算更新时间后 10 分钟
- 每天 `07:10`，对应 `en-GB` 推算更新时间后 10 分钟
- 每天 `11:10`，对应 `pt-BR` 推算更新时间后 10 分钟
- 每天 `12:10`，对应 `en-CA` 推算更新时间后 10 分钟
- 每天 `15:10`，对应 `en-US` 推算更新时间后 10 分钟
- 每天 `23:10`，对应 `ja-JP` 推算更新时间后 10 分钟

当前 `scripts/crawl.py` 每次运行都会遍历全部 `MARKETS`。多个触发点用于贴近各地区更新时间，已存在的元数据和文件会被去重逻辑跳过。

安装并启动示例：

```bash
sudo install -D -m 0644 deploy/systemd/dailywall-crawl.service /etc/systemd/system/dailywall-crawl.service
sudo install -D -m 0644 deploy/systemd/dailywall-crawl.timer /etc/systemd/system/dailywall-crawl.timer
sudo systemctl daemon-reload
sudo systemctl enable --now dailywall-crawl.timer
```

也可以使用交互式分组菜单执行安装、开机自启、启动停止、状态查看、日志查看、健康检查和手动触发一次爬取：

```bash
./scripts/systemd_menu.sh
```

建议在启用 `systemd timer` 前停用同类 `cron` 抓取任务，避免重复执行影响测试结论。

调度日志写入：

- `logs/systemd-crawl.log`

状态检查示例：

```bash
systemctl status dailywall-api.service
systemctl list-timers dailywall-crawl.timer
systemctl status dailywall-crawl.timer
journalctl -u dailywall-crawl.service -n 50 --no-pager
tail -n 50 logs/systemd-crawl.log
```

### API 访问日志

如果使用前台方式启动，API 日志会同时写入 `logs/api.log` 并输出到终端。

如果使用 `systemd` 管理 API，推荐命令：

```bash
sudo install -D -m 0644 deploy/systemd/dailywall-api.service /etc/systemd/system/dailywall-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now dailywall-api.service
systemctl status dailywall-api.service --no-pager
journalctl -u dailywall-api.service -n 50 --no-pager
curl http://127.0.0.1:8000/api/health
```

定位 API 问题时，建议优先查看：

- `logs/api.log`
- `logs/error.log`
- `journalctl -u dailywall-api.service -n 50 --no-pager`

健康检查返回 `code=200`、`data.status=healthy` 且 `data.db_ok=true` 时，可视为 API 服务和数据库连接正常。

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
- API 读库 engine 使用 `NullPool`，避免并发请求下复用被关闭的 SQLite 线程连接
- `busy_timeout=3000ms` 自动等待
- 避免手动操作数据库时运行爬虫

### API 并发访问后异常退出

如果前台 `uvicorn` 日志中出现类似报错：

```text
sqlite3.ProgrammingError: Cannot operate on a closed database.
```

优先检查：

- 当前代码是否仍使用 API 只读 engine + `NullPool`
- 是否误改为 `SingletonThreadPool`、线程绑定连接复用，或其他会跨线程保留 SQLite 连接的实现
- 是否在高并发压测或图片 `Range` 请求期间出现 `500` 后进程退出

当前项目的预期实现是：

- API：只读连接 `mode=ro` + `NullPool`
- 爬虫/脚本：独立读写 engine

### 磁盘空间不足

- 检查 `wallpaper/` 目录大小
- 运行 `scripts/check.py status` 查看资源总数
- 清理软删除资源的物理文件

### 采集失败

- 检查 `crawl_runs` 表最近记录的 `message` 字段
- 检查 `logs/cron.log` 是否为 `cron crawl exit=2` 或 `cron crawl exit=1`
- 检查网络连接
- 检查 `crawl_state` 表 `consecutive_failures` 字段
- 手动执行 `uv run python scripts/crawl.py` 观察日志输出

### Swagger UI 无法加载

通过反向代理或非 localhost 访问 `/docs` 时，浏览器可能因 iframe 安全策略阻止加载。改用 `/redoc` 即可。

### 首次运行采集脚本报 "no such table"

采集脚本已内置 `init_db()` 调用，会自动创建数据库和表。如仍报错，检查 `data/` 目录权限。
