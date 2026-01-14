# ChangeLens 系统架构文档
# ChangeLens System Architecture Documentation

## 概述 / Overview

ChangeLens 是一个可复现的云原生微服务基准测试平台，用于研究 CI/CD 变更如何引发尾延迟（P99）和错误率回归，并评估蓝绿部署/金丝雀发布策略以及自动回滚机制。

ChangeLens is a reproducible cloud-native microservices benchmark that studies how CI/CD changes trigger tail latency (P99) and error rate regressions, while evaluating blue-green/canary deployment strategies and automatic rollback mechanisms.

## 系统架构图 / System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        负载测试层                                 │
│                      Load Testing Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │   k6     │  │  Locust  │  │  Custom  │                      │
│  │ Baseline │  │          │  │  Scripts │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
└───────┼──────────────┼──────────────┼────────────────────────────┘
        │              │              │
        └──────────────┴──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │      API Service             │
        │    (FastAPI - Port 8000)     │
        │  ┌────────────────────────┐  │
        │  │  Regression Injector   │  │
        │  │  - CPU Regression      │  │
        │  │  - DB Regression       │  │
        │  │  - Dependency Reg.    │  │
        │  └────────────────────────┘  │
        └───────┬──────────────┬───────┘
                │              │
        ┌───────▼──────┐  ┌────▼──────────┐
        │   Worker     │  │   PostgreSQL   │
        │  Service     │  │   Database     │
        │ (Port 8001)  │  │   (Port 5432)  │
        └──────────────┘  └────────────────┘
                │
        ┌───────▼──────┐
        │    Redis     │
        │  (Optional)  │
        │  (Port 6379) │
        └──────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      监控和指标收集层                            │
│                  Monitoring & Metrics Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Metrics    │  │   Chart      │  │   Rollback   │          │
│  │  Collector   │  │  Generator   │  │   Detector   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件 / Core Components

### 1. API Service (FastAPI)

**职责 / Responsibilities**:
- 提供RESTful API端点
- 处理数据查询和任务提交
- 注入性能回归（CPU、数据库、依赖）
- 暴露性能指标

**主要端点 / Main Endpoints**:
- `GET /health` - 健康检查
- `GET /api/data` - 获取数据（触发DB查询）
- `POST /api/process` - 提交任务到Worker
- `GET /api/metrics` - 获取当前性能指标
- `POST /api/regression/{type}` - 注入回归
- `POST /api/metrics/reset` - 重置指标

### 2. Worker Service

**职责 / Responsibilities**:
- 处理来自API的异步任务
- 模拟后台工作（数据处理、外部调用）
- 支持长时间运行的任务

**主要端点 / Main Endpoints**:
- `GET /health` - 健康检查
- `POST /api/tasks` - 接收并处理任务
- `GET /api/tasks/{task_id}` - 获取任务结果

### 3. PostgreSQL Database

**职责 / Responsibilities**:
- 存储应用数据
- 支持有/无索引的性能测试
- 存储性能指标历史数据

**主要表 / Main Tables**:
- `items` - 测试数据表
- `metrics` - 性能指标历史表

### 4. Redis (可选)

**职责 / Responsibilities**:
- 缓存数据
- 任务队列
- 任务结果存储

## 回归注入机制 / Regression Injection Mechanism

### CPU回归 / CPU Regression

通过额外计算和锁竞争模拟CPU瓶颈：
- 执行大量循环计算
- 模拟锁竞争（定期sleep）
- 可配置强度（循环次数）

### 数据库回归 / DB Regression

通过慢查询模拟数据库瓶颈：
- 执行复杂计算（模拟慢查询）
- 模拟数据库I/O延迟
- 可配置强度（查询复杂度）

### 下游依赖回归 / Dependency Regression

模拟外部服务调用变慢或超时：
- 注入网络延迟
- 随机超时（5%概率）
- 可配置延迟时间

## 部署策略 / Deployment Strategies

### 蓝绿部署 / Blue-Green Deployment

- **原理**: 维护两个完全相同的环境（blue和green）
- **流程**: 
  1. 在新环境部署新版本
  2. 健康检查通过后切换流量
  3. 旧环境保留用于快速回滚
- **优势**: 零停机时间，快速回滚
- **劣势**: 需要双倍资源

### 金丝雀部署 / Canary Deployment

- **原理**: 逐步将流量从旧版本迁移到新版本
- **流程**:
  1. 启动金丝雀版本
  2. 5%流量 → 25%流量 → 100%流量
  3. 每个阶段观察指标
  4. 如有问题立即回滚
- **优势**: 风险最小化，资源效率高
- **劣势**: 部署时间较长

## 回滚机制 / Rollback Mechanism

### 回滚触发条件 / Rollback Trigger Conditions

1. **P99延迟阈值**: P99延迟超过基线1.5倍
2. **错误率阈值**: 错误率超过5%

### 回滚检测流程 / Rollback Detection Flow

```
持续监控指标
    ↓
检查P99和错误率
    ↓
超过阈值？
    ↓ 是
触发回滚脚本
    ↓
切换流量回旧版本
    ↓
验证健康状态
```

## 指标收集和可视化 / Metrics Collection & Visualization

### 收集的指标 / Collected Metrics

- **P50延迟**: 50%请求的延迟
- **P95延迟**: 95%请求的延迟
- **P99延迟**: 99%请求的延迟（尾延迟）
- **错误率**: 失败请求的百分比
- **请求计数**: 总请求数

### 可视化图表 / Visualization Charts

1. **P99延迟 vs 时间**: 显示尾延迟随时间的变化，标注部署阶段和回滚点
2. **错误率 vs 时间**: 显示错误率随时间的变化，标注部署阶段和回滚点

## 技术栈 / Tech Stack

- **API框架**: FastAPI (Python 3.11)
- **Worker框架**: FastAPI (Python 3.11)
- **数据库**: PostgreSQL 15
- **缓存/队列**: Redis 7
- **负载测试**: k6
- **容器编排**: Docker Compose
- **数据可视化**: Matplotlib, Plotly
- **数据处理**: Pandas

## 数据流 / Data Flow

### 正常请求流 / Normal Request Flow

```
Load Test → API Service → Database
                ↓
            Worker Service
                ↓
            Redis (optional)
```

### 指标收集流 / Metrics Collection Flow

```
API Service (metrics endpoint)
        ↓
Metrics Collector (Python script)
        ↓
CSV File Storage
        ↓
Chart Generator
        ↓
PNG Charts
```

### 回滚检测流 / Rollback Detection Flow

```
Metrics Collector
        ↓
Rollback Detector
        ↓
Threshold Check
        ↓
Rollback Script Execution
        ↓
Traffic Switch
```

## 扩展性 / Scalability

### 2周原型版本 / 2-Week Prototype

- 简单的指标收集（Python脚本）
- 基本的图表生成
- 简化的部署脚本

### 8周完整版本 / 8-Week Full Version

- Prometheus + Grafana集成
- OpenTelemetry分布式追踪
- Kubernetes部署清单
- 故障注入框架（Chaos Engineering）
- 噪声邻居实验
- 智能回滚阈值（变更感知、负载感知）

## 安全考虑 / Security Considerations

- 所有服务运行在Docker容器中，提供隔离
- 数据库密码通过环境变量配置
- API端点可以添加认证（未来增强）
- 生产环境应使用TLS/HTTPS

## 性能考虑 / Performance Considerations

- 数据库连接池优化
- Redis缓存减少数据库负载
- 异步任务处理提高吞吐量
- 负载测试可配置以模拟不同场景

## 故障处理 / Failure Handling

- 健康检查确保服务可用性
- 自动回滚机制响应性能回归
- 错误日志记录便于调试
- 优雅降级（服务不可用时返回错误）

---

*Last Updated: 2024*
