# dingtalk-ai-table-cli

这是一个面向 Agent 的钉钉 AI 表格安全 CLI。

统一入口：

```bash
python scripts/aitable.py <subcommand> ...
```

`dingtalk_ai_table` 包只作为内部实现，不建议 Agent 直接 `import`，也不要手写 `mcporter call`。

## 配置

按下面顺序读取配置：

1. `MCPORTER_CONFIG`
2. 当前工作目录下的 `config/mcporter.json`

## 关键边界

- 所有命令输出仍然是 JSON
- 复杂参数优先使用 `--input`
- `query-records` 单次最多返回 `100` 条
- `query-records` 的 `total` 只表示本次返回的 records 数量，不是服务端全量 count
- 用户问“有多少条 / 统计数量 / count”时，如果结果可能超过 `100`，不能直接用 `query-records` 的 `total`
- `limit` 不能超过 `100`
- 如果不知道 `baseId`，先用 `list-bases` 或 `search-bases`
- `filters + cursor` 允许
- `sort + cursor` 暂不允许
- 大批量只读查询可以用 `query-records + cursor` 分页
- 会修改数据集的批处理仍优先用 `process-records-with-marker` / `process-date-range-with-marker`
- `process-records-with-marker` / `process-date-range-with-marker` 都不支持 `sort`（marker 回写会改结果集，排序分页会造成重复和漏数据，只接受 `filters`）
- `update-records` 当前不会用来清空字段
- `process-date-range-with-marker` 的日期范围最大 `366` 天

## 重字段自动过滤

`query-records` / `process-records-with-marker` / `process-date-range-with-marker`
**默认会自动排除 `attachment` / `image` / `picture` / `file` 这几类重字段**。

原因：这些字段的 cell 通常是 base64 / 远程文件 URL，单条就能几 MB。
不踢掉会同时搞坏三件事：

1. 输出体积爆炸（一个 base64 图片就远大于上下文窗口）
2. MCP 响应超过 stdout pipe buffer (64KB) → JSON 被截断 → 解析报错
3. Agent 拿到巨大的 cell，毫无用处还占上下文

被默认排除不等于字段不存在，只是本次查询不返回。

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
python scripts/aitable.py query-records --field-id fld_date --field-id fld_sku ...
```

只读必要字段，体积最小、最稳定，避开 pipe buffer 和上下文问题。
一旦显式传了 `--field-id`，**不再自动排除重字段**——用户表达“我只要这些”，就以用户为准。
如果手上只有字段名（如 `日期` / `SKU`），先用 `resolve-field` 拿到对应的 `fieldId` 再传进来。

### excludedFields 返回字段

三个命令的结果中多了一个 `excludedFields` 字段，列出本次被默认跳过的字段：

```json
{
  "excludedFields": [
    { "fieldId": "ycDADsx", "fieldName": "图片", "type": "attachment" }
  ]
}
```

- 只在“触发了自动排除”的时候才出现；显式传 `--field-id` 或传了 `--include-heavy-fields` 时不出现
- 只看这个字段就能知道“哪些字段被默认跳过”，不用去猜

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

## 表查询说明

- `get-base`：按 `baseId` 查询 base 信息和 table 列表
- `list-bases`：列出可访问的 base
- `search-bases`：按关键词搜索 base
- `get-tables`：不是“列出 base 下所有表”
- `get-tables` 只适用于“已经知道 `tableId`，再按 `tableId` 查询表结构”
- `get-fields` 只适用于“已经知道 `fieldId` 后查看字段配置”
- 如果只知道字段名，先使用 `resolve-field`
- 如果只知道表名，应先使用 `resolve-table`
- 如果想查看表结构，先用 `resolve-table`，再用 `get-tables`
- 如果已经知道 `baseId`，不需要先用 `list-bases` / `search-bases`

推荐流程：

```text
search-bases / list-bases -> get-base -> resolve-table -> resolve-field -> build-filter -> query/process
```

## 输出规则

- `stdout` 只输出最终 JSON
- 失败时也输出 JSON，包含 `ok=false`、`command`、`error.type`、`error.message`
- `query-records` 默认只输出摘要和最多 `3` 条 `preview`
- `query-records --output <file>` 时，完整 records 写入 JSONL 文件
- 日期统计场景优先使用 `process-date-range-with-marker`，并读取 `summary.recordCount`
- `process-records-with-marker` 必须传 `--output`
- `process-date-range-with-marker` 必须传 `--output-dir`
- 大结果不会直接打印到终端

## 示例

```bash
python scripts/aitable.py get-base --base-id xxx
python scripts/aitable.py list-bases --limit 20
python scripts/aitable.py search-bases --query 评价 --limit 20
python scripts/aitable.py resolve-table --base-id xxx --table-name 评价收集表
python scripts/aitable.py resolve-field --base-id xxx --table-id xxx --field-name 日期
python scripts/aitable.py query-records --input examples/query_records.json
```
