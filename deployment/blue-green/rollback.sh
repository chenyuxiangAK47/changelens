#!/bin/bash
# 蓝绿部署回滚脚本
# Blue-Green Deployment Rollback Script

set -e

echo "⏪ 开始蓝绿部署回滚 / Starting Blue-Green Deployment Rollback"

# 颜色定义 / Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查当前环境
# Check current environment
CURRENT_ENV=$(docker-compose ps api | grep -o "blue\|green" || echo "blue")

if [ "$CURRENT_ENV" == "blue" ]; then
    ROLLBACK_ENV="green"
else
    ROLLBACK_ENV="blue"
fi

echo -e "${YELLOW}当前环境 / Current Environment: ${CURRENT_ENV}${NC}"
echo -e "${GREEN}回滚到环境 / Rollback to Environment: ${ROLLBACK_ENV}${NC}"

# 切换回旧环境
# Switch back to old environment
echo -e "${YELLOW}切换流量回旧环境 / Switching traffic back to old environment...${NC}"

export DEPLOYMENT_PHASE="baseline"
docker-compose restart api

# 等待服务就绪
# Wait for service to be ready
sleep 5

# 健康检查
# Health check
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 回滚成功 / Rollback Successful${NC}"
    echo -e "${GREEN}当前环境: ${ROLLBACK_ENV}${NC}"
else
    echo -e "${RED}❌ 回滚后健康检查失败 / Health check failed after rollback${NC}"
    exit 1
fi
