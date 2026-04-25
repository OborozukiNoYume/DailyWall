# 覆盖率报告

生成时间：`2026-04-25 16:30 CST`

执行命令：

```bash
uv run pytest \
  --cov=app \
  --cov=crawler \
  --cov=scripts \
  --cov-report=term-missing \
  --cov-report=xml:docs/coverage.xml \
  --cov-report=html:docs/coverage_html
```

测试结果：

- `91 passed`
- 总覆盖率：`91%`（`912` 行中未覆盖 `82` 行）

报告产物：

- `docs/coverage.xml`
- `docs/coverage_html/index.html`

主要未充分覆盖文件：

| 文件 | 覆盖率 | 未覆盖行 |
|------|--------|----------|
| `app/database.py` | `88%` | `66-72` |
| `scripts/check.py` | `78%` | `38, 46-48, 72, 88, 141-161, 165` |
| `crawler/crawler.py` | `82%` | `30-31, 41-43, 47-50, 63-67, 70, 72, 96-99, 112-115, 123-125` |
| `app/main.py` | `83%` | `78-96, 113` |
| `app/services/health_service.py` | `88%` | `12-13` |

其余说明：

- `app/api/*` 路由层已基本覆盖，除 `app/api/responses.py` 有 1 行未覆盖外，其余均为 `100%`。
- 新增的 `app/logging_utils.py` 当前覆盖率为 `98%`，未覆盖分支为非法组件名的异常路径。
- 图片服务与图片工具相关文件当前覆盖率为 `90%` 及以上。
- HTML 报告适合查看逐文件命中情况，XML 报告适合后续接入 CI 或其他分析工具。
