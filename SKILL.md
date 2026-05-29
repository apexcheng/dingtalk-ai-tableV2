---
name: dingtalk-ai-table
description: 钉钉 AI 表格（多维表）操作技能。使用 mcporter CLI 连接钉钉官方新版 AI 表格 MCP server，基于 baseId / tableId / fieldId / recordId 体系执行 Base、Table、Field、Record 的查询与增删改。适用于创建 AI 表格、搜索表格、读取表结构、批量增删改记录、批量建字段、更新字段配置、按模板建表等场景。默认使用当前 agent workspace 的 mcporter 注册名 dingtalk-ai-table，DINGTALK_AI_TABLE_DIRECT_URL 仅作为可选直连兜底。
version: 0.7.0
metadata:
  author: Marila@Dingtalk
  category: productivity
  tags:
    - dingtalk
    - spreadsheet
    - mcp
    - automation
    - data-management
  documentation: https://github.com/apexcheng/dingtalk-ai-table
  support: https://github.com/apexcheng/dingtalk-ai-table/issues
  openclaw:
    requires:
      bins:
        - mcporter
        - python3
    homepage: https://github.com/apexcheng/dingtalk-ai-table
---

# 钉钉 AI 表格操作（新版 MCP）

## 快速开始

### 1. 首次使用先检查 schema

首次调用前，或当 `mcporter` 里注册的 MCP Server 地址变化后，先执行：

```bash
mcporter list dingtalk-ai-table --schema
```

新版 schema 应包含这些能力：

- `list_bases`
- `get_base`
- `get_tables`
- `get_fields`
- `query_records`
- `create_records`
- `update_records`
- `delete_records`
- `prepare_attachment_upload`

如果 schema 中出现旧工具名，或者仍然基于旧参数体系，必须停止调用并提示版本不匹配。旧工具名包括：

- `get_root_node_of_my_document`
- `create_base_app`
- `list_base_tables`
- `add_base_record`
- `search_base_record`
- `list_base_field`

## 核心概念

按新版 MCP schema 工作：

- Base：`baseId`
- Table：`tableId`
- Field：`fieldId`
- Record：`recordId`

主示例统一使用：

```bash
mcporter call dingtalk-ai-table list_bases limit=5
```

不要把直连 URL 示例作为主示例，也不要把旧参数体系当成新 schema 使用。

## 必须遵守的查询规则

### 1. cursor 使用边界

`query_records` 里，`cursor` 不是永远不能用。

| 查询场景 | 是否可以用 cursor 连续翻页 | 推荐方式 |
| --- | ---: | --- |
| 无 filters、无 sort，普通读取 | 可以 | cursor 连续读取 |
| 有 filters，无 sort | 不要依赖 cursor | 第一页 -> 处理 -> 回写回查标记 -> 查未标记 |
| 无 filters，有 sort | 不要依赖 cursor | 第一页 -> 处理 -> 回写回查标记 -> 查未标记 |
| 有 filters、有 sort | 不要依赖 cursor | 第一页 -> 处理 -> 回写回查标记 -> 查未标记 |

无 `filters`、无 `sort` 的普通连续读取可以使用 `cursor`，适合普通读取、导出、统计或低风险遍历，只要不依赖排序语义，也不要求复杂过滤后的稳定分页。

### 2. 服务端查询限制

只要使用了 `filters` 或 `sort` 任意一种，就不要依赖 `cursor` 连续翻页完成稳定批量处理。

`query_records` 的服务端语义不保证以下方式可用于稳定批量遍历：

- 排序 + 过滤 + cursor 连续翻页
- 排序 + cursor 连续翻页
- 过滤 + cursor 连续翻页

这不是性能问题，而是服务端不保证稳定语义，可能导致：

- 漏数据
- 重复数据
- 顺序不稳定
- 批量处理结果不可控

### 3. 回查标记与批量处理

涉及 `filters` 或 `sort` 的批量处理，必须使用回查标记方式推进：

1. 查询第一页
2. 处理当前返回记录
3. 回写辅助标记字段
4. 下一轮继续查询未标记记录

辅助标记字段必须用于避免重复读取和模拟稳定分页。Agent 可以自动新增，示例字段名：

- `处理标记`
- `查询标记`
- `同步标记`
- `回查标记`
- `AI处理标记`

辅助字段只用于避免重复读取和模拟稳定分页，不应承载业务含义。

### 4. `filters` 字段规则

`filters` 必须使用 `fieldId`，不能直接使用字段名称，例如 `商品ID`、`日期`、`店铺`。

正确流程是：

1. 先读取字段列表
2. 找到字段名称对应的 `fieldId`
3. 用 `fieldId` 构造过滤条件

### 5. 单选 / 多选过滤规则

`singleSelect` / `multipleSelect` 过滤必须使用 option id，不能直接传选项名称。

正确流程是：

1. 读取字段 schema
2. 找到选项名称对应的 option id
3. 用 option id 构造过滤条件

### 6. 图片 / 附件字段默认不查

查询记录时，默认只返回非图片 / 非附件字段。

查询前先通过字段列表识别：

- attachment 字段
- 图片字段
- 截图字段
- 凭证字段
- 其他大附件字段

如果当前 MCP schema 支持指定返回字段，则只传入非图片 / 非附件字段的 `fieldId`。

如果当前 MCP schema 不支持指定返回字段，则查询后只使用非图片 / 非附件字段，并在必要时提示图片 / 附件字段可能导致查询变慢。

### 7. 日期过滤规则

日期过滤优先按日期维度处理，不要依赖小时 / 分钟 / 秒级服务端过滤完成复杂批量任务。

涉及复杂时间判断时，优先查询较小范围，再在 Agent 侧判断。

## 必须遵守的附件规则

### 1. 可靠附件写入流程

附件可靠写入必须使用：

1. `prepare_attachment_upload`
2. 使用返回的 `uploadUrl` 上传文件
3. 将返回或准备好的 `fileToken` 写入附件字段

### 2. 不要依赖外链 URL

直接写外链 URL 属于 best-effort 异步链路，不保证立即可读，也不保证稳定成功。

生产任务优先使用 `fileToken`。

### 3. 附件更新会覆盖字段

`update_records` 更新附件字段时，会整体覆盖该字段原有附件。

如果要追加附件，必须：

1. 先读取原附件值
2. 合并旧附件和新附件
3. 一起写回

禁止在未合并旧附件的情况下直接写新附件，避免误删已有附件。

## 配置与调用约定

- 默认使用当前 agent workspace 里的 `mcporter` 注册名 `dingtalk-ai-table`
- 如果需要直连兜底，请使用可选变量 `DINGTALK_AI_TABLE_DIRECT_URL`
- 主示例统一使用 `mcporter call dingtalk-ai-table <tool_name> ...`
- 复杂参数一律用 `--args '<json>'`

## 常用工具集

### 常用数据操作工具

- `get_tables`
- `get_fields`
- `query_records`
- `create_records`
- `update_records`
- `delete_records`
- `prepare_attachment_upload`

### 低频管理工具

- `list_bases`
- `search_bases`
- `get_base`
- `create_base`
- `update_base`
- `delete_base`
- `search_templates`
- `create_table`
- `update_table`
- `delete_table`
- `create_fields`
- `update_field`
- `delete_field`

## 常规流程

1. 先 `mcporter list dingtalk-ai-table --schema`，确认当前 schema 是新版。
2. 再 `get_base` / `get_tables` 读取结构。
3. 构造过滤条件前，必须先把字段名转换为 `fieldId`。
4. `singleSelect / multipleSelect` 过滤时必须传 option id。
5. 查询用 `query_records`：无 `filters`、无 `sort` 的普通大量读取可以使用 `cursor` 连续翻页；涉及 `filters` 或 `sort` 的批量处理，必须用“第一页 -> 处理 -> 回写辅助标记字段 -> 查未标记”。
6. 用户未明确要求图片 / 附件字段时，默认排除图片 / 附件字段。
7. 附件先 `prepare_attachment_upload`，再上传文件，最后写 `fileToken`。

## 脚本

### 批量新增字段

```bash
python3 bulk_add_fields.py <baseId> <tableId> fields.json
```

`fields.json` 示例：

```json
[
  {"fieldName":"任务名","type":"text"},
  {"fieldName":"优先级","type":"singleSelect","config":{"options":[{"name":"高"},{"name":"中"},{"name":"低"}]}}
]
```

### 批量导入记录

```bash
python3 import_records.py <baseId> <tableId> data.csv
python3 import_records.py <baseId> <tableId> data.json 50
```

说明：

- CSV 表头默认按 `fieldId` 解释
- JSON 支持：
  - `[{"cells": {...}}]`
  - `[{"fld_xxx": "value"}]`

## 安全规则

- 文件路径受 `OPENCLAW_WORKSPACE` 沙箱限制
- 仅允许读取工作区内 `.json` / `.csv` 文件
- Base / Table / Field / Record ID 都做格式校验
- 批量上限按 MCP server 实际限制控制：
  - `create_fields`：最多 15
  - `get_tables / get_fields`：最多 10
  - `create_records / update_records / delete_records`：最多 100

## 调试原则

- 先 `get_base`，再 `get_tables`，必要时 `get_fields`
- 不要猜 `fieldId`
- 构造过滤条件前，必须先把字段名转换为 `fieldId`
- 不要依赖排序 + 过滤 + 翻页、排序 + 翻页、过滤 + 翻页做全量遍历
- 无 `filters`、无 `sort` 的普通大量读取可以使用 `cursor`
- 涉及 `filters` 或 `sort` 的批量处理，必须使用“第一页 + 处理 + 回写辅助标记字段 + 查未标记”的方式推进
- 用户没有要求图片时，默认排除图片 / 附件字段
- 复杂参数一律用 `--args` JSON
- `singleSelect / multipleSelect` 过滤时必须传 option ID，不是 option name

## 参考

- API 参考：`references/api-reference.md`
- 错误排查：`references/error-codes.md`
- 快速开始补充：`docs/getting-started.md`
