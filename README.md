# ChangeLens: A Cloud-Native Microservice Benchmark for Change-Induced Performance Regressions

## Abstract

ChangeLens is a reproducible microservice benchmark designed to study change-induced performance regressions and evaluate safe deployment strategies (Blue-Green and Canary) with automated rollback mechanisms. This benchmark provides controlled regression scenarios, deterministic testing environments, and automated analysis tools to facilitate research on deployment safety and performance monitoring in cloud-native systems.

## Research Question

**How do different deployment strategies (Blue-Green vs. Canary) perform in detecting and mitigating performance regressions, and what are the trade-offs between deployment speed and system stability?**

This benchmark enables researchers to:
- Quantify the impact of controlled regressions (CPU, database, downstream dependencies) on system performance
- Compare the effectiveness of Blue-Green and Canary deployment strategies
- Evaluate automated rollback mechanisms based on latency and error rate thresholds
- Study the relationship between deployment granularity and regression detection time

## System Architecture

ChangeLens consists of a minimal microservice architecture:

```
┌─────────────┐
│   k6 Load   │
│  Generator  │
└──────┬──────┘
       │
       ├───► API v1 (Baseline)
       │
       └───► API v2 (With Regressions)
              │
              ├───► PostgreSQL
              │
              └───► Downstream Service
```

### Components

1. **API Gateway (v1/v2)**: FastAPI services exposing `/checkout` endpoint
   - **v1**: Baseline implementation without regressions
   - **v2**: Includes controlled regression toggles (CPU, DB, Downstream)

2. **Downstream Service**: Simulates external dependency with configurable latency and error rates

3. **PostgreSQL**: Persistent storage for order data

4. **Redis**: Optional caching layer (included but not actively used in v0.1)

5. **k6 Load Generator**: Generates controlled traffic and implements deployment routing logic

## Controlled Regressions

ChangeLens implements three types of controlled regressions:

### 1. CPU Regression (`REG_CPU=1`)
- **Mechanism**: Lock contention and CPU-bound busy-wait loops
- **Impact**: Increases request processing time by ~50-70ms per request
- **Use Case**: Simulates inefficient algorithms or resource contention

### 2. Database Regression (`REG_DB=1`)
- **Mechanism**: Drops index on `user_id` column, forcing full table scans
- **Impact**: Query latency increases proportionally with table size
- **Use Case**: Simulates missing indexes or inefficient queries

### 3. Downstream Regression (`REG_DOWNSTREAM=1`)
- **Mechanism**: Increased latency spikes (200ms) and error rate (15%)
- **Impact**: Higher P99 latency and increased 5xx error responses
- **Use Case**: Simulates external service degradation

## Deployment Strategies

### Blue-Green Deployment
- **Schedule**: 100% traffic switch from v1 to v2 at T=120s
- **Characteristics**: Instant cutover, all-or-nothing approach
- **Trade-off**: Fast deployment but higher risk if regressions exist

### Canary Deployment
- **Schedule**: 
  - T=120s: 5% traffic to v2
  - T=180s: 25% traffic to v2
  - T=240s: 100% traffic to v2
- **Characteristics**: Gradual rollout, early detection capability
- **Trade-off**: Slower deployment but better regression detection

## Automated Rollback

Rollback is triggered when **both** conditions are met for **N consecutive windows**:
- **P99 Latency** > threshold (default: 500ms)
- **OR Error Rate** > threshold (default: 5%)

**Configuration**:
- `P99_THRESHOLD_MS`: Latency threshold in milliseconds
- `ERR_THRESHOLD`: Error rate threshold (0.0-1.0)
- `WINDOW_SEC`: Time window size for metric aggregation (default: 10s)
- `CONSEC_WINDOWS`: Number of consecutive bad windows before rollback (default: 2)

## Metrics and Measurement

### Collected Metrics
- **Latency Percentiles**: P50, P95, P99 per time window
- **Error Rate**: Percentage of non-2xx responses per window
- **Request Count**: Total requests per window
- **Deployment Events**: Rollout steps and rollback triggers

### Research-Grade Metrics

In addition to basic performance metrics, ChangeLens computes research-grade derived metrics:

- **Time-to-Detection (TTD)**: Time from deployment start to rollback trigger (seconds)
- **Recovery Time**: Time from rollback trigger to metrics return to baseline (seconds)
- **Impact Scope**: 
  - Traffic percentage to v2 before rollback
  - Affected user percentage (traffic_to_v2 × error_rate)

### Measurement Methodology
- **Time Windows**: 10-second aggregation windows
- **Load Pattern**: 10 concurrent virtual users (VUs) with 100ms think time
- **Test Duration**: 10 minutes total (1 min warmup + 9 min main test)
- **Reproducibility**: Fixed random seeds for deterministic behavior

## Research Methodology

### Experimental Design

ChangeLens follows rigorous experimental methodology for research-grade results:

**Multi-Run Experiments**:
- Each scenario (Canary, Blue-Green) is executed **N=10 times** with different random seeds
- Seeds: base_seed + run_id (default: 42-51)
- Each run produces independent measurements for statistical analysis

**Statistical Analysis**:
- **Bootstrap Confidence Intervals**: 95% CI using percentile method (1000 bootstrap samples)
- **Effect Size**: Cliff's Delta for non-parametric comparison between deployment strategies
- **Aggregation**: Mean ± standard deviation with 95% CI for all metrics

**Configuration Tracking**:
- Complete experiment metadata captured per run:
  - Timestamp, git commit hash, Docker image tags
  - Environment variables (regression settings, thresholds)
  - Load parameters, random seed, host system info
- Saved in `results/run_{i}/config.json` for full reproducibility

**Derived Metrics Calculation**:
- TTD, Recovery Time, and Impact Scope computed from windowed metrics and rollback events
- Baseline calculated from warmup period (first 60 seconds)
- Recovery criteria: P99 < baseline + 10% AND error_rate < baseline + 1%

### Running Research Experiments

**Full Research Suite** (recommended):
```powershell
# Run complete research workflow (N runs per scenario + aggregation + report)
.\scripts\run_research_suite.ps1 -NRuns 10
```

**Individual Scenario**:
```powershell
# Run N canary experiments
python scripts/run_experiment_suite.py --scenario canary --n-runs 10

# Run N bluegreen experiments  
python scripts/run_experiment_suite.py --scenario bluegreen --n-runs 10
```

**Statistical Analysis**:
```powershell
# Aggregate results with bootstrap CI
python scripts/statistical_analysis.py --runs-dir results/canary --scenario canary --output aggregated.json

# Compare both scenarios
python scripts/statistical_analysis.py --runs-dir results --scenario both --output aggregated.json
```

**Generate Summary Report**:
```powershell
python scripts/generate_summary.py --results aggregated_results.json --output results/summary.md --n-runs 10
```

## Machine Learning Module: Early Regression Risk Prediction

ChangeLens includes a machine learning module for predicting deployment-induced performance regressions from early telemetry data. This module addresses the research question: **Can we predict whether a deployment will trigger a rollback based on metrics from the first 1-2 minutes after deployment?**

### Approach

We extract features from the first 120 seconds of post-deployment metrics:

**Latency Features**:
- P50/P95/P99 percentiles, deltas from baseline, rolling trends
- Mean, max, standard deviation across windows

**Error Features**:
- Error rate, error count, error rate trends
- Deltas from baseline error rate

**Deployment Context**:
- Time since deployment, traffic percentage (for Canary), deployment stage
- Scenario type (Canary vs. Blue-Green)

We train lightweight models (Logistic Regression, XGBoost) to predict:
- **Binary Classification**: Will this deployment trigger a rollback? (0/1)
- **Multi-class Classification**: What type of regression? (none/CPU/DB/downstream)

### Evaluation Metrics

**Classification Performance**:
- ROC-AUC, PR-AUC (Precision-Recall AUC), F1-Score
- Precision, Recall, Confusion Matrix

**Early Warning Capability** (Core Research Metric):
- **Early Detection Rate**: Percentage of rollbacks predicted X seconds in advance (10s, 20s, 30s, 60s, 120s)
- **Mean Early Warning Time**: Average time between prediction and actual rollback
- **False Positive/Negative Rates**: Trade-off between early detection and false alarms

### Usage

**Build Dataset**:
```powershell
# Extract features from experiment runs
python scripts/ml_dataset.py --results-dir results --output ml/dataset.csv --feature-window 120
```

**Train Models**:
```powershell
# Train Logistic Regression and XGBoost
python scripts/ml_train.py --dataset ml/dataset.csv --models-dir ml/models --test-size 0.2
```

**Evaluate Models**:
```powershell
# Evaluate both models and generate metrics/visualizations
python scripts/ml_eval.py --models-dir ml/models --dataset ml/dataset.csv --results-dir ml/results --model-type both
```

**Output**:
- Trained models: `ml/models/logistic_regression.pkl`, `ml/models/xgboost.json`
- Evaluation report: `ml/results/evaluation_report.json`
- Visualizations: ROC curve, PR curve, early warning time distribution

### Research Impact

This ML module extends ChangeLens from a deployment strategy comparison benchmark to a predictive system for deployment safety. It demonstrates how lightweight ML models can enhance traditional threshold-based rollback mechanisms, reducing Time-to-Detection (TTD) and limiting user impact during canary rollouts.

**Key Contribution**: Our ML models (XGBoost achieves ROC-AUC 0.75, PR-AUC 0.71) can predict rollbacks with mean early warning time of 140 seconds, achieving 33% early detection rate at 30+ seconds in advance with 0% false positive rate. This reduces user impact compared to reactive threshold-based systems. See [`ml/results/evaluation_report.json`](ml/results/evaluation_report.json) for detailed metrics.

### Results Structure

```
results/
  experiment_YYYYMMDD_HHMMSS/
    canary/
      run_1/
        config.json              # Experiment configuration
        canary_*.json            # k6 raw output
        canary_*.csv             # Windowed metrics
        events.json              # Rollback events
        derived_metrics.json     # TTD, Recovery, Impact Scope
        latency_canary.png       # Visualization
        error_rate_canary.png
      run_2/
        ...
      suite_summary.json
    bluegreen/
      run_1/
        ...
    aggregated_results.json     # Statistical aggregation
    summary.md                  # Research report
```

## Quick Inspection (No-Run Demo)

If you just want to inspect outputs without running experiments, see [`results/demo/`](results/demo/) or open [`results/demo/README.md`](results/demo/README.md) directly for a complete sample experiment output including:
- [`summary.md`](results/demo/summary.md): Research report with methodology and results
- [`aggregated_results.json`](results/demo/aggregated_results.json): Statistical aggregation (mean ± 95% CI)
- [`canary_run_1/`](results/demo/canary_run_1/) and [`bluegreen_run_1/`](results/demo/bluegreen_run_1/): Individual run results with plots and derived metrics

**📦 Pre-packaged Release**: For a complete demo package including all results and visualizations, download the [latest GitHub Release](https://github.com/chenyuxiangAK47/changelens/releases/latest). See [`docs/RELEASE_GUIDE.md`](docs/RELEASE_GUIDE.md) for details.

## Reproduce in 5 Minutes

This section demonstrates how to reproduce our research results from scratch.

### Prerequisites Check

```powershell
# 1. Check Docker
docker --version
docker compose version

# 2. Check k6
k6 version

# 3. Check Python (recommended: 3.12)
python --version
```

### One-Command Setup

```powershell
# Windows: Setup environment and install dependencies
.\scripts\setup_venv.ps1

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### Run Demo Experiment (3 runs, ~15 minutes)

```powershell
# 1. Start services
docker compose up -d

# Wait for services to be healthy (~30 seconds)
docker compose ps

# 2. Run research suite (N=3 for quick demo)
.\scripts\run_research_suite.ps1 -NRuns 3

# 3. View results
# Results will be in: results/experiment_YYYYMMDD_HHMMSS/
# - summary.md: Research report
# - aggregated_results.json: Statistical analysis
# - canary/run_*/: Individual run results with plots
```

### Expected Output

After running, you should see:
- `results/experiment_*/summary.md` - Research report with methodology and results
- `results/experiment_*/aggregated_results.json` - Statistical aggregation (mean ± CI)
- `results/experiment_*/canary/run_*/latency_*.png` - Latency plots
- `results/experiment_*/canary/run_*/error_rate_*.png` - Error rate plots

**Time**: ~15 minutes for N=3 runs (each run ~5 minutes)

---

## Prerequisites

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **k6** >= 0.47.0 ([Installation Guide](https://k6.io/docs/getting-started/installation/))
- **Python 3.12** (recommended) or Python >= 3.11
  - **Note**: Python 3.13 may have compatibility issues with some dependencies
  - Use `scripts/setup_venv.ps1` to create isolated environment
- **pip** (for Python dependencies)

### Quick Environment Setup

**Windows (PowerShell)**:
```powershell
# One-command setup (creates venv and installs dependencies)
.\scripts\setup_venv.ps1

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

**Linux/macOS**:
```bash
# Create venv
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Installing k6

**Windows** (using Chocolatey):
```powershell
choco install k6
```

**macOS** (using Homebrew):
```bash
brew install k6
```

**Linux**:
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

## Quick Start

### 1. Clone and Setup

```bash
cd D:\ChangeLens
cp .env.example .env  # Optional: customize regression settings
```

### 2. Start Services

```bash
docker compose up -d
```

Wait for all services to be healthy (check with `docker compose ps`).

### 3. Install Python Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run Canary Deployment Test

**Windows (PowerShell)**:
```powershell
.\scripts\run_canary.ps1
```

**Linux/macOS**:
```bash
bash scripts/run_canary.sh
```

### 5. Run Blue-Green Deployment Test

**Windows (PowerShell)**:
```powershell
.\scripts\run_bluegreen.ps1
```

**Linux/macOS**:
```bash
bash scripts/run_bluegreen.sh
```

### 5. View Results

Generated plots are saved in `results/`:
- `latency_canary.png` / `latency_bluegreen.png`: P99 latency over time
- `error_rate_canary.png` / `error_rate_bluegreen.png`: Error rate over time

## Configuration

### Environment Variables

Edit `.env` file or set environment variables:

```bash
# Enable/disable regressions in API v2
REG_CPU=1              # Enable CPU regression
REG_DB=1               # Enable DB regression
REG_DOWNSTREAM=1       # Enable downstream regression

# Downstream service behavior
DOWNSTREAM_LATENCY_MS=50      # Base latency (ms)
DOWNSTREAM_SPIKE_PROB=0.1     # Probability of latency spike
DOWNSTREAM_SPIKE_MS=200        # Spike duration (ms)
DOWNSTREAM_ERROR_PROB=0.15     # Error probability when regression enabled

# Rollback thresholds
P99_THRESHOLD_MS=500           # P99 latency threshold
ERR_THRESHOLD=0.05             # Error rate threshold (5%)
WINDOW_SEC=10                  # Aggregation window (seconds)
CONSEC_WINDOWS=2               # Consecutive bad windows for rollback
```

## Reproducing Results

### Deterministic Behavior

ChangeLens ensures reproducibility through:
- **Fixed Random Seeds**: All random number generators use seed=42
- **Pinned Dependencies**: Exact versions specified in `requirements.txt`
- **Deterministic Regression Toggles**: Environment variables control regression behavior

### Expected Results

With default regression settings (`REG_CPU=1`, `REG_DB=1`, `REG_DOWNSTREAM=1`):

1. **Baseline Phase (0-120s)**: 
   - P99 latency: ~100-200ms
   - Error rate: <1%

2. **After Deployment (120s+)**:
   - **Blue-Green**: Immediate spike in P99 latency (>500ms) and error rate (>5%)
   - **Canary**: Gradual increase as traffic percentage increases
   - Rollback should trigger within 20-40 seconds after full deployment

3. **Post-Rollback**:
   - Metrics return to baseline levels
   - System stabilizes

## Understanding the Plots

### Plot 1: P99 Latency Over Time

This plot shows:
- **Blue line**: P99 latency trend
- **Red dashed line**: Rollback threshold (500ms)
- **Green/Orange vertical lines**: Deployment milestones
  - Blue-Green: Single switch point at 120s
  - Canary: Multiple stages (5%, 25%, 100%)
- **Red vertical line**: Rollback trigger point

**Interpretation**:
- Steep increase after deployment indicates regression impact
- Canary deployment shows gradual latency increase, allowing earlier detection
- Rollback effectiveness is visible as latency returns to baseline

### Plot 2: Error Rate Over Time

This plot shows:
- **Red line**: Error rate percentage
- **Red dashed line**: Error threshold (5%)
- **Deployment markers**: Same as latency plot
- **Rollback marker**: When error rate triggers rollback

**Interpretation**:
- Error spikes indicate downstream regression impact
- Canary deployment limits error exposure to subset of traffic
- Rollback prevents error rate from escalating further

## Research Summary

### Research Question
How do Blue-Green and Canary deployment strategies compare in detecting and mitigating performance regressions in cloud-native microservices?

### Experimental Setup
- **System**: 3 microservices (API v1, API v2, Downstream) + PostgreSQL
- **Load**: 10 concurrent users, 10-minute test duration
- **Regressions**: CPU contention, missing DB index, downstream latency/errors
- **Metrics**: P50/P95/P99 latency, error rate, aggregated in 10s windows

### Key Findings

Based on experimental results (N=3 runs per scenario, 95% bootstrap CI):

1. **Deployment Strategy Trade-offs**:
   - **Canary deployment** shows higher P99 latency (446ms ± 23ms, 95% CI [424, 471]) but **3x lower error rate** (0.02% vs 0.06%) compared to Blue-Green, demonstrating better error containment during gradual rollout
   - **Blue-Green deployment** achieves lower P99 latency (430ms ± 14ms, 95% CI [420, 446]) but exposes all traffic immediately, resulting in higher error rates (Cohen's d = 2.35, large effect size)

2. **ML-Enhanced Early Warning**:
   - **XGBoost model** achieves 33% early detection rate (30+ seconds in advance) with **0% false positive rate** (ROC-AUC 0.75, PR-AUC 0.71), enabling proactive rollback decisions before threshold-based triggers
   - Mean early warning time: 140 seconds, demonstrating potential to reduce user impact compared to reactive systems

3. **Metric Sensitivity**:
   - Error rate shows larger effect size (Cohen's d = 2.35) than P99 latency (Cohen's d = -0.86) when comparing deployment strategies, suggesting error rate may be a more discriminative metric for regression detection in this benchmark

### What the Plots Demonstrate

The generated plots demonstrate:
1. **Regression Impact**: Quantified increase in latency and errors when regressions are enabled
2. **Deployment Strategy Comparison**: Visual comparison of gradual (Canary) vs. instant (Blue-Green) rollouts
3. **Rollback Effectiveness**: How automated rollback restores system stability
4. **Detection Time**: Time-to-detection difference between strategies

## File Structure

```
ChangeLens/
├── services/
│   ├── api_v1/          # Baseline API service
│   ├── api_v2/          # API with regression toggles
│   └── downstream/      # External dependency simulator
├── load/
│   └── k6/              # k6 load test scripts
│       ├── checkout.js
│       ├── scenario_bluegreen.js
│       └── scenario_canary.js
├── scripts/
│   ├── parse_k6.py      # Parse k6 JSON to CSV
│   ├── plot_results.py  # Generate visualization plots
│   ├── run_bluegreen.sh # Blue-Green test runner
│   └── run_canary.sh    # Canary test runner
├── results/             # Generated plots and CSV files
├── docker-compose.yml   # Service orchestration
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
└── README.md            # This file
```

## Troubleshooting

### Services not starting
```bash
docker compose logs
docker compose ps
```

### k6 not found
Ensure k6 is installed and in PATH: `k6 version`

### Port conflicts
Modify ports in `docker-compose.yml` if 8001, 8002, 8003, 5432, or 6379 are in use

### Plot generation fails
Ensure matplotlib is installed: `pip install -r requirements.txt`

## Comparison with Existing Benchmarks

ChangeLens is designed as a **lightweight, controlled, and focused** benchmark specifically for deployment regression detection research. Compared to existing microservice benchmarks:

### DeathStarBench & TrainTicket
- **DeathStarBench** (Gan et al., SOSP 2019): Comprehensive microservice suite with 10+ services, complex dependencies, and realistic workloads (social network, media service, e-commerce). Designed for end-to-end system performance evaluation.
- **TrainTicket** (Zhou et al., ICSE 2021): Large-scale microservice system with 41 services, simulating a railway ticketing platform. Focuses on distributed system testing and fault injection.

**ChangeLens Positioning**:
- **Smaller scale** (3 services) enables faster iteration and easier reproducibility
- **Controlled regression injection** (CPU/DB/downstream) allows systematic study of specific failure modes
- **Deterministic load generation** (seeded random) ensures reproducible results across runs
- **Focused research question**: Deployment strategy comparison (Blue-Green vs. Canary) with automated rollback
- **Faster execution**: Single experiment completes in ~10 minutes vs. hours for larger benchmarks
- **Lower resource requirements**: Runs on a single machine with Docker, making it accessible for researchers without cluster access

**Use Cases**:
- ChangeLens is ideal for: deployment strategy research, rollback mechanism evaluation, regression detection sensitivity analysis
- DeathStarBench/TrainTicket are better for: end-to-end system performance, complex fault propagation, large-scale scalability studies

## Threats to Validity

### External Validity
1. **Synthetic Benchmark**: Results are based on a minimal microservice architecture. Real-world production systems may exhibit different characteristics due to:
   - Network conditions (latency, packet loss, bandwidth)
   - Hardware variations (CPU, memory, disk I/O)
   - Application-specific behaviors and dependencies
   - Multi-tenant resource contention

2. **Limited Regression Types**: The three controlled regression scenarios (CPU, DB, downstream) may not capture all types of performance regressions encountered in production:
   - Memory leaks or GC pressure
   - Network partition scenarios
   - Cascading failures across multiple services
   - Gradual degradation vs. sudden failures

3. **Single-Machine Environment**: All services run on a single machine using Docker. Real production deployments involve:
   - Distributed systems across multiple nodes/data centers
   - Network latency and bandwidth constraints
   - Load balancers and service mesh overhead
   - Container orchestration (Kubernetes) complexities

### Internal Validity
1. **Load Generation Model**: k6's virtual user model may not perfectly represent real user behavior:
   - Fixed request patterns vs. variable user sessions
   - Simplified routing logic (no real API gateway)
   - Deterministic traffic distribution may not capture burst patterns

2. **Metric Aggregation Windows**: 10-second aggregation windows provide a balance between granularity and noise, but:
   - Finer-grained analysis (1-5s) might reveal additional patterns
   - Coarser windows (30-60s) might miss rapid changes
   - Window boundaries may affect rollback trigger timing

3. **Rollback Thresholds**: Fixed thresholds (P99 > 500ms, error rate > 5%) may not be optimal for all scenarios:
   - Different applications have different SLO requirements
   - Thresholds should be adaptive based on baseline characteristics
   - Consecutive window requirement (N=2) may delay detection

### Construct Validity
1. **Deployment Strategy Implementation**: Our Blue-Green and Canary implementations are simplified:
   - Real-world deployments involve gradual traffic shifting with health checks
   - Canary analysis often includes A/B testing and feature flags
   - Rollback mechanisms may involve database migrations and state management

2. **Performance Metrics**: P99 latency and error rate are common SLO metrics, but:
   - Other metrics (throughput, availability, cost) may be equally important
   - User-perceived latency may differ from server-side measurements
   - Error classification (4xx vs. 5xx) may need more nuanced analysis

### Reproducibility
1. **Environment Dependencies**: Results depend on:
   - Docker and Docker Compose versions
   - Host machine resources (CPU, memory, disk I/O)
   - Operating system and kernel versions
   - Network stack configuration

2. **Random Seed Effects**: While we use fixed seeds for reproducibility, different seed values may lead to different outcomes, especially for:
   - Downstream service error injection (15% probability)
   - Traffic distribution in Canary deployments
   - k6's internal timing mechanisms

## Citation

If you use ChangeLens in your research, please cite:

```bibtex
@software{changelens2024,
  title = {ChangeLens: A Cloud-Native Microservice Benchmark for Change-Induced Performance Regressions},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/yourusername/changelens}
}
```

## License

MIT License - See LICENSE file for details

## Contributing

This is a research benchmark. Contributions, bug reports, and suggestions are welcome via GitHub Issues.

## Acknowledgments

Built with FastAPI, k6, PostgreSQL, and Docker. Designed for reproducibility and academic research.
