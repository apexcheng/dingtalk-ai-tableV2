# dingtalk-ai-tableV2

钉钉 AI 表格 MCP 的 **OpenClaw 安全调用层**。

这个项目不是通用 SDK，也不是完整 CLI 工具集。  
它的作用是：让 OpenClaw / Agent 通过 Python 函数安全地调用钉钉 AI 表格 MCP，并把容易出错的规则硬写进代码里。

---

## 这个项目解决什么问题

钉钉 AI 表格 MCP 有一些调用边界需要严格遵守，例如：

- `query_records` 单次最多只能查 `100` 条
- 有 `filters` 或 `sort` 时不能继续用 `cursor`
- 过滤字段必须使用 `fieldId`，不能用字段名
- `create_records / update_records` 的 `cells` key 必须是 `fieldId`
- 日期范围查询不能直接用 `gte / lte`，需要按天拆成 `date_eq`
- 超过 100 条且带过滤 / 排序时，需要用 `查询标记` 推进分页

这些规则如果只写在提示词里，Agent 仍然可能执行错。  
所以本项目把这些边界写进 Python 函数里，让错误参数在本地就被拦住。

---

## 项目定位

本项目只做三件事：

1. 封装 `mcporter call dingtalk-ai-table`
2. 提供 OpenClaw 可直接调用的安全函数
3. 对高风险参数做硬校验

不做这些事：

- 不实现钉钉 AI 表格服务端
- 不做完整 SDK
- 不做复杂 CLI
- 不做批量导入工具
- 不自动解析字段名写入记录
- 不绕过 MCP 的服务端限制

---

## 运行前提

需要当前环境已安装：

```bash
mcporter
python3
```

并且 `mcporter` 中已经注册了钉钉 AI 表格 MCP：

```bash
mcporter call dingtalk-ai-table ...
```

默认情况下，本项目会调用：

```bash
mcporter call dingtalk-ai-table
```

如果当前环境没有注册名，也可以用环境变量兜底：

```bash
export DINGTALK_AI_TABLE_DIRECT_URL="你的 MCP Server URL"
```

---

## OpenClaw 推荐入口

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

---

## 函数说明

| 函数 | 用途 |
|---|---|
| `resolve_field_id` | 根据字段名查 `fieldId` |
| `resolve_option_id` | 根据单选 / 多选选项名查 option id |
| `safe_query_records` | 安全查询记录 |
| `safe_create_records` | 安全新增记录 |
| `safe_update_records` | 安全更新记录 |
| `safe_delete_records` | 安全删除记录 |
| `process_records_with_marker` | 带过滤 / 排序时，用 `查询标记` 稳定处理超过 100 条记录 |
| `process_date_range_with_marker` | 日期范围按天拆分，并用 `查询标记` 稳定处理 |
| `safe_prepare_attachment_upload` | 附件上传前置，获取上传信息 |

---

## 最小查询示例

```python
from dingtalk_ai_table import safe_query_records

result = safe_query_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    limit=100,
)

print(result)
```

注意：

- `limit` 最大只能是 `100`
- 不传 `limit` 时默认也是 `100`

---

## 根据字段名查询 fieldId

Agent 不应该直接猜 `fieldId`。  
如果只知道字段名，先解析：

```python
from dingtalk_ai_table import resolve_field_id

status_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="状态",
)

print(status_field_id)
```

---

## 新增记录

新增记录时，`cells` 的 key 必须是 `fieldId`，不能是字段名。

正确：

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

print(result)
```

错误：

```python
safe_create_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    records=[
        {
            "cells": {
                "姓名": "张三",
            }
        }
    ],
)
```

上面这种会被 Python 层拦截，因为 `"姓名"` 不是合法 `fieldId`。

---

## 更新记录

更新记录必须提供 `recordId`，并且 `cells` 里的 key 也必须是 `fieldId`。

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

print(result)
```

---

## 删除记录

```python
from dingtalk_ai_table import safe_delete_records

result = safe_delete_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    record_ids=[
        "rec_xxxxxxxx",
    ],
)

print(result)
```

单次最多删除 `100` 条。

---

## 带过滤查询

过滤字段必须使用 `fieldId`。

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
    limit=100,
)

print(result)
```

支持的过滤操作：

```text
eq
ne
date_eq
```

不支持：

```text
gte
lte
greater_equal
less_than
is_after
is_before
```

---

## 日期查询

日期字段只允许使用 `date_eq`，日期格式必须是：

```text
YYYY-MM-DD
```

示例：

```python
from dingtalk_ai_table import resolve_field_id, safe_query_records
from dingtalk_ai_table.filters import date_eq_filter

date_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="创建日期",
)

filters = date_eq_filter(date_field_id, "2026-06-05")

result = safe_query_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    filters=filters,
    limit=100,
)

print(result)
```

日期范围不要直接用 `gte / lte`。  
需要按天拆分，推荐用 `process_date_range_with_marker`。

---

## 超过 100 条记录的稳定处理

如果查询场景包含 `filters` 或 `sort`，不能用 `cursor` 翻页。  
需要使用 `查询标记` 字段推进。

示例：

```python
from dingtalk_ai_table import process_records_with_marker, resolve_field_id
from dingtalk_ai_table.filters import eq_filter

status_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="状态",
)

filters = eq_filter(status_field_id, "待处理")


def handle_batch(records):
    print(f"本批处理 {len(records)} 条")
    # 在这里处理业务逻辑


task_marker = process_records_with_marker(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    filters=filters,
    process_batch=handle_batch,
    task_name="handle_pending_records",
)

print(task_marker)
```

这个函数会：

1. 自动创建或复用 `查询标记` 字段
2. 每次查询最多 `100` 条
3. 处理完一批后写入本次任务标记
4. 继续查询未处理记录
5. 直到没有新记录

注意：这个流程会写入表格中的 `查询标记` 字段。

---

## 日期范围批量处理

```python
from dingtalk_ai_table import process_date_range_with_marker, resolve_field_id

date_field_id = resolve_field_id(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    field_name="创建日期",
)


def handle_batch(records):
    print(f"本批处理 {len(records)} 条")


results = process_date_range_with_marker(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    date_field_id=date_field_id,
    start_date="2026-06-01",
    end_date="2026-06-07",
    process_batch=handle_batch,
    task_name="handle_date_range",
)

print(results)
```

这个函数会把日期范围拆成：

```text
2026-06-01
2026-06-02
2026-06-03
...
2026-06-07
```

然后每天单独用 `date_eq` 查询，并在每天内部使用 `查询标记` 推进。

---

## 附件上传前置

附件写入需要先获取上传信息：

```python
from dingtalk_ai_table import safe_prepare_attachment_upload

result = safe_prepare_attachment_upload(
    base_id="base_xxxxxxxx",
    file_name="example.png",
    size=123456,
    mime_type="image/png",
)

print(result)
```

拿到上传信息后，再按 MCP 返回的 `uploadUrl` 上传文件，最后把 `fileToken` 写入附件字段。

注意：

- 附件字段更新通常是整体覆盖，不是追加
- 如果要保留旧附件，需要先读取旧附件，再合并后一起写回

---

## 硬限制

本项目会主动拦截以下错误：

| 场景 | 限制 |
|---|---|
| 查询数量 | `query_records.limit <= 100` |
| 批量新增记录 | 单次最多 `100` 条 |
| 批量更新记录 | 单次最多 `100` 条 |
| 批量删除记录 | 单次最多 `100` 条 |
| 批量建字段 | 单次最多 `15` 个字段 |
| 获取表信息 | 单次最多 `10` 个 table |
| 获取字段信息 | 单次最多 `10` 个 field |
| 过滤字段 | 必须使用 `fieldId` |
| 写入记录 | `cells` 的 key 必须是 `fieldId` |
| 过滤结构 | 必须是对象，不能是数组 |
| 过滤语法 | 禁止 `filterType` |
| 分页 | 有 `filters` 或 `sort` 时禁止传 `cursor` |
| 日期 | 只允许 `YYYY-MM-DD` |
| 查询标记字段 | 只能叫 `查询标记` |

---

## 常见错误

### 1. 使用字段名写入记录

错误：

```python
{"cells": {"状态": "已完成"}}
```

正确：

```python
{"cells": {"fld_xxxxxxxx": "已完成"}}
```

字段名需要先用 `resolve_field_id` 转成 `fieldId`。

---

### 2. 带 filters 时继续传 cursor

错误：

```python
safe_query_records(
    base_id="base_xxxxxxxx",
    table_id="tbl_xxxxxxxx",
    filters=filters,
    cursor="next_cursor",
)
```

正确做法：

- 100 条以内：只查一次
- 超过 100 条：用 `process_records_with_marker`

---

### 3. 日期范围直接用 gte / lte

错误：

```python
{
    "operator": "gte",
    "operands": [date_field_id, "2026-06-01"]
}
```

正确：

- 单日查询用 `date_eq`
- 日期范围用 `process_date_range_with_marker`

---

## 测试

运行：

```bash
python3 -B -m unittest -v
```

---

## 适合的使用方式

适合：

- OpenClaw Agent 调用钉钉 AI 表格
- 批量查询记录
- 批量新增 / 更新 / 删除记录
- 带过滤条件处理记录
- 日期范围分批处理
- 附件上传前置
- 防止 Agent 误用 MCP 参数

不适合：

- 做完整钉钉 AI 表格 SDK
- 做通用数据导入工具
- 让 Agent 自己拼复杂 MCP 参数
- 大量无边界地读取表格
- 绕过 MCP 服务端限制

---

## 推荐调用原则

1. 先用 `resolve_field_id` 找字段 ID
2. 再用 `fieldId` 构造查询或写入数据
3. 普通查询用 `safe_query_records`
4. 带过滤 / 排序且可能超过 100 条时，用 `process_records_with_marker`
5. 日期范围用 `process_date_range_with_marker`
6. 不要手写 `cursor` 分页逻辑
7. 不要用字段名直接写入 `cells`
8. 不要把这个项目当完整 SDK 扩展

---

## 项目状态

当前版本重点是稳定、安全、低维护。

后续除非真实调用中遇到 MCP 返回结构变化，否则不建议继续扩大功能范围。
