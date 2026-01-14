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

### Measurement Methodology
- **Time Windows**: 10-second aggregation windows
- **Load Pattern**: 10 concurrent virtual users (VUs) with 100ms think time
- **Test Duration**: 10 minutes total (1 min warmup + 9 min main test)
- **Reproducibility**: Fixed random seeds (42) for deterministic behavior

## Prerequisites

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **k6** >= 0.47.0 ([Installation Guide](https://k6.io/docs/getting-started/installation/))
- **Python** >= 3.11
- **pip** (for Python dependencies)

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

### Key Findings (Expected)

1. **Canary Deployment**:
   - Detects regressions earlier (at 5% or 25% traffic)
   - Limits impact to subset of users
   - Enables faster rollback decision
   - Trade-off: Slower full deployment (4 minutes vs. instant)

2. **Blue-Green Deployment**:
   - Faster full deployment (instant cutover)
   - Higher risk exposure (100% traffic immediately)
   - Rollback occurs after full impact is felt
   - Trade-off: All users affected before rollback

3. **Automated Rollback**:
   - Effective at preventing sustained degradation
   - P99 latency threshold more sensitive than error rate
   - 2-window threshold balances responsiveness vs. false positives

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
