# ChangeLens: A Comparative Study of Deployment Strategies for Performance Regression Detection

**Author**: [Your Name]  
**Institution**: [Your Institution]  
**Date**: [Date]  
**Version**: 1.0

---

## 1. Motivation

Performance regressions in cloud-native microservices can lead to degraded user experience, increased error rates, and potential revenue loss. While automated deployment strategies like Blue-Green and Canary deployments are widely adopted, there is limited empirical evidence comparing their effectiveness in detecting and mitigating performance regressions.

**Research Question**: How do Blue-Green and Canary deployment strategies differ in their ability to detect performance regressions and minimize user impact?

**Contributions**:
- A reproducible benchmark (ChangeLens) for studying deployment regression detection
- Empirical comparison of Blue-Green vs. Canary strategies across multiple regression types
- Quantitative metrics: Time-to-Detection (TTD), Recovery Time, and Impact Scope

---

## 2. Experimental Setup

### 2.1 System Architecture

ChangeLens consists of a minimal microservice architecture:
- **API v1**: Baseline service without regressions
- **API v2**: Service with controlled regression injection (CPU, DB, downstream)
- **PostgreSQL**: Persistent storage
- **Downstream Service**: Simulates external dependency with configurable latency/errors
- **k6 Load Generator**: Generates controlled traffic and implements deployment routing

### 2.2 Controlled Regressions

Three types of controlled regressions are injected:

1. **CPU Regression**: Lock contention and CPU-bound busy-wait loops (~50-70ms per request)
2. **Database Regression**: Missing index on `user_id` column, forcing full table scans
3. **Downstream Regression**: Increased latency spikes (200ms) and error rate (15%)

### 2.3 Deployment Strategies

**Blue-Green Deployment**:
- T=120s: Instant 100% traffic switch from v1 to v2
- Characteristics: Fast deployment, all-or-nothing approach

**Canary Deployment**:
- T=120s: 5% traffic to v2
- T=180s: 25% traffic to v2
- T=240s: 100% traffic to v2
- Characteristics: Gradual rollout, early detection capability

### 2.4 Rollback Mechanism

Automated rollback is triggered when **both** conditions are met for **2 consecutive windows** (10s each):
- P99 Latency > 500ms **OR** Error Rate > 5%

### 2.5 Experimental Design

- **Scenarios**: 2 deployment strategies (Blue-Green, Canary)
- **Regression Types**: 3 types (CPU, DB, Downstream)
- **Runs per Scenario**: 10 runs with different random seeds (base seed: 42)
- **Load**: 10 concurrent virtual users, 10-minute test duration (60s warmup + 540s main)
- **Metrics Aggregation**: 10-second windows

**Total Experiments**: 2 × 3 × 10 = 60 runs

---

## 3. Metrics

### 3.1 Primary Metrics

- **P99 Latency**: 99th percentile request latency per time window
- **Error Rate**: Percentage of non-2xx responses per window
- **Time-to-Detection (TTD)**: Time from deployment start to rollback trigger
- **Recovery Time**: Time from rollback to metrics returning to baseline
- **Impact Scope**: Percentage of traffic/users affected before rollback

### 3.2 Statistical Analysis

- **Confidence Intervals**: 95% bootstrap CI (percentile method, 1000 bootstrap samples)
- **Effect Size**: Cliff's Delta for non-parametric comparison between strategies
- **Aggregation**: Mean ± standard deviation with 95% CI across runs

---

## 4. Results

### 4.1 Performance Metrics

**P99 Latency** (mean ± SD, 95% CI):
- Canary: [X] ± [Y] ms [[lower], [upper]]
- Blue-Green: [X] ± [Y] ms [[lower], [upper]]

**Error Rate** (mean ± SD, 95% CI):
- Canary: [X] ± [Y]% [[lower], [upper]]
- Blue-Green: [X] ± [Y]% [[lower], [upper]]

### 4.2 Detection and Recovery

**Time-to-Detection (TTD)**:
- Canary: [X] ± [Y] seconds [[lower], [upper]]
- Blue-Green: [X] ± [Y] seconds [[lower], [upper]]

**Recovery Time**:
- Canary: [X] ± [Y] seconds [[lower], [upper]]
- Blue-Green: [X] ± [Y] seconds [[lower], [upper]]

### 4.3 Impact Scope

**Traffic Affected Before Rollback**:
- Canary: [X]% ± [Y]% [[lower], [upper]]
- Blue-Green: 100% (all traffic switched at once)

**Effect Size (Cliff's Delta)**:
- P99 Latency: [X] (interpretation: [negligible/small/medium/large])
- Error Rate: [X] (interpretation: [negligible/small/medium/large])
- TTD: [X] (interpretation: [negligible/small/medium/large])

### 4.4 Key Findings

1. **Detection Speed**: [Describe which strategy detects regressions faster]
2. **Impact Mitigation**: Canary deployment limits impact to [X]% of traffic before rollback, compared to 100% for Blue-Green
3. **Recovery Characteristics**: [Describe recovery time differences]
4. **Regression Type Sensitivity**: [Describe how different regression types affect detection]

---

## 5. Discussion

### 5.1 Trade-offs

**Blue-Green Deployment**:
- **Advantages**: Fast deployment, simple implementation, instant rollback
- **Disadvantages**: Higher risk if regressions exist, all users affected immediately

**Canary Deployment**:
- **Advantages**: Early detection, gradual rollout, limited impact scope
- **Disadvantages**: Slower deployment, more complex routing logic, potential for partial degradation

### 5.2 Implications for Practice

1. **For High-Stakes Deployments**: Canary deployment provides better protection against regressions
2. **For Fast Iteration**: Blue-Green deployment enables rapid deployment but requires robust testing
3. **Rollback Thresholds**: Adaptive thresholds based on baseline characteristics may improve detection accuracy

### 5.3 Limitations

See "Threats to Validity" section in README.md for detailed discussion of:
- External validity (synthetic benchmark, limited regression types, single-machine environment)
- Internal validity (load generation model, metric aggregation windows, rollback thresholds)
- Construct validity (deployment strategy implementation, performance metrics)
- Reproducibility (environment dependencies, random seed effects)

---

## 6. Threats to Validity

### 6.1 External Validity

- **Synthetic Benchmark**: Results based on minimal microservice architecture may not generalize to production systems
- **Limited Regression Types**: Three controlled regression scenarios may not capture all failure modes
- **Single-Machine Environment**: Docker-based deployment differs from distributed production environments

### 6.2 Internal Validity

- **Load Generation Model**: k6's virtual user model may not perfectly represent real user behavior
- **Metric Aggregation Windows**: 10-second windows provide a balance but may miss rapid changes
- **Rollback Thresholds**: Fixed thresholds may not be optimal for all scenarios

### 6.3 Construct Validity

- **Deployment Strategy Implementation**: Simplified Blue-Green and Canary implementations may not reflect real-world complexity
- **Performance Metrics**: P99 latency and error rate are common but may not capture all important aspects

---

## 7. Future Work

1. **Adaptive Thresholds**: Develop rollback thresholds that adapt to baseline characteristics
2. **Additional Regression Types**: Expand to include memory leaks, network partitions, cascading failures
3. **Multi-Node Deployment**: Evaluate strategies in distributed environments with network latency
4. **Cost Analysis**: Compare resource costs and deployment time between strategies
5. **Integration with Observability**: Use OpenTelemetry for distributed tracing and root cause analysis

---

## 8. Reproducibility

All experiments were conducted with:
- Fixed random seeds (42-51) for deterministic behavior
- Docker containerization for consistent environments
- Complete configuration capture (git commit, docker images, environment variables)
- Configuration files saved in `results/run_*/config.json`

**To Reproduce**:
1. Ensure Docker services are running: `docker compose up -d`
2. Run experiment suite: `.\scripts\run_research_suite.ps1 -NRuns 10`
3. View aggregated results: `results/experiment_*/aggregated_results.json`
4. Generate summary report: `results/experiment_*/summary.md`

---

## References

1. Gan, Y., et al. "An Open-Source Benchmark Suite for Microservices and Their Hardware-Software Implications for Cloud & Edge Systems." SOSP 2019.
2. Zhou, X., et al. "TrainTicket: A Microservice Benchmark Suite." ICSE 2021.
3. [Add other relevant references]

---

**Appendix**: Detailed results, configuration files, and additional plots are available in the `results/` directory of the ChangeLens repository.
