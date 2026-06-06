# dingtalk-ai-tableV2

这是一个面向 Agent 的钉钉 AI 表格安全 CLI。

`dingtalk_ai_table` 包保留为内部实现，Agent 统一通过下面的入口调用：

```bash
python scripts/aitable.py <subcommand> ...
```

## 依赖

- 需要 `mcporter >= 0.8.1`
- 默认调用 `mcporter call dingtalk-ai-table ...`
- 如果当前环境没有注册名，可用 `DINGTALK_AI_TABLE_DIRECT_URL` 兜底
- 不要求 `pip install dingtalk_ai_table`
- 不要求设置 `PYTHONPATH`

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
- 大结果不会直接打印到终端

## 示例

```bash
python scripts/aitable.py resolve-field --base-id xxx --table-id xxx --field-name 状态
python scripts/aitable.py query-records --input examples/query_records.json --output out/query_records.jsonl
python scripts/aitable.py create-records --input examples/create_records.json
python scripts/aitable.py process-records-with-marker --input examples/query_records.json --output out/process.jsonl
python scripts/aitable.py process-date-range-with-marker --base-id xxx --table-id xxx --date-field-id fld_xxx --start-date 2026-06-01 --end-date 2026-06-07 --output-dir out/daily
```
