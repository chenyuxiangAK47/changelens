# ChangeLens: A Cloud-Native Microservice Benchmark

**Research Question**: How do Blue-Green and Canary deployment strategies compare in detecting and mitigating performance regressions in cloud-native microservices?

## Methodology

ChangeLens is a reproducible microservice benchmark with controlled regression injection (CPU, DB, downstream) and automated rollback mechanisms. We compare Blue-Green (instant 100% cutover) vs. Canary (gradual 5%→25%→100% rollout) deployments using statistical analysis (N≥3 runs, 95% bootstrap CI, effect size).

## Key Findings

1. **Canary deployment** achieves **3x lower error rate** (0.02% vs 0.06%) compared to Blue-Green, demonstrating better error containment during gradual rollout, despite slightly higher P99 latency (446ms vs 430ms).

2. **ML-enhanced early warning**: XGBoost model achieves **33% early detection rate** (30+ seconds in advance) with **0% false positive rate** (ROC-AUC 0.75, PR-AUC 0.71), enabling proactive rollback decisions.

3. **Error rate shows larger effect size** (Cohen's d = 2.35) than P99 latency (Cohen's d = -0.86) when comparing deployment strategies, suggesting error rate may be a more discriminative metric for regression detection.

## How to Reproduce

```powershell
# 1. Setup environment
.\scripts\setup_venv.ps1
.\venv\Scripts\Activate.ps1

# 2. Start services
docker compose up -d

# 3. Run research suite
.\scripts\run_research_suite.ps1 -NRuns 10
```

**Repository**: https://github.com/chenyuxiangAK47/changelens  
**Demo Results**: See `results/demo/` for sample outputs

---

*ChangeLens v0.1.0 | MIT License | Designed for reproducible research*
