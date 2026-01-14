#!/bin/bash
# 完整实验运行脚本
# Complete Experiment Run Script

set -e

echo "🧪 ChangeLens 完整实验 / ChangeLens Complete Experiment"
echo "=========================================="

# 颜色定义 / Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查服务是否运行
# Check if services are running
echo -e "${YELLOW}检查服务状态 / Checking service status...${NC}"
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API服务未运行，请先启动服务 / API service not running, please start services first${NC}"
    echo "   运行: docker-compose up -d / Run: docker-compose up -d"
    exit 1
fi

# 创建结果目录
# Create results directory
RESULTS_DIR="$(pwd)/results/data"
CHARTS_DIR="$(pwd)/results/charts"
mkdir -p "$RESULTS_DIR" "$CHARTS_DIR"

# 生成时间戳
# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
METRICS_FILE="${RESULTS_DIR}/experiment_${TIMESTAMP}.csv"

echo -e "${GREEN}✅ 服务运行正常 / Services running normally${NC}"
echo ""

# 阶段1: 基线测试
# Phase 1: Baseline Test
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}阶段 1: 基线测试 / Phase 1: Baseline Test${NC}"
echo -e "${BLUE}========================================${NC}"

# 重置指标
# Reset metrics
echo "重置指标 / Resetting metrics..."
curl -X POST http://localhost:8000/api/metrics/reset > /dev/null 2>&1

# 启动指标收集（后台）
# Start metrics collection (background)
echo "启动指标收集 / Starting metrics collection..."
python monitoring/scripts/collect_metrics.py --output "$METRICS_FILE" --interval 5 --duration 120 &
COLLECTOR_PID=$!

# 运行基线负载测试
# Run baseline load test
echo "运行基线负载测试 / Running baseline load test..."
k6 run load-testing/k6/baseline.js --quiet || true

# 等待指标收集完成
# Wait for metrics collection to complete
wait $COLLECTOR_PID 2>/dev/null || true

echo -e "${GREEN}✅ 基线测试完成 / Baseline test completed${NC}"
echo ""

# 阶段2: 部署 + 回归注入
# Phase 2: Deployment + Regression Injection
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}阶段 2: 部署 + 回归注入 / Phase 2: Deployment + Regression Injection${NC}"
echo -e "${BLUE}========================================${NC}"

# 选择部署策略
# Select deployment strategy
STRATEGY="${1:-blue-green}"  # blue-green or canary
echo "部署策略 / Deployment Strategy: ${STRATEGY}"

# 执行部署
# Execute deployment
if [ "$STRATEGY" == "blue-green" ]; then
    bash deployment/blue-green/deploy.sh
elif [ "$STRATEGY" == "canary" ]; then
    bash deployment/canary/deploy.sh
fi

# 等待部署稳定
# Wait for deployment to stabilize
sleep 10

# 注入回归（CPU回归）
# Inject regression (CPU regression)
echo "注入CPU回归 / Injecting CPU regression..."
bash scripts/inject_regression.sh cpu true

# 启动指标收集（后台）
# Start metrics collection (background)
python monitoring/scripts/collect_metrics.py --output "$METRICS_FILE" --interval 5 --duration 180 &
COLLECTOR_PID=$!

# 运行回归负载测试
# Run regression load test
echo "运行回归负载测试 / Running regression load test..."
k6 run load-testing/k6/regression.js --quiet || true

# 等待指标收集完成
# Wait for metrics collection to complete
wait $COLLECTOR_PID 2>/dev/null || true

echo -e "${GREEN}✅ 回归测试完成 / Regression test completed${NC}"
echo ""

# 阶段3: 回滚检测和触发
# Phase 3: Rollback Detection and Trigger
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}阶段 3: 回滚检测和触发 / Phase 3: Rollback Detection and Trigger${NC}"
echo -e "${BLUE}========================================${NC}"

# 启动回滚检测器（后台）
# Start rollback detector (background)
echo "启动回滚检测器 / Starting rollback detector..."
python scripts/rollback_detector.py --strategy "$STRATEGY" --interval 5 --duration 60 &
DETECTOR_PID=$!

# 等待回滚检测
# Wait for rollback detection
wait $DETECTOR_PID 2>/dev/null || true

echo -e "${GREEN}✅ 回滚检测完成 / Rollback detection completed${NC}"
echo ""

# 阶段4: 生成图表
# Phase 4: Generate Charts
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}阶段 4: 生成图表 / Phase 4: Generate Charts${NC}"
echo -e "${BLUE}========================================${NC}"

echo "生成图表 / Generating charts..."
python monitoring/scripts/generate_charts.py --data "$METRICS_FILE"

echo -e "${GREEN}✅ 图表生成完成 / Charts generated${NC}"
echo ""

# 实验总结
# Experiment Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 实验完成 / Experiment Completed${NC}"
echo -e "${BLUE}========================================${NC}"
echo "指标数据文件 / Metrics Data File: $METRICS_FILE"
echo "图表目录 / Charts Directory: $CHARTS_DIR"
echo ""
echo "查看结果 / View Results:"
echo "  - P99延迟图表: $CHARTS_DIR/p99_latency_vs_time_*.png"
echo "  - 错误率图表: $CHARTS_DIR/error_rate_vs_time_*.png"
