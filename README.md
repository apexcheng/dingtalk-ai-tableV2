# dingtalk-ai-table-cli

这是一个面向 Agent 的钉钉 AI 表格安全 CLI。

统一入口：

```bash
python scripts/aitable.py <subcommand> ...
```

`dingtalk_ai_table` 包只作为内部实现，不建议 Agent 直接 `import`，也不要手写 `mcporter call`。

## 配置

按下面顺序读取配置：

1. `MCPORTER_CONFIG`
2. 当前工作目录下的 `config/mcporter.json`

## 关键边界

- 所有命令输出仍然是 JSON
- 复杂参数优先使用 `--input`
- `query-records` 单次最多返回 `100` 条
- `query-records` 的 `total` 只表示本次返回的 records 数量，不是服务端全量 count
- 用户问“有多少条 / 统计数量 / count”时，如果结果可能超过 `100`，不能直接用 `query-records` 的 `total`
- `limit` 不能超过 `100`
- 如果不知道 `baseId`，先用 `list-bases` 或 `search-bases`
- 不带 `filters` / `sort` 时可以使用 `cursor`
- 带 `filters` 或 `sort` 时禁止使用 `cursor`
- 带 `filters` / `sort` 且可能超过 `100` 条时，使用 `process-records-with-marker` 或 `process-date-range-with-marker`
- `update-records` 当前不会用来清空字段
- `process-date-range-with-marker` 的日期范围最多 `366` 天

## CLI 子命令

- `get-base`
- `list-bases`
- `search-bases`
- `get-tables`
- `get-fields`
- `create-fields`
- `resolve-table`
- `resolve-field`
- `resolve-option`
- `build-filter`
- `query-records`
- `create-records`
- `update-records`
- `delete-records`
- `process-records-with-marker`
- `process-date-range-with-marker`
- `prepare-attachment-upload`

## 表查询说明

- `get-base`：按 `baseId` 查询 base 信息和 table 列表
- `list-bases`：列出可访问的 base
- `search-bases`：按关键词搜索 base
- `get-tables`：不是“列出 base 下所有表”
- `get-tables` 只适用于“已经知道 `tableId`，再按 `tableId` 查询表结构”
- 如果只知道表名，应先使用 `resolve-table`
- 如果已经知道 `baseId`，不需要先用 `list-bases` / `search-bases`

推荐流程：

```text
search-bases / list-bases -> get-base -> resolve-table -> resolve-field -> build-filter -> query/process
```

## 输出规则

- `stdout` 只输出最终 JSON
- 失败时也输出 JSON，包含 `ok=false`、`command`、`error.type`、`error.message`
- `query-records` 默认只输出摘要和最多 `3` 条 `preview`
- `query-records --output <file>` 时，完整 records 写入 JSONL 文件
- 日期统计场景优先使用 `process-date-range-with-marker`，并读取 `summary.recordCount`
- `process-records-with-marker` 必须传 `--output`
- `process-date-range-with-marker` 必须传 `--output-dir`
- 大结果不会直接打印到终端

## 示例

```bash
python scripts/aitable.py get-base --base-id xxx
python scripts/aitable.py list-bases --limit 20
python scripts/aitable.py search-bases --query 评价 --limit 20
python scripts/aitable.py resolve-table --base-id xxx --table-name 评价收集表
python scripts/aitable.py resolve-field --base-id xxx --table-id xxx --field-name 日期
python scripts/aitable.py query-records --input examples/query_records.json
```
