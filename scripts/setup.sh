#!/bin/bash
# ChangeLens 项目设置脚本
# ChangeLens Project Setup Script

set -e

echo "🔧 ChangeLens 项目设置 / ChangeLens Project Setup"
echo "=========================================="

# 检查Docker
# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker / Docker not installed, please install Docker first"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose / Docker Compose not installed, please install Docker Compose first"
    exit 1
fi

# 检查k6
# Check k6
if ! command -v k6 &> /dev/null; then
    echo "⚠️  k6未安装 / k6 not installed"
    echo "   安装k6: https://k6.io/docs/getting-started/installation/"
    echo "   Install k6: https://k6.io/docs/getting-started/installation/"
fi

# 检查Python
# Check Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python未安装，请先安装Python 3.9+ / Python not installed, please install Python 3.9+"
    exit 1
fi

# 安装Python依赖
# Install Python dependencies
echo "安装Python依赖 / Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "❌ pip未找到 / pip not found"
    exit 1
fi

# 创建必要的目录
# Create necessary directories
echo "创建目录 / Creating directories..."
mkdir -p results/data results/charts

# 构建Docker镜像
# Build Docker images
echo "构建Docker镜像 / Building Docker images..."
docker-compose build

echo ""
echo "✅ 设置完成 / Setup completed!"
echo ""
echo "下一步 / Next steps:"
echo "1. 启动服务: docker-compose up -d"
echo "   Start services: docker-compose up -d"
echo "2. 检查服务: curl http://localhost:8000/health"
echo "   Check services: curl http://localhost:8000/health"
echo "3. 运行实验: bash scripts/run_experiment.sh"
echo "   Run experiment: bash scripts/run_experiment.sh"
