# dingtalk-ai-tableV2

这是给 OpenClaw 直接调用的钉钉 AI 表格 MCP 安全调用层，不是通用 SDK，也不是完整 CLI。

## 安装和配置

- 需要 `mcporter >= 0.8.1`
- 默认调用 `mcporter call dingtalk-ai-table ...`
- 如果当前环境没有注册名，可用 `DINGTALK_AI_TABLE_DIRECT_URL` 兜底

## OpenClaw 入口

优先从包根导入这 9 个函数：

```python
from dingtalk_ai_table import (
    resolve_field_id,
    resolve_option_id,
    safe_query_records,
    safe_create_records,
    safe_update_records,
    safe_delete_records,
    process_records_with_marker,
    process_date_range_with_marker,
    safe_prepare_attachment_upload,
)
```

## 最小示例

```python
from dingtalk_ai_table import process_date_range_with_marker, safe_query_records

records = safe_query_records(
    base_id="base_xxx",
    table_id="tbl_xxx",
    limit=100,
)

process_date_range_with_marker(
    base_id="base_xxx",
    table_id="tbl_xxx",
    date_field_id="fld_date_xxx",
    start_date="2026-06-01",
    end_date="2026-06-07",
    process_batch=lambda batch: print(len(batch)),
)
```
