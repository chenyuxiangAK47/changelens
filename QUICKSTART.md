# ChangeLens 快速开始指南
# ChangeLens Quick Start Guide

## 5分钟快速启动 / 5-Minute Quick Start

### 步骤1: 前置要求检查 / Step 1: Prerequisites Check

确保已安装以下工具 / Ensure the following tools are installed:

```bash
# 检查Docker
docker --version
docker-compose --version

# 检查Python (3.9+)
python --version

# 检查k6 (可选，用于负载测试)
k6 version
```

### 步骤2: 安装依赖 / Step 2: Install Dependencies

```bash
# 进入项目目录
cd D:\ChangeLens

# 安装Python依赖
pip install -r requirements.txt
```

### 步骤3: 启动服务 / Step 3: Start Services

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 等待服务就绪（约30秒）
# Wait for services to be ready (about 30 seconds)
```

### 步骤4: 验证服务 / Step 4: Verify Services

```bash
# 检查API服务健康状态
curl http://localhost:8000/health

# 检查Worker服务健康状态
curl http://localhost:8001/health

# 预期输出 / Expected output:
# {"status":"healthy","timestamp":"...","service":"changelens-api"}
```

### 步骤5: 运行简单测试 / Step 5: Run Simple Test

```bash
# 测试数据获取端点
curl http://localhost:8000/api/data

# 测试任务处理端点
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{"task_id": "test_001", "data": {"test": "data"}}'

# 查看当前指标
curl http://localhost:8000/api/metrics
```

## 运行完整实验 / Run Complete Experiment

### 方法1: 使用实验脚本 / Method 1: Using Experiment Script

```bash
# 运行完整实验（蓝绿部署）
bash scripts/run_experiment.sh blue-green

# 或运行金丝雀部署实验
bash scripts/run_experiment.sh canary
```

### 方法2: 手动步骤 / Method 2: Manual Steps

#### 1. 启动指标收集 / Start Metrics Collection

```bash
# 在后台启动指标收集
python monitoring/scripts/collect_metrics.py --interval 5 --duration 300 &
```

#### 2. 运行基线负载测试 / Run Baseline Load Test

```bash
k6 run load-testing/k6/baseline.js
```

#### 3. 注入回归 / Inject Regression

```bash
# 注入CPU回归
bash scripts/inject_regression.sh cpu true

# 或注入数据库回归
bash scripts/inject_regression.sh db true

# 或注入依赖回归
bash scripts/inject_regression.sh dependency true
```

#### 4. 运行回归负载测试 / Run Regression Load Test

```bash
k6 run load-testing/k6/regression.js
```

#### 5. 生成图表 / Generate Charts

```bash
# 生成图表（使用最新的数据文件）
python monitoring/scripts/generate_charts.py

# 或指定数据文件
python monitoring/scripts/generate_charts.py --data results/data/metrics_YYYYMMDD_HHMMSS.csv
```

#### 6. 分析结果 / Analyze Results

```bash
# 生成1页摘要
python scripts/analyze_results.py

# 或指定数据文件
python scripts/analyze_results.py --data results/data/metrics_YYYYMMDD_HHMMSS.csv
```

## 查看结果 / View Results

实验结果将保存在以下位置 / Experiment results will be saved in:

- **指标数据**: `results/data/metrics_*.csv`
- **图表**: `results/charts/p99_latency_vs_time_*.png` 和 `error_rate_vs_time_*.png`
- **摘要**: `results/summary.md`

## 常见问题 / Common Issues

### 问题1: 服务无法启动 / Services Won't Start

```bash
# 检查端口是否被占用
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# 查看Docker日志
docker-compose logs api
docker-compose logs worker
docker-compose logs postgres
```

### 问题2: 数据库连接失败 / Database Connection Failed

```bash
# 检查PostgreSQL是否运行
docker-compose ps postgres

# 重启PostgreSQL
docker-compose restart postgres
```

### 问题3: 指标收集失败 / Metrics Collection Failed

```bash
# 确保API服务运行
curl http://localhost:8000/health

# 检查API服务日志
docker-compose logs api
```

### 问题4: 图表生成失败 / Chart Generation Failed

```bash
# 确保数据文件存在
ls results/data/

# 检查Python依赖
pip list | grep matplotlib
pip list | grep pandas
```

## 下一步 / Next Steps

1. **阅读架构文档**: `docs/architecture.md`
2. **查看开发计划**: `docs/day1-14-checklist.md`
3. **准备RA申请**: `docs/ra-email-template.md`
4. **自定义实验**: 修改回归强度、部署策略等参数

## 获取帮助 / Get Help

- 查看完整文档: `README.md`
- 查看架构文档: `docs/architecture.md`
- 检查GitHub Issues（如果项目已发布）

---

*Happy Experimenting! / 祝实验顺利！*
