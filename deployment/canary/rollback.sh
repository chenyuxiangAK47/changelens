#!/bin/bash
# 金丝雀部署回滚脚本
# Canary Deployment Rollback Script

set -e

echo "⏪ 开始金丝雀部署回滚 / Starting Canary Deployment Rollback"

# 颜色定义 / Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 逐步减少金丝雀流量到0
# Gradually reduce canary traffic to 0
STAGES=("100" "25" "5" "0")
STAGE_NAMES=("100%" "25%" "5%" "0%")

for i in "${!STAGES[@]}"; do
    PERCENTAGE=${STAGES[$i]}
    STAGE_NAME=${STAGE_NAMES[$i]}
    
    echo -e "${YELLOW}回滚阶段: 流量 ${STAGE_NAME} / Rollback Stage: Traffic ${STAGE_NAME}${NC}"
    
    export CANARY_TRAFFIC_PERCENT=${PERCENTAGE}
    
    if [ "$PERCENTAGE" == "0" ]; then
        export DEPLOYMENT_PHASE="baseline"
        # 停止金丝雀版本
        # Stop canary version
        docker-compose -f docker-compose.canary.yml down
    else
        export DEPLOYMENT_PHASE="canary-rollback-${STAGE_NAME}"
    fi
    
    docker-compose restart api
    sleep 5
done

# 健康检查
# Health check
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 回滚成功 / Rollback Successful${NC}"
    echo -e "${GREEN}当前流量: 0% (已回滚到基线版本) / Current Traffic: 0% (rolled back to baseline)${NC}"
else
    echo -e "${RED}❌ 回滚后健康检查失败 / Health check failed after rollback${NC}"
    exit 1
fi
