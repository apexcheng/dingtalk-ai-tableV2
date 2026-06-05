---
name: dingtalk-ai-table
description: OpenClaw 安全调用层，基于 mcporter 调用 dingtalk-ai-table MCP，只暴露字段解析、记录增删改查、查询标记分页和附件上传前置，所有高风险边界由 Python 硬校验。
version: 0.7.3
metadata:
  author: Marila@Dingtalk
  category: productivity
  tags:
    - dingtalk
    - spreadsheet
    - mcp
    - automation
    - data-management
  documentation: https://github.com/apexcheng/dingtalk-ai-tableV2
  support: https://github.com/apexcheng/dingtalk-ai-tableV2/issues
  openclaw:
    requires:
      bins:
        - mcporter
        - python3
    homepage: https://github.com/apexcheng/dingtalk-ai-tableV2
---

# dingtalk-ai-table OpenClaw 规则

只保留最小调用约定和硬限制。

## 入口

OpenClaw 只需要直接调用包根导出的 9 个函数：

- `resolve_field_id`
- `resolve_option_id`
- `safe_query_records`
- `safe_create_records`
- `safe_update_records`
- `safe_delete_records`
- `process_records_with_marker`
- `process_date_range_with_marker`
- `safe_prepare_attachment_upload`

## 硬限制

- `query_records.limit` 最大只能是 `100`
- 只要出现 `filters` 或 `sort`，就禁止传 `cursor`
- `filters` 必须是对象结构，不能是数组
- 禁止 `filterType`
- 过滤字段必须使用 `fieldId`，不能使用 `fieldName`
- 只允许 `eq`、`ne`、`date_eq`
- 禁止 `gte`、`lte`、`greater_equal`、`less_than`、`is_after`、`is_before`
- `date_eq` 只接受 `YYYY-MM-DD`
- 单选 / 多选过滤必须使用 option id
- `create_fields` 单次最多 `15` 个字段
- `get_tables` / `get_fields` 单次最多 `10` 个对象
- `create_records` / `update_records` / `delete_records` 单次最多 `100` 条
- `query_records` 单次最多 `100` 条
- `查询标记` 是唯一允许的辅助分页字段名
- 附件可靠写入必须先 `prepare_attachment_upload`

## 最小约定

- 默认使用 `mcporter call dingtalk-ai-table ...`
- 如果没有注册名，可用 `DINGTALK_AI_TABLE_DIRECT_URL` 兜底
- 不要手拼 `filters` / `cursor` / 分页推进逻辑
