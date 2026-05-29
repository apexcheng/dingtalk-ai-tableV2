# 快速开始补充

这里是补充示例，不是核心规则来源。核心约束以仓库根目录的 `SKILL.md` 为准。

## 常见命令

```bash
mcporter list dingtalk-ai-table --schema
mcporter call dingtalk-ai-table list_bases limit=10
mcporter call dingtalk-ai-table search_bases query='销售'
mcporter call dingtalk-ai-table get_base baseId='base_xxx'
mcporter call dingtalk-ai-table get_tables \
  --args '{"baseId":"base_xxx","tableIds":["tbl_xxx"]}'
mcporter call dingtalk-ai-table get_fields \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","fieldIds":["fld_xxx"]}'
```

## 常见写入

```bash
mcporter call dingtalk-ai-table create_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","records":[{"cells":{"fld_name":"张三"}}]}'

mcporter call dingtalk-ai-table update_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","records":[{"recordId":"rec_xxx","cells":{"fld_name":"王五"}}]}'

mcporter call dingtalk-ai-table delete_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","recordIds":["rec_xxx","rec_yyy"]}'
```

## 批量脚本

```bash
python3 bulk_add_fields.py base_xxx tbl_xxx fields.json
python3 import_records.py base_xxx tbl_xxx data.csv
```

## 可选直连

如果当前环境没有注册 `dingtalk-ai-table`，可以改用直连 URL：

```bash
export DINGTALK_AI_TABLE_DIRECT_URL='<your-url>'
mcporter call "$DINGTALK_AI_TABLE_DIRECT_URL" .list_bases limit=10
```

## 更多参考

- API 参考：`references/api-reference.md`
- 错误排查：`references/error-codes.md`
- 详细说明：`README.md`
