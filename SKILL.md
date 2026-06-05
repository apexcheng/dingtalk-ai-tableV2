---
name: dingtalk-ai-table
description: OpenClaw 调用钉钉 AI 表格 MCP 的安全调用层。Agent 不直接手拼 mcporter 参数，而是优先调用 dingtalk_ai_table 包导出的 Python 函数，由 Python 层完成参数校验、字段 ID 解析、选项 ID 解析、记录增删改查、过滤构造、查询标记分页和附件上传前置。
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

# dingtalk-ai-table OpenClaw Skill

这是钉钉 AI 表格 MCP 的 **Python 安全调用层**。

它不是钉钉 AI 表格服务端，不是完整 SDK，也不是通用 CLI 工具。

它的作用是：让 OpenClaw / Agent 通过少量 Python 函数安全地查询、创建、更新、删除钉钉 AI 表格记录，并把容易出错的 MCP 调用规则硬写进 Python 代码里。

## 1. 核心原则

Agent 使用本 skill 时，遵守下面的优先级：

1. **业务调用优先走 Python 函数**，不要手拼 `mcporter call`
2. **字段名先转 fieldId**，不要猜字段 ID
3. **单选 / 多选名称先转 option id**，不要直接用选项名过滤
4. **普通查询最多 100 条**
5. **带 filters 或 sort 且可能超过 100 条时，用查询标记分页**
6. **日期范围不要用 gte / lte，必须按天拆成 date_eq**
7. **写入 cells 时，key 必须是 fieldId，不是字段名**

## 2. 什么时候使用

当用户要求操作钉钉 AI 表格、多维表、Base、Table、Field、Record 时，使用本 skill。

典型任务：

- 查询表格记录
- 新增记录
- 更新记录
- 删除记录
- 根据字段名查 `fieldId`
- 根据单选 / 多选选项名查 option id
- 带过滤条件批量处理记录
- 按日期范围批量处理记录
- 附件上传前获取上传信息

## 3. 什么时候不要使用

不要把本 skill 当成完整 SDK 使用。

不要用它做：

- 通用数据导入工具
- 任意文件处理工具
- 非钉钉 AI 表格任务
- 绕过 MCP 服务端限制
- 让 Agent 自己拼复杂 mcporter 参数
- 在不知道 `base_id` / `table_id` 的情况下盲目调用

## 4. 推荐导入方式

OpenClaw / Agent 优先只调用包根导出的 9 个函数：

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

构造过滤条件时，使用 `dingtalk_ai_table.filters` 里的辅助函数：

```python
from dingtalk_ai_table.filters import (
    eq_filter,
    ne_filter,
    date_eq_filter,
    and_filter,
    or_filter,
)
```

## 5. 函数速查

| 函数 | 用途 | 什么时候用 |
|---|---|---|
| `resolve_field_id(base_id, table_id, field_name)` | 字段名转 `fieldId` | 只知道字段名时先调用 |
| `resolve_option_id(base_id, table_id, field_name, option_name)` | 单选 / 多选选项名转 option id | 过滤单选 / 多选字段前调用 |
| `safe_query_records(...)` | 安全查询记录 | 普通查询，单次最多 100 条 |
| `safe_create_records(base_id, table_id, records)` | 新增记录 | 写入新记录 |
| `safe_update_records(base_id, table_id, records)` | 更新记录 | 已知 `recordId` 时修改记录 |
| `safe_delete_records(base_id, table_id, record_ids)` | 删除记录 | 已知 `recordId` 时删除记录 |
| `process_records_with_marker(...)` | 查询标记分页处理 | 带 filters / sort 且可能超过 100 条 |
| `process_date_range_with_marker(...)` | 日期范围按天处理 | 日期范围查询 / 处理 |
| `safe_prepare_attachment_upload(...)` | 获取附件上传信息 | 写入附件字段前调用 |

## 6. 基本调用流程

### 6.1 查询记录

1. 确认 `base_id` 和 `table_id`
2. 如果需要指定返回字段，先用 `resolve_field_id` 找到字段 ID
3. 如果需要过滤，先构造 filters
4. 调用 `safe_query_records`
5. 不要让 `limit` 超过 100

```python
from dingtalk_ai_table import resolve_field_id, safe_query_records
from dingtalk_ai_table.filters import eq_filter

status_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="状态",
)

filters = eq_filter(status_field_id, "待处理")

result = safe_query_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    filters=filters,
    field_ids=[status_field_id],
    limit=100,
)
```

### 6.2 新增记录

新增记录时，`cells` 的 key 必须是 `fieldId`。

```python
from dingtalk_ai_table import resolve_field_id, safe_create_records

name_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="姓名",
)

result = safe_create_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    records=[
        {
            "cells": {
                name_field_id: "张三",
            }
        }
    ],
)
```

下面这种是错误的：

```python
safe_create_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    records=[{"cells": {"姓名": "张三"}}],
)
```

原因：`"姓名"` 是字段名，不是 `fieldId`。

### 6.3 更新记录

更新记录必须提供 `recordId`，并且 `cells` 的 key 必须是 `fieldId`。

```python
from dingtalk_ai_table import resolve_field_id, safe_update_records

status_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="状态",
)

result = safe_update_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    records=[
        {
            "recordId": "rec_xxxxxxxx",
            "cells": {
                status_field_id: "已完成",
            },
        }
    ],
)
```

### 6.4 删除记录

删除记录必须提供 `recordId` 数组，单次最多 100 条。

```python
from dingtalk_ai_table import safe_delete_records

result = safe_delete_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    record_ids=["rec_xxxxxxxx"],
)
```

## 7. 过滤条件用法

不要手写复杂 filters，优先用辅助函数。

支持的基础过滤：

```python
eq_filter(field_id, value)
ne_filter(field_id, value)
date_eq_filter(field_id, "2026-06-05")
```

支持组合：

```python
and_filter(filter_a, filter_b)
or_filter(filter_a, filter_b)
```

示例：

```python
from dingtalk_ai_table import resolve_field_id, safe_query_records
from dingtalk_ai_table.filters import and_filter, eq_filter, date_eq_filter

status_field_id = resolve_field_id(base_id, table_id, "状态")
date_field_id = resolve_field_id(base_id, table_id, "创建日期")

filters = and_filter(
    eq_filter(status_field_id, "待处理"),
    date_eq_filter(date_field_id, "2026-06-05"),
)

result = safe_query_records(
    base_id=base_id,
    table_id=table_id,
    filters=filters,
    limit=100,
)
```

### 7.1 单选 / 多选过滤

单选 / 多选字段过滤时，过滤值必须使用 option id。

```python
from dingtalk_ai_table import resolve_field_id, resolve_option_id, safe_query_records
from dingtalk_ai_table.filters import eq_filter

status_field_id = resolve_field_id(base_id, table_id, "状态")
pending_option_id = resolve_option_id(base_id, table_id, "状态", "待处理")

filters = eq_filter(status_field_id, pending_option_id)

result = safe_query_records(
    base_id=base_id,
    table_id=table_id,
    filters=filters,
    limit=100,
)
```

## 8. 超过 100 条的处理

`query_records` 单次最多 100 条。

如果没有 `filters` 和 `sort`，可以按 MCP 普通 cursor 分页；但本 skill 的重点不是让 Agent 手写分页。

如果有 `filters` 或 `sort`，禁止传 `cursor`。这类场景如果可能超过 100 条，必须用 `process_records_with_marker`。

```python
from dingtalk_ai_table import process_records_with_marker, resolve_field_id
from dingtalk_ai_table.filters import eq_filter

status_field_id = resolve_field_id(base_id, table_id, "状态")
filters = eq_filter(status_field_id, "待处理")


def handle_batch(records):
    for record in records:
        print(record)


task_marker = process_records_with_marker(
    base_id=base_id,
    table_id=table_id,
    filters=filters,
    process_batch=handle_batch,
    task_name="handle_pending_records",
)
```

注意：

- 这个函数会自动创建或复用 `查询标记` 字段
- 每批最多处理 100 条
- 每处理完一批，会把本次 `task_marker` 写入 `查询标记` 字段
- 它会修改表格数据，因为要写入查询标记
- `readonly=True` 会直接报错，因为 filters / sort 场景下只读无法稳定分页

## 9. 日期范围处理

日期范围不要写 `gte / lte`。

错误：

```python
{"operator": "gte", "operands": [date_field_id, "2026-06-01"]}
```

正确做法：用 `process_date_range_with_marker`，它会把日期范围拆成每天的 `date_eq`。

```python
from dingtalk_ai_table import process_date_range_with_marker, resolve_field_id

created_field_id = resolve_field_id(base_id, table_id, "创建日期")


def handle_batch(records):
    for record in records:
        print(record)


results = process_date_range_with_marker(
    base_id=base_id,
    table_id=table_id,
    date_field_id=created_field_id,
    start_date="2026-06-01",
    end_date="2026-06-07",
    process_batch=handle_batch,
    task_name="handle_created_date",
)
```

返回结果类似：

```python
[
    {"date": "2026-06-01", "taskMarker": "task_..."},
    {"date": "2026-06-02", "taskMarker": "task_..."},
]
```

日期必须是 `YYYY-MM-DD`。

## 10. 附件上传前置

写入附件字段前，先调用 `safe_prepare_attachment_upload` 获取上传信息。

```python
from dingtalk_ai_table import safe_prepare_attachment_upload

upload_info = safe_prepare_attachment_upload(
    base_id="base_xxxxxxxx",
    file_name="example.png",
    size=123456,
    mime_type="image/png",
)
```

拿到 MCP 返回的上传信息后，再按返回的上传地址上传文件，最后把 `fileToken` 写入附件字段。

注意：

- `file_name` 必须包含扩展名
- `size` 必须是大于 0 的整数
- 附件字段更新通常是整体覆盖，不是追加
- 如果要保留旧附件，需要先读取旧附件，再合并后一起写回
- 不要默认查询或返回图片 / 附件字段，除非用户明确需要

## 11. 参数和数据格式要求

### 11.1 资源 ID

`base_id`、`table_id`、`field_id`、`record_id` 都必须是合法资源 ID。

不要使用字段名、表名、中文名代替 ID。

### 11.2 records

新增记录：

```python
records=[
    {
        "cells": {
            "fld_xxxxxxxx": "值",
        }
    }
]
```

更新记录：

```python
records=[
    {
        "recordId": "rec_xxxxxxxx",
        "cells": {
            "fld_xxxxxxxx": "新值",
        },
    }
]
```

### 11.3 field_ids

如果用户只需要部分字段，传 `field_ids` 限制返回字段，避免无意义拉取大字段。

```python
safe_query_records(
    base_id=base_id,
    table_id=table_id,
    field_ids=[name_field_id, status_field_id],
    limit=100,
)
```

## 12. 硬限制

必须遵守：

- `query_records.limit` 最大只能是 `100`
- `query_records` 不传 `limit` 时默认按 `100` 处理
- 只要出现 `filters` 或 `sort`，就禁止传 `cursor`
- `filters` 必须是对象结构，不能是数组
- 禁止使用 `filterType`
- 过滤字段必须使用 `fieldId`，不能使用字段名
- 写入 `cells` 时，key 必须是 `fieldId`
- 基础过滤 operator 只允许：`eq`、`ne`、`date_eq`
- 组合过滤 operator 只允许：`and`、`or`
- 禁止使用：`gte`、`lte`、`greater_equal`、`less_than`、`is_after`、`is_before`
- `date_eq` 只接受 `YYYY-MM-DD`
- 单选 / 多选过滤必须使用 option id
- `create_fields` 单次最多 `15` 个字段
- `get_tables` 单次最多 `10` 个 table
- `get_fields` 单次最多 `10` 个 field
- `create_records` / `update_records` / `delete_records` 单次最多 `100` 条
- `查询标记` 是唯一允许的辅助分页字段名
- 附件可靠写入必须先 `prepare_attachment_upload`

## 13. 禁止行为

Agent 不要做这些事：

- 不要直接猜 `fieldId`
- 不要直接猜 option id
- 不要用字段名写入 `cells`
- 不要手拼复杂 `filters`
- 不要传数组形式的 filters
- 不要使用 `filterType`
- 不要在有 `filters` 或 `sort` 时继续用 `cursor`
- 不要默认全量查询后本地筛选
- 不要生成日期区间过滤条件
- 不要用 `gte / lte` 查询日期范围
- 不要把图片 / 附件字段默认查出来
- 不要绕过 Python 安全函数直接拼 MCP 参数
- 不要为了一个需求扩展成完整 SDK 或复杂 CLI

## 14. mcporter 说明

本项目内部通过 `mcporter call dingtalk-ai-table ...` 调用 MCP。

Agent 正常情况下不需要手写 `mcporter call`。
只有在调试 MCP 注册状态时，才检查：

```bash
mcporter list dingtalk-ai-table --schema
```

如果当前环境没有注册名，可用环境变量兜底：

```bash
export DINGTALK_AI_TABLE_DIRECT_URL="你的 MCP Server URL"
```

但业务调用仍然优先走 Python 安全函数。

## 15. 选型规则

### 15.1 用户要查 100 条以内

用 `safe_query_records`。

### 15.2 用户要查带过滤的很多记录

用 `process_records_with_marker`。

### 15.3 用户要查日期范围

用 `process_date_range_with_marker`。

### 15.4 用户要新增 / 更新 / 删除

分别用：

- `safe_create_records`
- `safe_update_records`
- `safe_delete_records`

### 15.5 用户只给字段名

先用 `resolve_field_id`。

### 15.6 用户只给单选 / 多选名称

先用 `resolve_option_id`。

### 15.7 用户要附件字段

先用 `safe_prepare_attachment_upload`，拿到上传信息后再处理文件上传和 fileToken 写入。

## 16. 最小完整示例

下面是一个“查待处理记录，并更新状态”的完整示例：

```python
from dingtalk_ai_table import (
    resolve_field_id,
    safe_query_records,
    safe_update_records,
)
from dingtalk_ai_table.filters import eq_filter

base_id = "base_xxxxxxxx"
table_id = "tbl_xxxxxxxx"

status_field_id = resolve_field_id(base_id, table_id, "状态")
filters = eq_filter(status_field_id, "待处理")

query_result = safe_query_records(
    base_id=base_id,
    table_id=table_id,
    filters=filters,
    field_ids=[status_field_id],
    limit=100,
)

records = query_result.get("records") or query_result.get("data", {}).get("records") or []

update_records = []
for record in records:
    record_id = record.get("recordId") or record.get("id")
    if record_id:
        update_records.append({
            "recordId": record_id,
            "cells": {
                status_field_id: "已完成",
            },
        })

if update_records:
    safe_update_records(
        base_id=base_id,
        table_id=table_id,
        records=update_records,
    )
```

## 17. 总原则

优先让 Python 层拦截错误参数。
不要只依赖提示词约束 Agent 行为。
保持实现简单、可读、边界清晰。
除非真实调用中发现 MCP 返回结构变化，否则不要扩大功能范围。
