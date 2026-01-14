#!/bin/bash
# 蓝绿部署脚本
# Blue-Green Deployment Script

set -e

echo "🚀 开始蓝绿部署 / Starting Blue-Green Deployment"

# 颜色定义 / Color definitions
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查当前环境状态
# Check current environment state
CURRENT_ENV=$(docker-compose ps api | grep -o "blue\|green" || echo "blue")

if [ "$CURRENT_ENV" == "blue" ]; then
    NEW_ENV="green"
    OLD_ENV="blue"
else
    NEW_ENV="blue"
    OLD_ENV="green"
fi

echo -e "${BLUE}当前环境 / Current Environment: ${CURRENT_ENV}${NC}"
echo -e "${GREEN}新环境 / New Environment: ${NEW_ENV}${NC}"

# 启动新环境
# Start new environment
echo -e "${YELLOW}启动新环境服务 / Starting new environment services...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.${NEW_ENV}.yml up -d --build

# 等待新环境就绪
# Wait for new environment to be ready
echo -e "${YELLOW}等待新环境就绪 / Waiting for new environment to be ready...${NC}"
sleep 10

# 健康检查
# Health check
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 新环境健康检查通过 / New environment health check passed${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}等待健康检查... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ 新环境健康检查失败 / New environment health check failed${NC}"
    exit 1
fi

# 切换流量（通过更新nginx配置或docker-compose服务标签）
# Switch traffic (by updating nginx config or docker-compose service labels)
echo -e "${YELLOW}切换流量到新环境 / Switching traffic to new environment...${NC}"

# 这里简化处理：直接更新环境变量并重启服务
# Simplified: directly update environment variable and restart service
export DEPLOYMENT_PHASE="blue-green"
docker-compose restart api

echo -e "${GREEN}✅ 蓝绿部署完成 / Blue-Green Deployment Completed${NC}"
echo -e "${BLUE}新环境: ${NEW_ENV}${NC}"
echo -e "${YELLOW}旧环境: ${OLD_ENV} (可手动清理)${NC}"
