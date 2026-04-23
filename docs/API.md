# API 接口文档

Base URL: `http://localhost:8000`

交互式文档：
- Swagger UI：`http://localhost:8000/docs`（反向代理环境下可能因 iframe 限制无法使用）
- ReDoc：`http://localhost:8000/redoc`（推荐，无 iframe 依赖）

---

## 1. 获取筛选选项

`GET /api/filters`

返回可用于筛选的地区、年份、月份列表。结果缓存 24 小时。

### 响应示例

```json
{
  "markets": ["de-DE", "en-CA", "en-GB", "en-IN", "en-US", "es-ES", "fr-FR", "it-IT", "ja-JP", "pt-BR", "zh-CN"],
  "years": [2026],
  "year_months": {
    "2026": [4]
  }
}
```

### 调用示例

```bash
curl "http://localhost:8000/api/filters"
```

---

## 2. 壁纸分页列表

`GET /api/wallpapers`

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mkt` | string | 否 | 地区筛选（如 en-US、zh-CN） |
| `year` | integer | 否 | 年份筛选 |
| `month` | integer | 否 | 月份筛选 |
| `date` | string | 否 | 精确日期筛选，格式 `YYYY-MM-DD` |
| `date_from` | string | 否 | 起始日期筛选，格式 `YYYY-MM-DD` |
| `date_to` | string | 否 | 结束日期筛选，格式 `YYYY-MM-DD` |
| `keyword` | string | 否 | 关键词检索（最少 2 字符），需搭配 mkt/year/month/date/date_from/date_to 之一 |
| `dedup` | boolean | 否 | 是否按 `resources.sha256` 去重，默认 `false` |
| `page` | integer | 否 | 页码，默认 1，≥1 |
| `size` | integer | 否 | 每页条数，默认 20，范围 1-100 |

### 日期筛选规则

- `date` 用于精确某一天，不能和 `date_from` / `date_to` 同时使用
- `date_from` / `date_to` 可单独使用，也可组合为闭区间筛选
- 当同时提供 `date_from` 和 `date_to` 时，`date_from` 不能晚于 `date_to`

### `dedup=true` 行为说明

- 按 `resources.sha256` 聚合同一张图片
- `title` / `copyright` 按地区优先级选择：`zh-CN` > `en-US` > 其他
- `mkt` 字段改为数组，返回该图出现过的所有地区
- `date` 字段为该图最早发布日期
- `keyword` 命中任意一条关联 metadata 即返回该图
- `total`、`pages` 和分页结果都基于去重后的资源数量计算

### 响应示例

```json
{
  "items": [
    {
      "id": "08b00319b4bf4b145022467b2f5b0cccf2732adfd063621517932e5308e5478e",
      "mkt": "zh-CN",
      "date": "2026-04-16",
      "title": "蝙蝠信号：开启",
      "copyright": "灰头狐蝠母亲携幼崽，雅拉湾国家公园，澳大利亚 (© Doug Gimesy/Nature Picture Library)",
      "copyrightlink": "https://www.bing.com/search?q=gray-headed+flying+fox",
      "width": 3840,
      "height": 2160,
      "bytes": 3522378,
      "ext": "jpg",
      "mime_type": "image/jpeg",
      "thumbnail_url": "/api/images/08b003...e5478e?size=thumbnail",
      "preview_url": "/api/images/08b003...e5478e?size=preview",
      "download_url": "/api/images/08b003...e5478e/download"
    }
  ],
  "total": 18,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

`dedup=true` 响应示例：

```json
{
  "items": [
    {
      "id": "08b00319b4bf4b145022467b2f5b0cccf2732adfd063621517932e5308e5478e",
      "mkt": ["zh-CN", "en-US", "ja-JP"],
      "date": "2026-04-16",
      "title": "蝙蝠信号：开启",
      "copyright": "灰头狐蝠母亲携幼崽，雅拉湾国家公园，澳大利亚 (© Doug Gimesy/Nature Picture Library)",
      "copyrightlink": "https://www.bing.com/search?q=gray-headed+flying+fox",
      "width": 3840,
      "height": 2160,
      "bytes": 3522378,
      "ext": "jpg",
      "mime_type": "image/jpeg",
      "thumbnail_url": "/api/images/08b003...e5478e?size=thumbnail",
      "preview_url": "/api/images/08b003...e5478e?size=preview",
      "download_url": "/api/images/08b003...e5478e/download"
    }
  ],
  "total": 17,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| 400 | keyword 未搭配 mkt/year/month/date/date_from/date_to 之一 |
| 400 | `date` 与 `date_from` / `date_to` 冲突 |
| 400 | `date_from` 晚于 `date_to` |

### 调用示例

```bash
# 获取 zh-CN 地区 2026 年 4 月壁纸
curl "http://localhost:8000/api/wallpapers?mkt=zh-CN&year=2026&month=4"

# 获取 zh-CN 地区某一天壁纸
curl "http://localhost:8000/api/wallpapers?mkt=zh-CN&date=2026-04-21"

# 获取某个日期区间内的壁纸
curl "http://localhost:8000/api/wallpapers?date_from=2026-04-01&date_to=2026-04-21"

# 关键词搜索（必须搭配筛选条件）
curl "http://localhost:8000/api/wallpapers?mkt=zh-CN&keyword=蝙蝠"

# 分页
curl "http://localhost:8000/api/wallpapers?page=2&size=10"

# 去重浏览
curl "http://localhost:8000/api/wallpapers?dedup=true"

# 不带筛选条件，返回全部
curl "http://localhost:8000/api/wallpapers"
```

---

## 3. 图片访问

`GET /api/images/{id}`

### 路径参数

| 参数 | 说明 |
|------|------|
| `id` | SHA256 哈希值（64 位十六进制字符串） |

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `size` | string | `preview` | `thumbnail`（200px 宽）或 `preview`（≤1920px 宽） |

### 响应

返回图片文件流，`Content-Type` 为 `image/jpeg`，附带 `Cache-Control: public, max-age=86400`。

### 错误码

| 状态码 | 说明 |
|--------|------|
| 404 | 图片不存在或文件丢失 |
| 400 | size 参数无效 |

### 调用示例

```bash
# 预览图（默认）
curl "http://localhost:8000/api/images/08b003...e5478e" -o preview.jpg

# 缩略图
curl "http://localhost:8000/api/images/08b003...e5478e?size=thumbnail" -o thumb.jpg
```

---

## 4. 原图下载

`GET /api/images/{id}/download`

### 路径参数

| 参数 | 说明 |
|------|------|
| `id` | SHA256 哈希值（64 位十六进制字符串） |

### 响应

返回原图文件流（UHD 4K 画质），附带 `Content-Disposition: attachment` 响应头，浏览器会触发下载。

### 错误码

| 状态码 | 说明 |
|--------|------|
| 404 | 图片不存在或文件丢失 |

### 调用示例

```bash
curl -O "http://localhost:8000/api/images/08b003...e5478e/download"
```

---

## 5. 随机壁纸

`GET /api/wallpapers/random`

返回一张随机壁纸的可直接引用图片 URL，适合前端页面初始化时调用一次并直接用于 `<img src>`。
`image_url` 为站内相对路径，前端可直接作为同源地址使用，或按部署域名拼成完整 URL。

### 响应示例

```json
{
  "id": "08b00319b4bf4b145022467b2f5b0cccf2732adfd063621517932e5308e5478e",
  "image_url": "/api/images/08b00319b4bf4b145022467b2f5b0cccf2732adfd063621517932e5308e5478e?size=preview"
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| 404 | 当前没有可用壁纸 |

### 调用示例

```bash
curl "http://localhost:8000/api/wallpapers/random"
```

---

## 6. 健康检测

`GET /api/health`

无需认证，用于监控服务状态。响应时间目标 ≤10ms。

### 响应示例

```json
{
  "status": "healthy",
  "db_ok": true,
  "last_success_at": "2026-04-18T02:23:54.182000+00:00",
  "wallpaper_count": 89,
  "resource_count": 19,
  "markets_count": 11
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `status` | 服务状态：`healthy`（数据库正常）/ `unhealthy`（数据库异常） |
| `db_ok` | 数据库连接是否正常（执行 `SELECT 1` 测试） |
| `last_success_at` | 最后一次采集成功时间（ISO 8601），无记录时为 `null` |
| `wallpaper_count` | 可用壁纸总数（`metadata` 表 `is_deleted=0` 去重计数） |
| `resource_count` | 去重后资源总数（`resources` 表 `is_deleted=0` 计数） |
| `markets_count` | 已配置地区数（`crawl_state` 表记录数） |

### 调用示例

```bash
curl "http://localhost:8000/api/health"
```
