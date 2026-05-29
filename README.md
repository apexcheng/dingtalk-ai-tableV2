# dingtalk-ai-table 使用说明

本仓库面向 OpenClaw 多 agent + per-agent `mcporter.json` 场景。
`SKILL.md` 里写的是必须遵守的核心规则，这里只保留快速上手、命令示例和补充说明。

## 快速上手

```bash
mcporter list dingtalk-ai-table --schema
mcporter call dingtalk-ai-table list_bases limit=5
mcporter call dingtalk-ai-table get_base baseId='base_xxx'
mcporter call dingtalk-ai-table query_records --args '{"baseId":"base_xxx","tableId":"tbl_xxx","limit":10}'
```

如果当前环境没有注册 `dingtalk-ai-table`，可以作为高级兜底改用：

```bash
export DINGTALK_AI_TABLE_DIRECT_URL='<your-url>'
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
| `attachment` | 附件 | `[{"fileId":"file_xxx"}]` |
| `url` | 链接 | `{"text":"官网","link":"https://..."}` |
| `richText` | 富文本 | `{"markdown":"**加粗**"}` |
