#!/bin/bash
# 回归注入脚本
# Regression Injection Script

set -e

API_URL="http://localhost:8000"
REGRESSION_TYPE="${1:-cpu}"  # cpu, db, dependency
ENABLED="${2:-true}"  # true, false

echo "🔧 注入回归 / Injecting Regression"
echo "   类型 / Type: ${REGRESSION_TYPE}"
echo "   状态 / Status: ${ENABLED}"

# 发送回归注入请求
# Send regression injection request
curl -X POST "${API_URL}/api/regression/${REGRESSION_TYPE}" \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": ${ENABLED}}"

echo ""
echo "✅ 回归注入完成 / Regression injection completed"
