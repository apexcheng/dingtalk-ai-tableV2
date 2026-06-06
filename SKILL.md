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

## 命令选择

按任务类型选择 CLI 子命令，不要直接调用 MCP 工具。

| 场景 | 使用命令 |
| --- | --- |
| 查看表列表 | `get-tables` |
| 查看字段列表 | `get-fields` |
| 创建字段 | `create-fields` |
| 根据字段名获取字段 ID | `resolve-field` |
| 根据单选/多选名称获取选项 ID | `resolve-option` |
| 构造筛选条件 | `build-filter` |
| 读取少量数据，预计 `100` 条以内 | `query-records` |
| 读取带 `filters` / `sort` 的大量数据 | `process-records-with-marker` |
| 按日期范围批量处理数据 | `process-date-range-with-marker` |
| 新增记录 | `create-records` |
| 修改记录 | `update-records` |
| 删除已知 recordId 的记录 | `delete-records` |
| 准备附件上传参数 | `prepare-attachment-upload` |

## 推荐流程

### 查询少量数据

1. 需要字段 ID 时，先用 `resolve-field`
2. 需要筛选时，用 `build-filter`
3. 用 `query-records` 查询
4. 需要完整 records 时，使用 `--output` 写入 JSONL 文件

### 查询或导出大量数据

1. 先用 `resolve-field` / `resolve-option` 准备字段和选项 ID
2. 用 `build-filter` 构造筛选条件
3. 使用 `process-records-with-marker`
4. 输出结果写入 `--output` 指定的 JSONL 文件

### 按日期范围批量处理

1. 先确认日期字段
2. 日期范围不超过 `366` 天
3. 使用 `process-date-range-with-marker`
4. 不要自己循环拼多个 MCP 请求

### 新增或修改记录

1. 用 `get-fields` 或 `resolve-field` 确认字段 ID
2. 用 `create-records` 新增记录
3. 用 `update-records` 修改记录
4. 不要用 `update-records` 清空字段

### 附件字段写入

1. 先用 `prepare-attachment-upload` 准备上传参数
2. 再用 `create-records` 或 `update-records` 写入记录

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
python scripts/aitable.py resolve-field --base-id base_xxxx --table-id tbl_xxxx --field-name 状态
python scripts/aitable.py resolve-option --base-id base_xxxx --table-id tbl_xxxx --field-name 状态 --option-name 进行中
python scripts/aitable.py build-filter --operator eq --field-id fld_xxxx --value 进行中
python scripts/aitable.py query-records --input examples/query_records.json
python scripts/aitable.py create-records --input examples/create_records.json
python scripts/aitable.py update-records --input examples/update_records.json
python scripts/aitable.py delete-records --input examples/delete_records.json
python scripts/aitable.py process-records-with-marker --input examples/process_records_with_marker.json
python scripts/aitable.py process-date-range-with-marker --input examples/process_date_range_with_marker.json
python scripts/aitable.py prepare-attachment-upload --input examples/prepare_attachment_upload.json
```
