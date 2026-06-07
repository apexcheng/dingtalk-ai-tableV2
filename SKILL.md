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
- 如果不知道 `baseId`，先用 `list-bases` 或 `search-bases`
- 不带 `filters` / `sort` 时可以使用 `cursor`；带 `filters` 或 `sort` 时禁止使用 `cursor`
- 带 `filters` / `sort` 且结果可能超过 `100` 条时，改用 `process-records-with-marker` 或 `process-date-range-with-marker`
- `process-records-with-marker` 推荐动作名是 `export-with-marker`
- `process-records-with-marker` 的 `delete` 不写查询标记
- `update-records` 当前不支持用来清空字段
- `process-date-range-with-marker` 的日期范围最大 `366` 天
- 日期统计场景优先使用 `process-date-range-with-marker`，并读取 `summary.recordCount`

## 重字段自动过滤

`query-records` / `process-records-with-marker` / `process-date-range-with-marker`
**默认会自动排除 `attachment` / `image` / `picture` / `file` 这几类重字段**。

原因：这些字段的 cell 通常是 base64 / 远程文件 URL，单条就能几 MB。
如果不剔掉，结果会同时撑出三个坑：

1. 输出体积爆炸（一个 base64 图片就远大于上下文窗口）
2. MCP 响应超过 stdout pipe buffer (64KB) → JSON 被截断 → 解析报错
3. Agent 拿到巨大的 cell，毫无用处还占用上下文

被默认排除不代表字段不存在，只是这次查询不返回。

### 拿回重字段

确认需要图片 / 附件时，显式打开：

```bash
python scripts/aitable.py query-records --include-heavy-fields ...
```

`--include-heavy-fields` 适用于 `query-records` / `process-records-with-marker` /
`process-date-range-with-marker` 三个命令。

### 最佳实践：显式传 `--field-id`

大批量统计 / 导出时，**优先显式指定只需要的字段**：

```bash
python scripts/aitable.py query-records --field-id 日期 --field-id SKU ...
```

只读必要字段，体积最小、最稳定，避开 pipe buffer 和上下文问题。
一旦显式传了 `--field-id`，**不再自动排除重字段**——用户表达“我只要这些”，就以用户为准。

### excludedFields 返回字段

三个命令的结果中，多了一个 `excludedFields` 字段，列出本次被默认跳过的字段：

```json
{
  "excludedFields": [
    { "fieldId": "ycDADsx", "fieldName": "图片", "type": "attachment" }
  ]
}
```

- 只在“触发了自动排除”的时候才出现；显式传 `--field-id` 或传了 `--include-heavy-fields` 时不会出现
- 只看这个字段就能知道“哪些字段被默认跳过”，不用去猜

## 命令选择

按任务类型选择 CLI 子命令，不要直接调用 MCP 工具。

| 场景 | 使用命令 |
| --- | --- |
| 查看 base 信息和表列表 | `get-base` |
| 列出可访问的 base | `list-bases` |
| 按关键词搜索 base | `search-bases` |
| 查看表结构 | `get-tables` |
| 已知 fieldId，查看字段配置 | `get-fields` |
| 创建字段 | `create-fields` |
| 根据表名解析 tableId | `resolve-table` |
| 根据字段名获取字段 ID | `resolve-field` |
| 根据单选 / 多选名称获取选项 ID | `resolve-option` |
| 构造筛选条件 | `build-filter` |
| 读取少量数据，单次最多 100 条 | `query-records` |
| 读取带 `filters` / `sort` 的大量数据 | `process-records-with-marker` |
| 按日期范围批量处理数据 | `process-date-range-with-marker` |
| 新增记录 | `create-records` |
| 修改记录 | `update-records` |
| 删除已知 recordId 的记录 | `delete-records` |
| 准备附件上传参数 | `prepare-attachment-upload` |

## 表查询规则

- `get-base` 用于查询 base 信息和 table 列表
- `list-bases` 用于列出可访问的 base
- `search-bases` 用于按关键词搜索 base
- `get-tables` 不是列出所有表
- `get-tables` 只适用于已知 `tableId` 后查询表结构
- `get-fields` 只适用于已知 `fieldId` 后查看字段配置
- 如果只知道字段名，先使用 `resolve-field`
- 如果只知道表名，应先使用 `resolve-table`
- 如果想查看表结构，先用 `resolve-table`，再用 `get-tables`
- 如果已经知道 `baseId`，不需要先用 `list-bases` / `search-bases`

推荐流程：

```text
search-bases / list-bases -> get-base -> resolve-table -> resolve-field -> build-filter -> query/process
```

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

## 常用模板

```bash
python scripts/aitable.py get-base --base-id xxx
python scripts/aitable.py list-bases --limit 20
python scripts/aitable.py search-bases --query 评价 --limit 20
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
