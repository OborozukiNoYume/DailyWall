# 采集流程文档

## 概述

爬虫通过 Bing HPImageArchive.aspx API 获取每日壁纸元数据，下载 UHD 原图，预生成缩略图和预览图，并写入 SQLite 数据库。

**重要**：Bing API 根据 IP 地理位置决定返回语言，中国服务器无法通过 `mkt` 参数获取其他语言的标题和版权信息。因此，当服务器位于中国大陆时，**必须配置 `PROXY_URL`** 以获取各市场的本地化文案。不同市场的每日壁纸也可能不同（不仅仅是文案翻译差异）。

## 采集策略

### 地区

支持多地区配置，通过 `MARKETS` 环境变量指定（JSON 数组格式），默认：`["zh-CN","en-US","en-GB","en-IN","en-CA","ja-JP","de-DE","fr-FR","it-IT","es-ES","pt-BR"]`。

每个地区独立调用 Bing API，获取该地区专属的标题、版权信息和版权跳转链接。不同地区在同一天的壁纸可能不同（独立的图片和文案），而非简单翻译。

**注意**：并非所有 Bing 市场都提供本地化标题。经测试，部分市场（如 ar-SA、ko-KR、ru-RU 等）仅返回标题"Info"而无本地化文案，且图片与其他"Rest of World"市场完全相同，无独特内容。已选定的 11 个市场均经过验证，确保提供完整的本地化标题和版权信息。

### 频率

- **日常采集**：可通过 `systemd timer` 或 `cron` 定时触发，最终都通过 `scripts/crawl.py` 执行
- **冷启动**：首次运行自动拉取最近 8 天数据（`idx=0, n=8`）
- **重复执行策略**：当前实现每次都会请求最近 8 天数据，再依靠 `(mkt, date)` 和 `SHA256` 双重去重避免重复入库；`crawl_state` 当前仅用于记录状态，不参与断点续采
- **默认 systemd 计划**：`deploy/systemd/dailywall-crawl.timer` 按各市场公开接口更新时间后 10 分钟设置多个触发点；每次触发仍会遍历全部 `MARKETS`

### 采集日志

- `scripts/crawl.py` 会自动初始化统一日志配置，正式业务日志写入 `logs/crawl.log`
- 采集过程按 `INFO / WARNING / ERROR` 分层：
  - `INFO`：开始、结束、去重命中、新增资源、汇总统计
  - `WARNING`：跳过、字段缺失、无法构造下载地址、重复任务
  - `ERROR`：请求失败、处理失败、运行异常
- 所有采集链路中的错误还会额外汇总到 `logs/error.log`
- 如果通过 `cron` 或 `systemd` 触发任务，`logs/cron.log`、`logs/systemd-crawl.log` 只用于记录调度开始和退出码，不替代 `crawl.log`

### 采集流程

1. 获取文件锁（`fcntl.flock`，非阻塞排他锁）
2. 初始化数据库（`init_db()`，幂等）
3. 依次处理每个地区：
   a. 调用 Bing API 获取最近 8 天壁纸元数据
   b. 对每张壁纸执行 `_process_image`
   c. 更新 `crawl_state` 表
4. 汇总结果写入 `crawl_runs` 表
5. 释放文件锁

### Bing API 参数

```
https://www.bing.com/HPImageArchive.aspx?format=js&uhd=1&idx={offset}&n={count}&mkt={market}
```

| 参数 | 说明 |
|------|------|
| `format=js` | JSON 格式响应 |
| `uhd=1` | 请求 UHD 分辨率 |
| `idx` | 日期偏移（0=今天，最大 7） |
| `n` | 获取数量（最大 8） |
| `mkt` | 地区编码 |

### 当前使用的响应字段

单条 `images[*]` 响应中，当前采集逻辑会读取以下字段：

| 字段 | 用途 |
|------|------|
| `startdate` | 转换为 `metadata.date` |
| `hsh` | 写入 `metadata.hsh` |
| `title` | 写入 `metadata.title` |
| `copyright` | 写入 `metadata.copyright` |
| `copyrightlink` | 写入 `metadata.copyrightlink` |
| `urlbase` | 拼接 UHD 原图下载地址 |

## 双重去重机制

### 一级去重（元数据级别）

查询 `metadata` 表，检查 `(mkt, date)` 是否已存在。存在则跳过下载，直接返回成功。

如果已存在记录缺少 `copyrightlink`，而本次 Bing 响应提供了该字段，则会补写 `metadata.copyrightlink` 后返回成功。

### 二级去重（文件级别）

下载图片到临时文件后计算 SHA256，查询 `resources` 表：
- **SHA256 已存在**：仅创建新的 `metadata` 记录指向已有资源（不同地区共享同一张图片）
- **SHA256 不存在**：执行完整的下载、预生成、入库流程

## 单张壁纸处理流程（`_process_image`）

```
获取元数据 → 一级去重(mkt+date) → 下载到临时文件 → 计算 SHA256
    ↓ 已存在                        ↓
    返回成功              二级去重(SHA256) → 新资源 → 下载预处理 → 入库
                              ↓ 已存在
                         仅新增 metadata → 返回成功
```

## 图片预生成

| 尺寸 | 宽度 | 高度 | 格式 | 质量 | 规则 |
|------|------|------|------|------|------|
| 缩略图 | 200px | 等比缩放 | JPEG | 85 | 固定宽度，不放大 |
| 预览图 | ≤1920px | 等比缩放 | JPEG | 90 | 最大宽度，不放大 |
| 原图 | 原始 | 原始 | 原始 | 原始 | 保留 UHD 画质，权限 0o444 |

## 容错机制

- **文件锁**：使用 `fcntl.flock(LOCK_EX|LOCK_NB)` 防止并发采集，获取锁失败时跳过本次运行
- **代理支持**：通过 `PROXY_URL` 环境变量配置 HTTP 代理，用于突破 Bing IP 地理限制获取多语言元数据。留空则直连。
- **HTTP 重试**：httpx HTTPTransport retries=3
- **请求超时**：元数据请求 30s，图片下载 60s
- **数据校验**：下载后 PIL verify 校验图片完整性，无效文件不入库
- **状态持久化**：`crawl_state` 表记录各地区采集状态，重启后不丢失
- **运行记录**：`crawl_runs` 表记录每次执行详情（成功/失败数量、异常信息）
- **连续失败计数**：`consecutive_failures` 上限 10，用于诊断长期失败地区

## 幂等性

整个采集流程设计为幂等的：
- 一级去重确保同地区同日期不会重复处理
- 一级去重允许在重复采集时补写缺失的 `copyrightlink`
- 二级去重确保相同文件不会重复存储
- `crawl.py` 启动时自动调用 `init_db()`，无需手动建表
- 允许重复执行，不会产生脏数据

## 手动执行

```bash
uv run python scripts/crawl.py
```

脚本会自动初始化数据库，并创建运行所需目录：

- `data/`
- `wallpaper/`
- `logs/`

如需通过代理抓取，在执行前确保 `.env` 中已设置 `PROXY_URL`，例如：

```env
PROXY_URL=http://127.0.0.1:7890
```

手动采集完成后，可启动 API 并检查运行状态：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://127.0.0.1:8000/api/health
```

健康检查返回 `code=200`、`data.status=healthy` 且 `data.db_ok=true` 时，表示 API 已成功连接本地数据库。

如需确认本次采集是否成功，建议至少检查：

- `logs/crawl.log` 中存在 `Crawl finished: status=success ...`
- 若为定时任务，还应确认 `logs/cron.log` 或 `logs/systemd-crawl.log` 中存在对应的退出码记录
