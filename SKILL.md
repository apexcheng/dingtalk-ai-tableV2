---
name: dingtalk-ai-table
description: 钉钉 AI 表格（多维表）操作技能。使用 mcporter CLI 连接钉钉官方新版 AI 表格 MCP server，基于 baseId / tableId / fieldId / recordId 体系执行 Base、Table、Field、Record 的查询与增删改。适用于创建 AI 表格、搜索表格、读取表结构、批量增删改记录、批量建字段、更新字段配置、按模板建表等场景。默认使用当前 agent workspace 的 mcporter 注册名 dingtalk-ai-table，DINGTALK_AI_TABLE_DIRECT_URL 仅作为可选直连兜底。
version: 0.7.2
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

### 1. `query_records` limit 规则

`query_records` 单次 `limit` 最大只能是 `100`。

- 默认 `limit` 应使用 `100`
- 只有在用户明确要求更小数量时，才使用更小的 `limit`
- 禁止尝试 `limit=200` 或任何大于 `100` 的值

### 2. cursor 使用边界

`query_records` 里，`cursor` 不是永远不能用。

| 查询场景 | 是否可以用 cursor 连续翻页 | 严格要求 |
| --- | ---: | --- |
| 无 filters、无 sort，普通读取 | 可以 | cursor 连续读取 |
| 有 filters，无 sort | 禁止 | 第一页 -> 处理 -> 回写“查询标记” -> 查未标记 |
| 无 filters，有 sort | 禁止 | 第一页 -> 处理 -> 回写“查询标记” -> 查未标记 |
| 有 filters、有 sort | 禁止 | 第一页 -> 处理 -> 回写“查询标记” -> 查未标记 |

无 `filters`、无 `sort` 的普通连续读取可以使用 `cursor`，适合普通读取、导出、统计或低风险遍历，只要不依赖排序语义，也不要求复杂过滤后的稳定分页。

只要出现 `filters` 或 `sort` 任意一个，就禁止使用 `cursor` 作为连续翻页机制。

即使 MCP 返回了 `cursor`，也不能继续拿这个 `cursor` 查询下一页，必须改用“查询标记”字段推进。

### 3. 服务端查询限制

只要使用了 `filters` 或 `sort` 任意一种，就不要依赖 `cursor` 连续翻页完成稳定批量处理。

`query_records` 的服务端语义不保证以下方式可用于稳定批量遍历：

- `filters + sort + cursor`
- `sort + cursor`
- `filters + cursor`

这不是性能问题，而是服务端不保证稳定语义，可能导致：

- 漏数据
- 重复数据
- 顺序不稳定
- 批量处理结果不可控

### 4. 回写“查询标记”与批量处理

涉及 `filters` 或 `sort` 的批量处理，必须使用“查询标记”方式推进：

1. 用 `query_records` 且 `limit: 100` 查询第一页
2. 处理当前返回记录
3. 用 `update_records` 回写字段 `查询标记`
4. 下一轮继续查询未标记记录

辅助标记字段固定为 `查询标记`，不要改用其他同级替代名称，避免 Agent 自由发挥。

- 如果表里已有 `查询标记` 字段，直接使用
- 如果没有 `查询标记` 字段，Agent 可以通过 `create_fields` 自动新增
- 自动创建 `查询标记` 字段不影响其他业务字段
- 新增字段类型优先使用 `text`
- 批量分页、去重、清洗、迁移、补写、批量处理时，优先使用 `查询标记` 做回写标记翻页
- 每批处理完成后，必须 `update_records` 回写 `查询标记`
- 下一轮查询时，`filters` 里必须排除已标记记录，只查询 `查询标记` 为空或不等于本次任务标记的记录
- 每次任务必须生成唯一标记值，禁止只写 `已处理`、`done`、`1`、`true`
- 唯一推荐格式：`task_YYYYMMDD_HHMMSS_任务说明`
- 示例：`task_20260529_213000_dedupe_reviews`
- 示例：`task_20260529_220500_export_orders`
- 示例：`task_20260529_230000_fix_notify_status`

这里的“回写 `查询标记`”是技术性分页动作，不等同于更新业务字段。

- 即使任务目标是只查询、只导出、只统计、只去重检查、只生成报告，只要需要在 `filters` 或 `sort` 条件下稳定处理超过 `100` 条数据，仍然可以且应当使用 `查询标记`
- 只查询业务数据，不代表禁止写入辅助字段；`查询标记` 属于辅助字段，不承载业务含义
- Agent 不要因为任务没有新增 / 更新业务字段，就误判为“不能回写 `查询标记`”
- 只有当用户明确要求“绝对只读、禁止任何写入，包括辅助字段”时，才不能使用 `查询标记`；此时应明确提示无法保证 `filters` / `sort` 场景下超过 `100` 条数据的稳定分页处理

短例子：按店铺筛选后导出全部订单，任务本身不修改订单业务字段，但如果结果可能超过 `100` 条，仍应：

1. 查询“符合店铺条件且 `查询标记` 为空”的前 `100` 条
2. 导出这 `100` 条
3. 回写本次任务标记，例如 `task_20260530_101500_export_orders`
4. 继续查询“符合店铺条件且未写本次标记”的前 `100` 条
5. 重复直到返回数量小于 `100`

禁止新增或推荐其他同类辅助字段名，包括但不限于：

- `处理标记`
- `同步标记`
- `回查标记`
- `AI处理标记`

`查询标记` 只用于避免重复读取和模拟稳定分页，不应承载业务含义。

### 5. 返回 `100` 条后的处理规则

`query_records` 单次 `limit` 最大为 `100`，默认也应使用 `100`。

在 `filters` 或 `sort` 场景下，如果本轮 `query_records` 返回数量大于等于 `100`，或等于本轮 `limit`，必须认为可能还有更多记录。

下一批只能通过继续查询“`查询标记` 为空 / 不等于本次任务标记”的记录获取，禁止使用 `cursor` 获取下一页。

如果任务要求处理全量结果，必须严格按以下流程推进：

1. `query_records` 使用 `limit: 100` 查询第一批
2. 处理本批记录
3. 给已处理记录写入 `查询标记`
4. 下一次查询时排除已写入 `查询标记` 的记录
5. 重复直到返回数量小于 `100`

只要带 `filters` 或 `sort` 的查询单轮返回 `100` 条，就必须按上面流程继续处理，不要把这一批误判为“已经查完”，也不要切回 `cursor` 翻页。

### 6. `filters` 字段规则

`filters` 必须使用 MCP/schema 支持的对象结构，并且过滤字段必须使用 `fieldId`，不能直接使用字段名称，例如 `商品ID`、`日期`、`店铺`。

禁止使用以下错误格式：

```json
{
  "baseId": "base_xxx",
  "tableId": "tbl_xxx",
  "filterType": "and",
  "filters": [
    {
      "fieldName": "评价时间",
      "operator": "gte",
      "value": "2026-05-28"
    }
  ],
  "limit": 100
}
```

这是硬性禁止项：

- 禁止使用 `filterType`
- 禁止把 `filters` 写成数组
- 禁止使用 `fieldName` 作为过滤字段
- 禁止 Agent 自行猜测 `gte`、`lte` 等 operator
- `filters` 必须使用 MCP/schema 支持的对象结构
- 过滤字段必须先通过字段列表获取 `fieldId`，再用 `fieldId` 过滤

唯一推荐格式：

```json
{
  "baseId": "base_xxx",
  "tableId": "tbl_xxx",
  "limit": 100,
  "filters": {
    "operator": "and",
    "operands": [
      {
        "operator": "eq",
        "operands": ["fld_xxx", "2026-05-28"]
      }
    ]
  }
}
```

其中 `fld_xxx` 是字段 ID，不是字段名称。

正确流程是：

1. 先读取字段列表
2. 找到字段名称对应的 `fieldId`
3. 用 `fieldId` 构造过滤条件

### 6.1 `filters` operator 使用规则

- 不要猜 operator
- 不要因为常见数据库 API 有 `gte` / `lte`，就直接使用
- 只有在当前 schema、工具说明、服务端错误提示或项目代码里明确支持时，才能使用对应 operator
- 当前仓库内已确认的 `filters` operator 证据只有 `eq` 和 `ne`
- 日期过滤禁止使用区间条件；不要生成 `greater_equal` + `less_than`，也不要生成 `is_after` / `is_before` 这类区间比较思路
- 当前仓库里没有找到 `greater_equal`、`less_than`、`is_after`、`is_before` 的真实支持证据时，不要把它们写成确定可用
- 如果不确定 operator 是否支持，优先使用已确认的 `eq`
- 日期范围查询不要直接猜 `gte` / `lte`
- 日期范围查询唯一推荐方案是按天拆成多次服务端 `eq` 查询，不要默认切成“全量查询 -> 本地筛选”

这是经过当前工具真实支持能力确认后的推荐写法：基于仓库内目前可确认的 `eq` / `ne` 能力，日期范围查询优先按天拆成多次服务端 `eq` 查询。

日期过滤值只传 `yyyy-mm-dd`，不要传完整时间；表格中即使存的是 `yyyy-mm-dd HH:MM:SS`，使用 `yyyy-mm-dd` 也用于匹配当天数据。

示例：查询 `2026-05-27` 到 `2026-05-28` 两天数据时，拆成两次查询。

```json
{
  "baseId": "xxx",
  "tableId": "xxx",
  "limit": 100,
  "filters": {
    "operator": "and",
    "operands": [
      {
        "operator": "eq",
        "operands": ["日期字段ID", "2026-05-27"]
      }
    ]
  }
}
```

```json
{
  "baseId": "xxx",
  "tableId": "xxx",
  "limit": 100,
  "filters": {
    "operator": "and",
    "operands": [
      {
        "operator": "eq",
        "operands": ["日期字段ID", "2026-05-28"]
      }
    ]
  }
}
```

如果单日查询结果达到 `100` 条，继续使用 `查询标记` 回写推进，不能改用 `cursor`。多天范围查询时，每一天都必须按这个规则独立循环处理完成，再进入下一天。

### 7. 单选 / 多选过滤规则

`singleSelect` / `multipleSelect` 过滤必须使用 option id，不能直接传选项名称。

正确流程是：

1. 读取字段 schema
2. 找到选项名称对应的 option id
3. 用 option id 构造过滤条件

### 8. 图片 / 附件字段默认不查

查询记录时，默认只返回非图片 / 非附件字段。

查询前先通过字段列表识别：

- attachment 字段
- 图片字段
- 截图字段
- 凭证字段
- 其他大附件字段

如果当前 MCP schema 支持指定返回字段，则只传入非图片 / 非附件字段的 `fieldId`。

如果当前 MCP schema 不支持指定返回字段，则查询后只使用非图片 / 非附件字段，并在必要时提示图片 / 附件字段可能导致查询变慢。

### 9. 日期过滤规则

日期过滤优先按日期维度处理，不要依赖小时 / 分钟 / 秒级服务端过滤完成复杂批量任务。

过滤查询不允许使用区间条件：

- 不要用 `greater_equal` + `less_than`
- 不要让 Agent 生成日期区间过滤条件
- 不要传完整时间，例如 `2026-05-27 00:00:00`
- 日期过滤值只传 `yyyy-mm-dd`

只有在以下场景才允许本地过滤：

1. 服务端确实不支持该字段或该操作符
2. 已经尝试读取 schema / 工具定义确认无法服务端过滤
3. 数据量很小，且用户明确允许
4. 服务端过滤结果仍需做二次业务判断

禁止默认采用“全量查询 -> 本地筛选”的方案。

应优先使用服务端过滤条件：

- 日期范围优先用服务端日期过滤；如果当前环境未确认范围 operator，则按当前已确认能力拆成多次服务端 `eq`
- 日期范围查询改成按天循环过滤；例如查询 `2025-05-01 ~ 2025-05-05`，应依次过滤 `2025-05-01`、`2025-05-02`、`2025-05-03`、`2025-05-04`、`2025-05-05`
- 状态字段优先用服务端过滤
- 订单号、主播、店铺、型号等条件优先用服务端过滤
- 需要排序时优先使用服务端排序

涉及复杂时间判断时，优先查询较小范围，再在 Agent 侧判断。

按天过滤时，直接使用当天日期值，例如 `2026-05-27`；不要构造 `00:00:00 ~ 次日 00:00:00`，也不要在文档或示例里表达左闭右开区间。

单日查询超过 `100` 条时，不使用 `cursor` 翻页，必须使用 `查询标记` 回写方式继续分页；多天范围查询时，每一天都按这个规则独立循环完成。

错误反例：

```json
[
  {
    "fieldId": "日期字段ID",
    "operator": "is_after",
    "value": "2026-05-27 00:00:00"
  },
  {
    "fieldId": "日期字段ID",
    "operator": "is_before",
    "value": "2026-05-27 00:00:00"
  }
]
```

同一个时间点同时 `after` 和 `before` 会导致结果为空，禁止这样写。当前仓库也没有找到 `is_after` / `is_before` 的真实支持证据，因此不要把这类写法当成可用方案。

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
5. 查询用 `query_records`：单次 `limit` 最大 `100`，默认使用 `100`，除非用户明确要求更小数量。
6. 无 `filters`、无 `sort` 的普通大量读取可以使用 `cursor` 连续翻页；只要涉及 `filters` 或 `sort`，就必须用“第一页 -> 处理 -> 回写 `查询标记` -> 查未标记”，即使 MCP 返回 `cursor` 也不能继续用它翻页。
7. 如果表里没有 `查询标记` 字段，Agent 可以先用 `create_fields` 创建，字段类型优先 `text`。
8. 只查询 / 只导出 / 只统计等任务，如果需要在 `filters` 或 `sort` 条件下稳定处理超过 `100` 条数据，也可以回写 `查询标记`；这属于技术性分页，不等同于修改业务数据。
9. 日期过滤只传 `yyyy-mm-dd`，不要传完整时间，也不要构造左闭右开区间。
10. 日期范围查询一律按天拆成多次服务端 `eq` 查询，不要生成区间条件，不要猜 `greater_equal` / `less_than` / `is_after` / `is_before`。
11. 单日查询达到 `100` 条时，必须在当天范围内使用“查询标记”循环分页，不能使用 `cursor`。
12. 用户未明确要求图片 / 附件字段时，默认排除图片 / 附件字段。
13. 附件先 `prepare_attachment_upload`，再上传文件，最后写 `fileToken`。

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
  - `query_records`：单次最多 100
  - `create_records / update_records / delete_records`：最多 100

## 调试原则

- 先 `get_base`，再 `get_tables`，必要时 `get_fields`
- 不要猜 `fieldId`
- 构造过滤条件前，必须先把字段名转换为 `fieldId`
- `query_records` 默认 `limit=100`，禁止使用大于 `100` 的值
- 禁止默认采用“全量查询 -> 本地筛选”的方案
- 日期、状态、订单号、主播、店铺、型号等条件优先走服务端过滤；需要排序时优先使用服务端排序
- 不要依赖 `filters + sort + cursor`、`sort + cursor`、`filters + cursor` 做全量遍历
- 无 `filters`、无 `sort` 的普通大量读取可以使用 `cursor`
- 涉及 `filters` 或 `sort` 的批量处理，必须使用“第一页 + 处理 + 回写 `查询标记` + 查未标记”的方式推进
- `filters` 或 `sort` 场景下，如果单轮返回大于等于 `100` 条，必须继续查询未标记记录，不能使用 `cursor` 取下一页
- 若缺少 `查询标记` 字段，可先创建该字段，类型优先 `text`
- `查询标记` 固定使用唯一值格式 `task_YYYYMMDD_HHMMSS_任务说明`
- 只查询 / 只导出 / 只统计任务不等于绝对只读；为了稳定分页，仍可回写 `查询标记`，除非用户明确禁止任何辅助字段写入
- `filters` 必须使用对象结构和 `fieldId`；禁止使用 `filterType`、数组 `filters`、`fieldName` 过滤和未确认支持的 `gte` / `lte`
- 日期过滤禁止使用区间条件；只传 `yyyy-mm-dd`，按天拆成多次服务端 `eq` 查询；单日达到 `100` 条时在当天范围内用“查询标记”循环分页，不能使用 `cursor`
- 用户没有要求图片时，默认排除图片 / 附件字段
- 复杂参数一律用 `--args` JSON
- `singleSelect / multipleSelect` 过滤时必须传 option ID，不是 option name

## 参考

- API 参考：`references/api-reference.md`
- 错误排查：`references/error-codes.md`
- 快速开始补充：`docs/getting-started.md`
