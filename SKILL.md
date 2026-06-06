---
name: dingtalk-ai-table-cli
description: Agent-first safe DingTalk AI Table access via scripts/aitable.py CLI.
version: 1.1.0
metadata:
  author: Marila@Dingtalk
  category: productivity
  tags:
    - dingtalk
    - spreadsheet
    - mcp
    - automation
    - data-management
  documentation: https://github.com/apexcheng/dingtalk-ai-table-cli
  support: https://github.com/apexcheng/dingtalk-ai-table-cli/issues
  openclaw:
    requires:
      bins:
        - mcporter
        - python3
    homepage: https://github.com/apexcheng/dingtalk-ai-table-cli
---

# dingtalk-ai-table-cli Skill

Agent 不直接 `import dingtalk_ai_table`，也不手拼 `mcporter call`。
统一入口是：

```bash
python scripts/aitable.py <subcommand> ...
```

`dingtalk_ai_table` 包只作为 CLI 内部实现，不作为 Agent 的主调用面。

## 规则

- 所有业务调用都走 `scripts/aitable.py`
- 所有 CLI 输出都保持 JSON
- 复杂参数优先使用 `--input` JSON 文件
- 优先读取 `MCPORTER_CONFIG` 指向的配置文件，其次读取当前工作目录下的 `config/mcporter.json`
- `query-records` 默认只返回摘要，不直接输出完整 records
- `query-records` 单次最多返回 `100` 条，`limit` 不能超过 `100`
- 不带 `filters` / `sort` 时，可以使用 `cursor` 翻页；带 `filters` 或 `sort` 时，禁止使用 `cursor`
- 带 `filters` / `sort` 且可能超过 `100` 条时，改用 `process-records-with-marker` 或 `process-date-range-with-marker`
- `process-records-with-marker` 推荐动作名是 `export-with-marker`
- `process-records-with-marker` 适用于带 `filters` 或 `sort` 的批处理场景；无过滤条件时不要使用。
- `process-records-with-marker` 的 `delete` 不写查询标记
- `process-date-range-with-marker` 也走同一套 CLI 入口和 JSON 输出规则
- `update-records` 会忽略空字符串和 `null` 等空值，因此当前版本不支持通过 `update-records` 清空字段；如果要清空字段，先人工确认，不要默认执行
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

## 常用调用模板

```bash
python scripts/aitable.py resolve-field --base-id xxx --table-id xxx --field-name 状态
python scripts/aitable.py resolve-option --base-id xxx --table-id xxx --field-name 状态 --option-name 进行中
python scripts/aitable.py build-filter --operator eq --field-id fld_xxx --value 进行中
python scripts/aitable.py query-records --input examples/query_records.json
python scripts/aitable.py create-records --input examples/create_records.json
python scripts/aitable.py update-records --input examples/update_records.json
python scripts/aitable.py delete-records --input examples/delete_records.json
python scripts/aitable.py process-records-with-marker --input examples/process_records_with_marker.json
python scripts/aitable.py process-date-range-with-marker --input examples/process_date_range_with_marker.json
python scripts/aitable.py prepare-attachment-upload --input examples/prepare_attachment_upload.json
```
