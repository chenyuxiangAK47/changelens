# ChangeLens 14天开发计划
# ChangeLens 14-Day Development Plan

## 总体目标 / Overall Goals

在14天内完成ChangeLens项目的2周原型版本，包括：
- 完整的微服务架构（API、Worker、DB）
- 三种回归注入类型
- 两种部署策略（蓝绿、金丝雀）
- 自动回滚机制
- 性能指标收集和可视化
- 完整的实验流程

## 每日任务清单 / Daily Task Checklist

### Phase 1: Days 1-3 - 基础设置 / Foundation Setup

#### Day 1: 项目结构和基础服务 / Project Structure & Basic Services

- [x] 创建项目目录结构
- [x] 设置FastAPI服务（基本端点、健康检查）
- [x] 设置Worker服务（后台任务处理）
- [x] 设置PostgreSQL数据库（简单schema）
- [x] 创建docker-compose.yml（所有服务）
- [x] 验证基础健康检查

**交付物 / Deliverables**:
- 项目目录结构完整
- 所有服务可以启动并响应健康检查

#### Day 2: 数据库和基础集成 / Database & Basic Integration

- [x] 实现API → DB交互（CRUD操作）
- [x] 实现API → Worker异步任务提交
- [x] 添加Redis（可选）用于缓存/队列
- [x] 测试端到端流程：API → DB → Worker

**交付物 / Deliverables**:
- 完整的服务间通信
- 端到端流程测试通过

#### Day 3: 负载测试设置 / Load Testing Setup

- [x] 设置k6负载测试脚本
- [x] 配置基线负载（持续RPS）
- [x] 集成指标收集（简单Python脚本收集P50/P95/P99 + 错误率）
- [x] 生成第一个基线指标图表

**交付物 / Deliverables**:
- k6基线负载测试脚本
- 指标收集脚本
- 第一个基线性能图表

### Phase 2: Days 4-7 - 回归注入 / Regression Injection

#### Day 4: CPU回归 / CPU Regression

- [x] 实现CPU回归注入器（额外计算、锁竞争）
- [x] 添加功能开关启用/禁用CPU回归
- [x] 测试CPU回归对延迟的影响

**交付物 / Deliverables**:
- CPU回归注入功能
- CPU回归影响验证

#### Day 5: 数据库回归 / DB Regression

- [x] 实现数据库回归（慢查询、缺失索引）
- [x] 添加功能开关用于数据库回归
- [x] 测试数据库回归影响

**交付物 / Deliverables**:
- 数据库回归注入功能
- 数据库回归影响验证

#### Day 6: 下游依赖回归 / Downstream Dependency Regression

- [x] 实现依赖回归（模拟外部调用变慢/超时）
- [x] 添加功能开关用于依赖回归
- [x] 测试依赖回归影响

**交付物 / Deliverables**:
- 依赖回归注入功能
- 依赖回归影响验证

#### Day 7: 回归测试和验证 / Regression Testing & Validation

- [x] 独立测试所有三种回归类型
- [x] 验证指标收集能够捕获回归
- [x] 优化回归强度（使其可测量但不会灾难性）

**交付物 / Deliverables**:
- 所有回归类型测试通过
- 回归强度调优完成

### Phase 3: Days 8-11 - 部署策略 / Deployment Strategies

#### Day 8: 蓝绿部署 / Blue-Green Deployment

- [x] 实现蓝绿部署脚本
- [x] 设置流量切换机制（nginx/envoy或docker-compose服务标签）
- [x] 测试蓝绿部署流程

**交付物 / Deliverables**:
- 蓝绿部署脚本
- 流量切换机制工作正常

#### Day 9: 金丝雀部署 / Canary Deployment

- [x] 实现金丝雀部署（5% → 25% → 100%流量分割）
- [x] 设置流量分割（nginx/envoy加权路由）
- [x] 测试金丝雀部署流程

**交付物 / Deliverables**:
- 金丝雀部署脚本
- 流量分割机制工作正常

#### Day 10: 回滚逻辑 / Rollback Logic

- [x] 实现回滚检测（P99阈值、错误率阈值）
- [x] 为两种策略创建回滚脚本
- [x] 测试自动回滚触发

**交付物 / Deliverables**:
- 回滚检测逻辑
- 自动回滚功能验证

#### Day 11: 集成测试 / Integration Testing

- [x] 测试完整流程：部署 → 回归注入 → 回滚
- [x] 验证回滚正确触发
- [x] 优化阈值

**交付物 / Deliverables**:
- 完整流程测试通过
- 回滚机制验证完成

### Phase 4: Days 12-14 - 可视化和文档 / Visualization & Documentation

#### Day 12: 图表生成 / Chart Generation

- [x] 实现图表生成脚本（matplotlib/plotly）
- [x] 生成P99延迟 vs 时间图表（标注部署阶段、回滚点）
- [x] 生成错误率 vs 时间图表（标注）

**交付物 / Deliverables**:
- 图表生成脚本
- 两个主要图表（P99延迟、错误率）

#### Day 13: 结果分析和摘要 / Results Analysis & Summary

- [x] 运行完整实验：基线 → 部署 → 回归 → 回滚
- [x] 生成带正确标注的两个图表
- [x] 编写1页摘要文档（结果、洞察、未来工作）

**交付物 / Deliverables**:
- 完整实验数据
- 两个标注图表
- 1页摘要文档

#### Day 14: 文档和RA邮件准备 / Documentation & RA Email Prep

- [x] 完成README.md（设置说明）
- [x] 编写架构文档
- [x] 创建RA邮件模板（个性化简历亮点）
- [x] 准备repo分享（清理、文档化、可运行）

**交付物 / Deliverables**:
- 完整的README.md
- 架构文档
- RA邮件模板
- 可分享的代码仓库

## 关键里程碑 / Key Milestones

- **Day 3**: 基础系统运行，可以收集基线指标
- **Day 7**: 所有回归类型实现并测试
- **Day 11**: 部署和回滚机制完整
- **Day 14**: 完整原型就绪，可以开始RA申请

## 风险缓解 / Risk Mitigation

- **服务启动问题**: 提前测试docker-compose配置
- **指标收集延迟**: 使用简单方法先实现，后续优化
- **部署脚本复杂性**: 先实现简化版本，逐步完善
- **图表生成问题**: 使用成熟的库（matplotlib），参考示例

## 成功标准 / Success Criteria

- [x] 所有服务可以正常启动和通信
- [x] 三种回归类型都可以注入并观察到影响
- [x] 两种部署策略都可以执行
- [x] 自动回滚可以在阈值触发时工作
- [x] 可以生成两个带标注的图表
- [x] 有完整的文档和README

## 下一步（8周版本）/ Next Steps (8-Week Version)

- 故障注入框架（Chaos Engineering）
- 噪声邻居实验（资源争抢）
- 更智能的回滚阈值（变更感知、负载感知）
- OpenTelemetry分布式追踪用于根因归因
- Kubernetes部署清单
- Prometheus + Grafana集成
- 学术论文草稿准备

---

*此清单用于跟踪14天原型开发进度 / This checklist tracks progress for the 14-day prototype development*
