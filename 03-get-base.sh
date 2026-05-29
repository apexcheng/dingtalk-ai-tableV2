#!/bin/bash
# 示例 3：查看 Base 内的表

BASE_ID="${1}"

if [ -z "$BASE_ID" ]; then
  echo "❌ 用法：$0 <baseId>"
  exit 1
fi

echo "📊 查看 Base 内的表..."
if [ -n "${DINGTALK_MCP_URL:-}" ]; then
  mcporter call "$DINGTALK_MCP_URL" .get_base baseId="$BASE_ID"
else
  mcporter call dingtalk-ai-table get_base baseId="$BASE_ID"
fi
