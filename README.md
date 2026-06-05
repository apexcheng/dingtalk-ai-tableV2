# dingtalk-ai-table 使用说明

本仓库面向 OpenClaw 多 agent + per-agent `mcporter.json` 场景。
`SKILL.md` 里写的是必须遵守的核心规则，这里只保留快速上手、命令示例和补充说明。

## Python 安全调用层

仓库内已提供 `dingtalk_ai_table/` Python 安全调用层，用来统一封装
`mcporter call dingtalk-ai-table ...`。

高风险调用优先走 Python safe client，不要让 Agent 直接手拼 MCP 参数，尤其是：

- `query_records` 的 `limit / filters / sort / cursor`
- 批量 `create_records / update_records / delete_records`
- `create_fields / get_tables / get_fields` 的批量上限
- `查询标记` 分页推进
- 附件上传与附件合并写回

现有脚本 `bulk_add_fields.py`、`import_records.py` 已改为调用这一层。

面向业务场景的现成 helper 也已提供，例如：

- `dingtalk_ai_table.markers.query_with_marker`
- `dingtalk_ai_table.markers.query_date_range_with_marker`

其中 `query_date_range_with_marker` 会强制：

- 按天拆分日期范围
- 每天只使用 `date_eq`
- 每天内部使用 `查询标记` 推进
- 不回退到 `cursor`

如果是 OpenClaw skill 直接调用，优先使用包根导出的最小入口函数集合：

- `resolve_field_id`
- `resolve_option_id`
- `safe_query_records`
- `safe_create_records`
- `safe_update_records`
- `safe_delete_records`
- `process_records_with_marker`
- `process_date_range_with_marker`
- `safe_prepare_attachment_upload`

## 快速上手

```bash
mcporter list dingtalk-ai-table --schema
mcporter call dingtalk-ai-table list_bases limit=5
mcporter call dingtalk-ai-table get_base baseId='base_xxx'
mcporter call dingtalk-ai-table query_records --args '{"baseId":"base_xxx","tableId":"tbl_xxx","limit":100}'
```

如果当前环境没有注册 `dingtalk-ai-table`，可以作为高级兜底改用：

```bash
export DINGTALK_AI_TABLE_DIRECT_URL='<your-mcp-server-url>'
mcporter call "$DINGTALK_AI_TABLE_DIRECT_URL" .list_bases limit=10
```

## 示例数据文件

### `fields.json` - 批量新增字段示例

```json
[
  {
    "fieldName": "任务名",
    "type": "text"
  },
  {
    "fieldName": "优先级",
    "type": "singleSelect",
    "config": {
      "options": [
        {"name": "高"},
        {"name": "中"},
        {"name": "低"}
      ]
    }
  },
  {
    "fieldName": "截止日期",
    "type": "date"
  },
  {
    "fieldName": "负责人",
    "type": "user",
    "config": {
      "multiple": false
    }
  },
  {
    "fieldName": "进度",
    "type": "progress"
  }
]
```

### `data.csv` - 批量导入记录示例

```csv
fld_name,fld_age,fld_status,fld_salary
张三,25,进行中,15000
李四,30,已完成,18000
王五,28,进行中,16000
```

### `data.json` - JSON 格式导入示例

```json
[
  {
    "cells": {
      "fld_name": "张三",
      "fld_age": 25,
      "fld_status": "进行中",
      "fld_salary": 15000
    }
  },
  {
    "cells": {
      "fld_name": "李四",
      "fld_age": 30,
      "fld_status": "已完成",
      "fld_salary": 18000
    }
  }
]
```

## 批量脚本用法

```bash
python3 bulk_add_fields.py base_xxx tbl_xxx fields.json
python3 import_records.py base_xxx tbl_xxx data.csv
python3 import_records.py base_xxx tbl_xxx data.json 50
```

## 字段类型参考

| 类型 | 说明 | 示例 |
|------|------|------|
| `text` | 文本 | `"张三"` |
| `number` | 数字 | `25` |
| `singleSelect` | 单选 | `{"name":"高"}` |
| `multipleSelect` | 多选 | `[{"name":"高"},{"name":"紧急"}]` |
| `date` | 日期 | `"2026-03-31"` |
| `user` | 用户 | `{"id":"user_xxx"}` |
| `checkbox` | 复选框 | `true` |
| `attachment` | 附件 | `[{"fileToken":"ft_xxx"}]` |
| `url` | 链接 | `{"text":"官网","link":"https://..."}` |
| `richText` | 富文本 | `{"markdown":"**加粗**"}` |

附件字段推荐使用 `fileToken`；如需保留已有附件，先从 `query_records` 读取原始附件对象，再原样合并回传。
