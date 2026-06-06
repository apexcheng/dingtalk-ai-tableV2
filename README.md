# dingtalk-ai-table-cli

这是一个面向 Agent 的钉钉 AI 表格安全 CLI。

`dingtalk_ai_table` 包只保留为内部实现，Agent 统一通过下面的入口调用：

```bash
python scripts/aitable.py <subcommand> ...
```

## 配置

按这个顺序配就行：

1. 优先使用 `agent workspace/config/mcporter.json`
2. 其次使用 `DINGTALK_AI_TABLE_DIRECT_URL`

不要求 `pip install dingtalk_ai_table`，也不要求设置 `PYTHONPATH`。

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
