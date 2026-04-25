# 数据库结构与文件存储规范

## 数据库表结构

SQLite 数据库文件位于 `data/dailywall.db`，启用 WAL 模式。

### 数据库连接策略

| 角色 | 连接方式 | 用途 |
|------|----------|------|
| API 服务 | 只读连接 `?mode=ro`，单例引擎 + `NullPool` | 查询壁纸数据 |
| 爬虫/脚本 | 读写连接，每次新建引擎 | 采集写入、巡检 |

PRAGMA 设置：`journal_mode=WAL`、`busy_timeout=3000`、`foreign_keys=ON`、`synchronous=NORMAL`

补充说明：

- API 侧保留单例 SQLAlchemy engine，但不复用线程绑定 SQLite 连接
- API engine 使用 `NullPool`，每次会话按需建立只读连接，避免并发线程数升高时出现已关闭连接被复用的问题

### resources（资源主表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `sha256` | TEXT(64) | PRIMARY KEY | 文件 SHA256 哈希值，同时作为 API 返回的 id |
| `year` | INTEGER | NOT NULL | 归档年份 |
| `month` | INTEGER | NOT NULL | 归档月份 |
| `base_path` | TEXT | NOT NULL | 基础存储路径（不含后缀和扩展名） |
| `ext` | TEXT | NOT NULL | 文件后缀（如 jpg） |
| `mime_type` | TEXT | NOT NULL | MIME 类型（如 image/jpeg） |
| `width` | INTEGER | NOT NULL | 原图宽度 |
| `height` | INTEGER | NOT NULL | 原图高度 |
| `bytes` | INTEGER | NOT NULL | 文件大小（字节） |
| `is_deleted` | INTEGER | NOT NULL DEFAULT 0 | 软删除标记 |

### metadata（地区元数据表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `mkt` | TEXT | PRIMARY KEY | 地区编码（如 en-US） |
| `date` | TEXT | PRIMARY KEY | 发布日期（YYYY-MM-DD） |
| `sha256` | TEXT(64) | FK → resources(sha256) | 关联的资源 SHA256 |
| `hsh` | TEXT | NOT NULL | Bing 原生去重标识 |
| `title` | TEXT | | 壁纸标题 |
| `copyright` | TEXT | | 版权信息 |
| `copyrightlink` | TEXT | | Bing 版权跳转链接 |
| `is_deleted` | INTEGER | NOT NULL DEFAULT 0 | 软删除标记 |

**唯一约束**：`UNIQUE(mkt, date)` — 同地区同日期仅一张壁纸。

**多市场关系说明**：同一张壁纸图片（同一 `sha256`）可能被多个市场的 metadata 引用，但不同市场在同一天也可能展示完全不同的图片（不同 `sha256`）。在当前实现里，`resources` 与 `metadata` 的关系是“一对多”：一条 `resources` 记录可对应多条 `metadata`，每条 `metadata` 只指向一条 `resources` 记录。

### crawl_runs（采集运行记录表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| `run_date` | TEXT | NOT NULL, INDEXED | 运行日期 |
| `started_at` | TEXT | NOT NULL | 开始时间（ISO 8601） |
| `finished_at` | TEXT | | 结束时间 |
| `status` | TEXT | NOT NULL | 状态：success/partial/fail |
| `success_count` | INTEGER | DEFAULT 0 | 成功数量 |
| `fail_count` | INTEGER | DEFAULT 0 | 失败数量 |
| `message` | TEXT | | 异常信息 |

### crawl_state（采集状态表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `mkt` | TEXT | PRIMARY KEY | 地区编码 |
| `last_success_date` | TEXT | | 最后成功采集日期 |
| `last_attempt_at` | TEXT | | 最后尝试采集时间 |
| `consecutive_failures` | INTEGER | DEFAULT 0 | 连续失败次数（上限 10） |

## 索引

- `metadata` 表：`(mkt, date, hsh)` 联合索引、`date` 单独索引
- `crawl_runs` 表：`run_date` 索引

## 文件存储目录规范

```
wallpaper/
├── 2026/
│   └── 04/
│       ├── {sha256}.jpg                    # 原图（UHD 4K）
│       ├── {sha256}_thumbnail.jpg          # 缩略图（200px 宽，JPEG 质量 85）
│       └── {sha256}_preview.jpg            # 预览图（≤1920px 宽，JPEG 质量 90）
```

## 日志目录规范

项目运行时会自动创建 `logs/` 目录，当前约定如下：

```text
logs/
├── api.log            # API 服务日志
├── crawl.log          # 采集业务日志
├── maintenance.log    # 备份/巡检脚本日志
├── error.log          # 所有 ERROR 级别日志汇总
├── cron.log           # Cron 调度辅助日志
└── systemd-crawl.log  # systemd 抓取测试辅助日志
```

补充说明：

- `api.log`、`crawl.log`、`maintenance.log` 是正式业务日志
- `error.log` 只额外汇总错误，不包含全部普通日志
- `cron.log`、`systemd-crawl.log` 用于确认任务是否被触发、退出码是多少，不替代业务日志

## 路径拼接规则

`resources.base_path` 存储格式：`wallpaper/YYYY/MM/{sha256}`（不含后缀）

| 尺寸 | 路径拼接规则 | 示例 |
|------|-------------|------|
| 原图 | `{base_path}.{ext}` | `wallpaper/2026/04/08b003...e5478e.jpg` |
| 缩略图 | `{base_path}_thumbnail.jpg` | `wallpaper/2026/04/08b003...e5478e_thumbnail.jpg` |
| 预览图 | `{base_path}_preview.jpg` | `wallpaper/2026/04/08b003...e5478e_preview.jpg` |

缩略图和预览图始终保存为 JPEG 格式。原图文件权限设为 `0o444`（只读）。
