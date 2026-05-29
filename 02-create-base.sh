#!/bin/bash
# 示例 2：创建新 Base

BASE_NAME="${1:-我的项目}"

echo "🆕 创建 Base: $BASE_NAME"
if [ -n "${DINGTALK_MCP_URL:-}" ]; then
  mcporter call "$DINGTALK_MCP_URL" .create_base baseName="$BASE_NAME"
else
  mcporter call dingtalk-ai-table create_base baseName="$BASE_NAME"
fi
