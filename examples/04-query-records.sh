#!/bin/bash
# 示例 4：查询记录

BASE_ID="${1}"
TABLE_ID="${2}"
LIMIT="${3:-100}"

if [ -z "$BASE_ID" ] || [ -z "$TABLE_ID" ]; then
  echo "❌ 用法：$0 <baseId> <tableId> [limit]"
  exit 1
fi

echo "🔍 查询记录..."
if [ -n "${DINGTALK_AI_TABLE_DIRECT_URL:-}" ]; then
  mcporter call "$DINGTALK_AI_TABLE_DIRECT_URL" .query_records \
    --args "{\"baseId\":\"$BASE_ID\",\"tableId\":\"$TABLE_ID\",\"limit\":$LIMIT}"
else
  mcporter call dingtalk-ai-table query_records \
    --args "{\"baseId\":\"$BASE_ID\",\"tableId\":\"$TABLE_ID\",\"limit\":$LIMIT}"
fi
