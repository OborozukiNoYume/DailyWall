# 错误记录

本文件记录开发过程中遇到的典型问题和解决方案。

---

## 记录格式

```
### [日期] 简要描述
- **现象**：...
- **原因**：...
- **解决**：...
- **教训**：...
```

---

## 示例

### [2026-04-18] SQLite 内存数据库测试表不存在
- **现象**：使用 `sqlite:///:memory:` 测试时报 "no such table" 错误
- **原因**：SQLite 内存数据库每个连接独立，SQLAlchemy 默认连接池创建多个连接导致表不可见
- **解决**：使用 `StaticPool` 替代默认连接池
- **教训**：SQLite 内存数据库测试必须使用 `StaticPool`

### [2026-04-18] 只读 API 引擎找不到表
- **现象**：使用 `sqlite:///path?mode=ro` 的只读引擎无法看到已创建的表
- **原因**：SQLAlchemy 的 SQLite URL 解析未正确处理 URI 模式参数
- **解决**：使用 `creator` 参数自定义连接函数，通过 `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` 建立只读连接
- **教训**：SQLite URI 模式需通过 `creator` 自定义连接，而非 URL 查询参数

### [2026-04-18] scripts/inspect.py 与标准库 inspect 模块命名冲突
- **现象**：运行 `scripts/crawl.py` 时报 `ImportError: cannot import name 'settings' from partially initialized module 'app.config'`，asyncio 初始化阶段触发循环导入
- **原因**：Python 的 asyncio 内部会 `import inspect`，而 `scripts/inspect.py` 与标准库同名，被优先解析为项目文件，导致加载 `app.config` 时再次触发 asyncio 初始化形成循环
- **解决**：将 `scripts/inspect.py` 重命名为 `scripts/check.py`
- **教训**：项目文件不可与 Python 标准库模块同名，尤其是 `inspect`、`test`、`collections` 等常见名

### [2026-04-18] 采集脚本首次运行表不存在
- **现象**：删除 `data/` 目录后运行 `scripts/crawl.py`，报 `no such table: metadata`
- **原因**：表创建逻辑仅在 `app/main.py` 的 lifespan 中通过 `init_db()` 执行，`scripts/crawl.py` 未调用 `init_db()`
- **解决**：在 `scripts/crawl.py` 的 `main()` 中添加 `settings.ensure_dirs()` 和 `init_db()` 调用
- **教训**：独立脚本入口必须自行初始化数据库，不能依赖 API 服务的 lifespan

### [2026-04-18] 采集时 base_path 年月解析索引错误
- **现象**：首次采集部分壁纸报 `invalid literal for int() with base 10: '2c'` 等错误，成功入库的 3 张图片 year/month 字段也互换了
- **原因**：`base_path` 格式为 `wallpaper/2026/04/{sha256}`，split("/") 后 `[-3]=2026, [-2]=04, [-1]=sha256`，但代码错误地用 `[-2]` 取年份、`[-1][:2]` 取月份（实际取到 SHA256 前两位）
- **解决**：修正为 `split("/")[-3]` 取年份、`split("/")[-2]` 取月份
- **教训**：路径解析应验证 split 结果的实际含义，而非假设索引位置；也可考虑直接从时间变量取值而非从路径反推

### [2026-04-18] Bing API 地理锁定导致多市场文案全部为中文
- **现象**：数据库中 6 个市场的 title、copyright 字段内容完全相同且均为中文，未按市场返回本地语言
- **原因**：Bing HPImageArchive.aspx API 根据 IP 地理位置决定响应语言，`mkt` 参数在中国大陆 IP 下被忽略，无论传何值均返回中文内容。同时 Bing 会将 `www.bing.com` 重定向至 `cn.bing.com`。测试确认 `Accept-Language`、`setlang`、`cc` 参数、Cookie、区域域名（`de.bing.com`、`jp.bing.com` 等）均无法绕过此限制
- **解决**：引入 `PROXY_URL` 配置项，通过国际出口代理访问 Bing API，使 `mkt` 参数生效。爬虫代码统一通过 `create_http_client()` 构建 HTTP 客户端，自动注入代理配置。清空错误 metadata 后重新抓取
- **教训**：Bing API 的 `mkt` 参数仅在 IP 与请求市场匹配时生效；中国大陆部署时必须配置代理才能获取多语言元数据

### [2026-04-21 15:49] Cron 测试任务中未转义百分号导致任务未执行
- **现象**：为验证定时任务创建的 `cron_test.log` 在计划时间后仍未生成，测试任务没有写出日志
- **原因**：我写入 `crontab` 的命令使用了 `printf "[%s] ..."` 和 `date -Iseconds`，其中 `%` 在 Cron 命令中具有特殊含义，未转义时会被当作换行分隔，导致实际执行命令被破坏
- **解决**：确认任务未成功执行，并记录该错误；后续应改为转义 `%` 或改用不含 `%` 的 shell 形式重建测试任务
- **教训**：写入 `crontab` 的命令不能直接复用普通 shell 命令模板，必须先检查 `%`、换行和重定向在 Cron 语境下的特殊解析规则
