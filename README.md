# dingtalk-ai-table-cli

这是一个面向 Agent 的钉钉 AI 表格安全 CLI。

`dingtalk_ai_table` 包只保留为内部实现，Agent 统一通过下面的入口调用：

```bash
python scripts/aitable.py <subcommand> ...
```

## 配置

按这个顺序配就行：

1. 优先读取 `MCPORTER_CONFIG` 指向的配置文件
2. 其次读取当前工作目录下的 `config/mcporter.json`

不要求 `pip install dingtalk_ai_table`，也不要求设置 `PYTHONPATH`。

## 关键边界

- `query-records` 单次最多返回 `100` 条
- `limit` 不能超过 `100`
- 不带 `filters` / `sort` 时，可以使用 `cursor` 翻页
- 带 `filters` 或 `sort` 时，禁止使用 `cursor`
- 带 `filters` / `sort` 且可能超过 `100` 条时，改用 `process-records-with-marker` 或 `process-date-range-with-marker`
- 当前 `update-records` 会忽略空字符串和 `null` 等空值，因此不能用它清空字段；如果要清空字段，先人工确认，不要默认执行
- `process-date-range-with-marker` 的日期范围最多 `366` 天

## CLI 子命令

- `get-tables`
- `get-fields`
- `create-fields`
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

## 输出规则

- `stdout` 只输出最终 JSON
- 失败时也输出 JSON，包含 `ok=false`、`command`、`error.type`、`error.message`
- `query-records` 默认只输出摘要和最多 3 条 `preview`
- `query-records --output <file>` 时，完整 records 写入 JSONL 文件
- `process-records-with-marker` 必须传 `--output`
- `process-date-range-with-marker` 必须传 `--output-dir`
- `process-records-with-marker` 推荐使用 `export-with-marker`，这个动作会写入查询标记
- `process-records-with-marker` 适用于带 `filters` 或 `sort` 的批处理场景；无过滤条件时不要使用。
- `process-records-with-marker` 的 `delete` 不写查询标记，只做“查询一批、删一批、直到为空”
- 大结果不会直接打印到终端

## 示例

```bash
python scripts/aitable.py resolve-field --base-id xxx --table-id xxx --field-name 状态
python scripts/aitable.py query-records --input examples/query_records.json
python scripts/aitable.py create-records --input examples/create_records.json
python scripts/aitable.py process-records-with-marker --input examples/process_records_with_marker.json
python scripts/aitable.py process-date-range-with-marker --input examples/process_date_range_with_marker.json
```
