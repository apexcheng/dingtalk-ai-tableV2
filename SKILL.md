---
name: dingtalk-ai-table
description: 钉钉 AI 表格（多维表）操作技能。使用 mcporter CLI 连接钉钉官方新版 AI 表格 MCP server，基于 baseId / tableId / fieldId / recordId 体系执行 Base、Table、Field、Record 的查询与增删改。适用于创建 AI 表格、搜索表格、读取表结构、批量增删改记录、批量建字段、更新字段配置、按模板建表等场景。默认使用当前 agent workspace 的 mcporter 注册名 dingtalk-ai-table，DINGTALK_AI_TABLE_DIRECT_URL 仅作为可选直连兜底。
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

# 钉钉 AI 表格 OpenClaw 规则

本文件只保留硬规则和最小调用约定。

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

## 硬规则

- `query_records.limit` 最大只能是 `100`。
- 只要出现 `filters` 或 `sort`，就禁止传 `cursor`。
- `filters` 必须是对象结构，不能是数组。
- 禁止 `filterType`。
- 过滤字段必须使用 `fieldId`，不能使用 `fieldName`。
- 只允许已确认的 operator：`eq`、`ne`、`date_eq`。
- 禁止 `gte`、`lte`、`greater_equal`、`less_than`、`is_after`、`is_before`。
- `date_eq` 只接受 `YYYY-MM-DD`。
- 日期范围查询必须按天拆成多次 `date_eq`。
- 单选 / 多选过滤必须使用 option id。
- `create_fields` 单次最多 15 个字段。
- `get_tables` / `get_fields` 单次最多 10 个对象。
- `create_records` / `update_records` / `delete_records` 单次最多 100 条。
- `query_records` 单次最多 100 条。
- `process_records_with_marker` 和 `process_date_range_with_marker` 是稳定分页的标准入口。
- `查询标记` 是唯一允许的辅助分页字段名。
- 附件可靠写入必须走 `prepare_attachment_upload -> PUT uploadUrl -> fileToken`。
- `update_records` 更新附件字段时是整体覆盖，不是追加。

## 最小约定

- 默认使用 `mcporter call dingtalk-ai-table ...`
- 如果没有注册名，可用 `DINGTALK_AI_TABLE_DIRECT_URL` 兜底
- 复杂参数用 `--args '<json>'`
- 不要手拼 `filters` / `cursor` / 分页标记逻辑，优先用 Python 安全调用层
