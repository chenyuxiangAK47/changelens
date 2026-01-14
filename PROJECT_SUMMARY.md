# ChangeLens Project Summary

## ✅ Project Status: Complete

All core components have been implemented and are ready for testing.

## 📁 Project Structure

```
D:\ChangeLens/
├── services/
│   ├── api_v1/          ✅ Baseline API service (no regressions)
│   ├── api_v2/          ✅ API with regression toggles (CPU, DB, Downstream)
│   └── downstream/      ✅ External dependency simulator
├── load/
│   └── k6/              ✅ Load testing scripts
│       ├── checkout.js
│       ├── scenario_bluegreen.js
│       └── scenario_canary.js
├── scripts/
│   ├── parse_k6.py      ✅ k6 JSON to CSV parser
│   ├── plot_results.py   ✅ Visualization generator
│   ├── run_bluegreen.ps1 ✅ Windows PowerShell runner
│   ├── run_canary.ps1    ✅ Windows PowerShell runner
│   ├── run_bluegreen.sh  ✅ Linux/macOS runner
│   ├── run_canary.sh     ✅ Linux/macOS runner
│   └── verify_setup.py   ✅ Service verification script
├── results/             ✅ Output directory for plots and CSV
├── docker-compose.yml    ✅ Service orchestration
├── requirements.txt     ✅ Python dependencies
├── .env.example         ✅ Configuration template
├── README.md            ✅ Comprehensive documentation
└── LICENSE              ✅ MIT License
```

## 🚀 Quick Start

### 1. Start Services
```powershell
cd D:\ChangeLens
docker compose up -d
```

### 2. Verify Setup
```powershell
python scripts/verify_setup.py
```

### 3. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run Tests

**Canary Deployment:**
```powershell
.\scripts\run_canary.ps1
```

**Blue-Green Deployment:**
```powershell
.\scripts\run_bluegreen.ps1
```

### 5. View Results

Plots will be generated in `results/`:
- `latency_canary.png` / `latency_bluegreen.png`
- `error_rate_canary.png` / `error_rate_bluegreen.png`

## 🎯 Key Features Implemented

### ✅ Controlled Regressions
- **CPU Regression**: Lock contention + busy-wait loops (~50-70ms overhead)
- **DB Regression**: Missing index on user_id (full table scans)
- **Downstream Regression**: Latency spikes (200ms) + 15% error rate

### ✅ Deployment Strategies
- **Blue-Green**: Instant 100% traffic switch at T=120s
- **Canary**: Gradual rollout (5% → 25% → 100%)

### ✅ Automated Rollback
- P99 latency threshold: 500ms
- Error rate threshold: 5%
- Window-based detection (10s windows)
- Requires 2 consecutive bad windows

### ✅ Metrics & Visualization
- P50/P95/P99 latency percentiles
- Error rate tracking
- Deployment event markers
- Rollback trigger visualization

## 📊 Expected Results

With default regression settings (`REG_CPU=1`, `REG_DB=1`, `REG_DOWNSTREAM=1`):

1. **Baseline (0-120s)**: P99 ~100-200ms, Error rate <1%
2. **After Deployment**: 
   - Blue-Green: Immediate spike (P99 >500ms, errors >5%)
   - Canary: Gradual increase with traffic percentage
3. **Rollback**: Triggers within 20-40s, metrics return to baseline

## 🔧 Configuration

Edit `.env` file or set environment variables:
- `REG_CPU=1` - Enable CPU regression
- `REG_DB=1` - Enable DB regression  
- `REG_DOWNSTREAM=1` - Enable downstream regression
- `P99_THRESHOLD_MS=500` - Rollback latency threshold
- `ERR_THRESHOLD=0.05` - Rollback error rate threshold

## 📝 Next Steps

1. **Run the tests** to generate initial plots
2. **Experiment** with different regression combinations
3. **Compare** Blue-Green vs Canary results
4. **Analyze** rollback effectiveness

## 🐛 Troubleshooting

- **Services not starting**: Check `docker compose logs`
- **k6 not found**: Install k6 (see README)
- **Port conflicts**: Modify ports in `docker-compose.yml`
- **Plot generation fails**: Ensure matplotlib is installed

## 📚 Documentation

See `README.md` for:
- Detailed architecture explanation
- Research question and methodology
- Complete configuration options
- Plot interpretation guide
- Academic citation format

## 🎓 Academic Use

This project is designed for:
- PhD research on deployment strategies
- Performance regression studies
- Cloud-native system benchmarking
- Automated rollback mechanism evaluation

All code is reproducible with fixed random seeds and pinned dependencies.
