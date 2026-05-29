#!/bin/bash
# 示例 7：批量新增字段

BASE_ID="${1}"
TABLE_ID="${2}"
FIELDS_FILE="${3}"

if [ -z "$BASE_ID" ] || [ -z "$TABLE_ID" ] || [ -z "$FIELDS_FILE" ]; then
  echo "❌ 用法：$0 <baseId> <tableId> <fields_file>"
  exit 1
fi

echo "🆕 批量新增字段..."
python3 bulk_add_fields.py "$BASE_ID" "$TABLE_ID" "$FIELDS_FILE"
