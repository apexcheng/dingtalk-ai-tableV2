---
name: dingtalk-ai-table
description: OpenClaw 调用钉钉 AI 表格 MCP 的安全调用层。Agent 不直接手拼 mcporter 参数，而是优先调用 dingtalk_ai_table 包导出的 Python 函数，由 Python 层完成参数校验、字段 ID 解析、选项 ID 解析、记录增删改查、过滤构造、查询标记分页和附件上传前置。MCP URL 由 MCPORTER_CONFIG 或当前工作目录 config/mcporter.json 隔离配置。
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
8. **MCP URL 只写在 mcporter 配置文件里，不要写死在业务代码里**

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

## 4. MCP URL 配置

本 skill 通过 `mcporter` 调用钉钉 AI 表格 MCP。

MCP URL 不在 Python 业务代码里配置，而是在 mcporter 配置文件里配置。

本项目只使用两层配置优先级：

1. `MCPORTER_CONFIG` 环境变量：显式指定 mcporter 配置文件路径，优先级最高
2. `{cwd}/config/mcporter.json`：当前工作目录下的项目级配置

`cwd` 是当前进程的工作目录。

在 OpenClaw 中，每个 Agent 的 workspace 目录就是它运行时的 `cwd`。因此不同 Agent 可以各自在自己的 workspace 下放置：

```text
config/mcporter.json
```

这样每个 Agent 会读取自己的 mcporter 配置，从而实现 MCP URL 隔离。

### 4.1 推荐方式：项目级配置

在每个 Agent 的 workspace 下创建：

```text
config/mcporter.json
```

例如：

```text
review-analyst/
  config/
    mcporter.json

live-stream-recorder/
  config/
    mcporter.json
```

只要 Agent 的 `cwd` 是自己的 workspace，Python 层会自动把该文件作为 `MCPORTER_CONFIG` 传给 mcporter。

业务调用仍然使用同一个注册名：

```bash
mcporter call dingtalk-ai-table query_records --args "..."
```

真正的 MCP URL 由当前 Agent workspace 下的 `config/mcporter.json` 决定。

### 4.2 显式路径方式：MCPORTER_CONFIG

如果要手动指定配置文件路径，可以设置：

```bash
export MCPORTER_CONFIG="/path/to/mcporter.json"
```

Windows PowerShell：

```powershell
$env:MCPORTER_CONFIG="C:\\path\\to\\mcporter.json"
```

Windows CMD：

```cmd
set MCPORTER_CONFIG=C:\path\to\mcporter.json
```

设置后，Python 层会优先使用这个路径，不再自动找 `{cwd}/config/mcporter.json`。

### 4.3 配置缺失时

如果既没有设置 `MCPORTER_CONFIG`，当前工作目录下也没有 `config/mcporter.json`，Python 层会直接报错。

这是为了避免 Agent 错误地使用全局 mcporter 配置，导致多个 Agent 意外共用同一个 MCP URL。

### 4.4 Agent 判断规则

Agent 遇到 MCP 连接问题时，按这个顺序检查：

1. 当前 Agent 的 `cwd` 是否正确
2. 当前 `cwd` 下是否存在 `config/mcporter.json`
3. 是否显式设置了 `MCPORTER_CONFIG`
4. mcporter 配置里是否存在 `dingtalk-ai-table` 注册名
5. 该注册名是否指向正确的钉钉 AI 表格 MCP Server URL
6. 再检查具体业务参数，如 `base_id`、`table_id`、`fieldId`

不要把 MCP URL 和表格资源 ID 混在一起。

## 5. 推荐导入方式

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

## 6. 函数速查

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

## 7. 基本调用流程

### 7.1 查询记录

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

### 7.2 新增记录

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

### 7.3 更新记录

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

### 7.4 删除记录

删除记录必须提供 `recordId` 数组，单次最多 100 条。

```python
from dingtalk_ai_table import safe_delete_records

result = safe_delete_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    record_ids=["rec_xxxxxxxx"],
)
```

## 8. 过滤条件用法

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

### 8.1 单选 / 多选过滤

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

## 9. 超过 100 条的处理

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

## 10. 日期范围处理

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

## 11. 附件上传前置

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

## 12. 参数和数据格式要求

### 12.1 资源 ID

`base_id`、`table_id`、`field_id`、`record_id` 都必须是合法资源 ID。

不要使用字段名、表名、中文名代替 ID。

### 12.2 records

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

### 12.3 field_ids

如果用户只需要部分字段，传 `field_ids` 限制返回字段，避免无意义拉取大字段。

```python
safe_query_records(
    base_id=base_id,
    table_id=table_id,
    field_ids=[name_field_id, status_field_id],
    limit=100,
)
```

## 13. 硬限制

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

## 14. 禁止行为

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
- 不要在业务代码里硬编码 MCP URL
- 不要把 MCP URL 当成 `base_id` / `table_id`
- 不要为了一个需求扩展成完整 SDK 或复杂 CLI

## 15. mcporter 说明

本项目内部通过 `mcporter` 调用 MCP。

Python 层调用时会先确定 mcporter 配置文件路径：

1. 如果存在 `MCPORTER_CONFIG` 环境变量，使用它指向的配置文件
2. 否则使用 `{cwd}/config/mcporter.json`
3. 如果都没有，直接报错，不使用全局兜底配置

然后统一执行：

```bash
mcporter call dingtalk-ai-table query_records --args "..."
```

`dingtalk-ai-table` 是 mcporter 配置文件里的 MCP Server 注册名。

Agent 正常情况下不需要手写 `mcporter call`。
只有在调试 MCP 注册状态时，才检查：

```bash
mcporter list dingtalk-ai-table --schema
```

业务调用仍然优先走 Python 安全函数。

## 16. 选型规则

### 16.1 用户要查 100 条以内

用 `safe_query_records`。

### 16.2 用户要查带过滤的很多记录

用 `process_records_with_marker`。

### 16.3 用户要查日期范围

用 `process_date_range_with_marker`。

### 16.4 用户要新增 / 更新 / 删除

分别用：

- `safe_create_records`
- `safe_update_records`
- `safe_delete_records`

### 16.5 用户只给字段名

先用 `resolve_field_id`。

### 16.6 用户只给单选 / 多选名称

先用 `resolve_option_id`。

### 16.7 用户要附件字段

先用 `safe_prepare_attachment_upload`，拿到上传信息后再处理文件上传和 fileToken 写入。

### 16.8 用户反馈 MCP 连接失败

先检查：

1. 当前 Agent 的 `cwd` 是否正确
2. 是否存在 `MCPORTER_CONFIG`
3. 当前 `cwd` 下是否存在 `config/mcporter.json`
4. mcporter 配置中是否存在 `dingtalk-ai-table` 注册名
5. 该注册名是否指向正确的钉钉 AI 表格 MCP Server
6. 再检查业务参数

## 17. 最小完整示例

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

## 18. 总原则

优先让 Python 层拦截错误参数。
不要只依赖提示词约束 Agent 行为。
MCP URL 只做连接配置，不参与业务参数构造。
每个 Agent 通过自己的 `cwd/config/mcporter.json` 实现 MCP URL 隔离。
保持实现简单、可读、边界清晰。
除非真实调用中发现 MCP 返回结构变化，否则不要扩大功能范围。
