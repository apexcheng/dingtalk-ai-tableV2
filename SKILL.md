---
name: dingtalk-ai-table-cli
description: Agent-first safe DingTalk AI Table access via scripts/aitable.py CLI.
version: 1.2.0
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

Agent 不直接 `import dingtalk_ai_table`，也不手写 `mcporter call`。

统一入口：

```bash
python scripts/aitable.py <subcommand> ...
```

## 规则

- 所有业务调用都走 `scripts/aitable.py`
- 所有 CLI 输出都保持 JSON
- 复杂参数优先使用 `--input`
- 优先读取 `MCPORTER_CONFIG`，其次读取当前工作目录下的 `config/mcporter.json`
- `query-records` 默认只返回摘要，不直接输出完整 records
- `query-records` 单次最多返回 `100` 条，`limit` 不能超过 `100`
- `query-records` 的 `total` 只表示本次返回的 records 数量，不是服务端全量 count
- 用户问“有多少条 / 统计数量 / count”时，如果结果可能超过 `100`，不能直接用 `query-records` 的 `total`
- 不带 `filters` / `sort` 时可以使用 `cursor`；带 `filters` 或 `sort` 时禁止使用 `cursor`
- 带 `filters` / `sort` 且可能超过 `100` 条时，改用 `process-records-with-marker` 或 `process-date-range-with-marker`
- `process-records-with-marker` 推荐动作名是 `export-with-marker`
- `process-records-with-marker` 的 `delete` 不写查询标记
- `update-records` 当前不支持用来清空字段
- `process-date-range-with-marker` 的日期范围最多 `366` 天
- 日期统计场景优先使用 `process-date-range-with-marker`，并读取 `summary.recordCount`

## 命令选择

按任务类型选择 CLI 子命令，不要直接调用 MCP 工具。

| 场景 | 使用命令 |
| --- | --- |
| 查看 base 信息和表列表 | `get-base` |
| 查看表结构 | `get-tables` |
| 查看字段列表 | `get-fields` |
| 创建字段 | `create-fields` |
| 根据表名解析 tableId | `resolve-table` |
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

## 表查询规则

- `get-base` 用于查询 base 信息和 table 列表
- `get-tables` 不是列出所有表
- `get-tables` 只适用于已知 `tableId` 后查询表结构
- 如果只知道表名，应先用 `resolve-table`
- 当前必须先提供 `baseId`
- 当前没有 `list-bases` / `search-bases`

推荐流程：

```text
resolve-table -> resolve-field -> build-filter -> query-records
```

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

- `get-base`
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

## 常用模板

```bash
python scripts/aitable.py get-base --base-id xxx
python scripts/aitable.py resolve-table --base-id xxx --table-name 评价收集表
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
