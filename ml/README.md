# ChangeLens ML Module: Early Regression Risk Prediction

This directory contains the machine learning module for predicting deployment-induced performance regressions.

## Overview

The ML module extends ChangeLens from a deployment strategy comparison tool to a predictive system for deployment safety. It predicts whether a deployment will trigger a rollback based on metrics from the first 120 seconds after deployment.

## Directory Structure

```
ml/
├── models/              # Trained models (gitignored)
│   ├── logistic_regression.pkl
│   ├── scaler.pkl
│   ├── xgboost.json
│   ├── feature_names.json
│   └── training_metrics.json
├── results/            # Evaluation results (gitignored)
│   ├── evaluation_report.json
│   ├── roc_curve_logistic.png
│   ├── pr_curve_logistic.png
│   └── early_warning_dist_logistic.png
├── dataset.csv         # Extracted features (gitignored)
└── README.md           # This file
```

## Workflow

### 1. Feature Extraction

Extract features from experiment runs:

```bash
python scripts/ml_dataset.py --results-dir results --output ml/dataset.csv --feature-window 120
```

**Input**: CSV files, events.json, config.json from experiment runs  
**Output**: `ml/dataset.csv` with features and labels

**Features Extracted**:
- **Per-window metrics**: P50/P95/P99, error_rate, request counts
- **Baseline comparison**: Deltas from baseline (mean, max, std)
- **Trend features**: Linear regression slopes, rolling statistics
- **Deployment context**: Time since deployment, traffic percentage, scenario type

**Labels**:
- `will_rollback`: Binary (0/1)
- `regression_type`: Multi-class (none/cpu/db/downstream)

### 2. Model Training

Train Logistic Regression and XGBoost models:

```bash
python scripts/ml_train.py --dataset ml/dataset.csv --models-dir ml/models --test-size 0.2
```

**Models**:
- **Logistic Regression**: Interpretable, uses StandardScaler for feature scaling
- **XGBoost**: Gradient boosting, handles non-linear relationships

**Output**:
- Trained models saved to `ml/models/`
- Feature importance rankings
- Training metrics (accuracy, F1-score, ROC-AUC)

### 3. Model Evaluation

Evaluate models with research-grade metrics:

```bash
python scripts/ml_eval.py --models-dir ml/models --dataset ml/dataset.csv --results-dir ml/results --model-type both
```

**Evaluation Metrics**:

**Classification Performance**:
- ROC-AUC: Overall classification ability
- PR-AUC: Performance on imbalanced data
- F1-Score: Balance between precision and recall
- Confusion Matrix: True/False positives and negatives

**Early Warning Capability** (Core Research Metric):
- Early Detection Rate: % of rollbacks predicted X seconds in advance
  - Thresholds: 10s, 20s, 30s, 60s, 120s
- Mean Early Warning Time: Average time between prediction and actual rollback
- False Positive Rate: % of deployments predicted to rollback but didn't
- False Negative Rate: % of deployments that rolled back but weren't predicted

**Output**:
- `evaluation_report.json`: Complete metrics
- `roc_curve_*.png`: ROC curve visualization
- `pr_curve_*.png`: Precision-Recall curve
- `early_warning_dist_*.png`: Distribution of early warning times

## Feature Engineering

### Baseline Calculation
- Uses first 60 seconds (warmup period) as baseline
- Calculates mean P99 latency and error rate

### Feature Window
- Extracts features from first 120 seconds after deployment
- 12 windows × 10 seconds each
- Balances early detection with sufficient signal

### Aggregated Features
- **Statistics**: Mean, max, std across windows
- **Deltas**: Differences from baseline
- **Trends**: Linear regression slopes
- **Rolling stats**: Mean and std of last 3 windows

## Model Selection

**Logistic Regression**:
- ✅ Interpretable (coefficients show feature importance)
- ✅ Fast training and prediction
- ✅ Good baseline for comparison
- ⚠️ Assumes linear relationships

**XGBoost**:
- ✅ Handles non-linear relationships
- ✅ Feature importance via tree splits
- ✅ Often better performance
- ⚠️ Less interpretable than Logistic Regression

## Research Narrative

This ML module demonstrates how lightweight machine learning models can enhance traditional threshold-based rollback mechanisms:

1. **Early Detection**: Predict rollbacks 30+ seconds before they occur
2. **Reduced Impact**: Limit user exposure to regressions
3. **Adaptive**: Learn from historical deployment patterns
4. **Interpretable**: Feature importance reveals key indicators

**One-liner for applications**:
> "I built a reproducible microservice benchmark and trained lightweight ML models to predict change-induced regressions from early telemetry, achieving [X]% early detection rate and reducing Time-to-Detection by [Y] seconds compared to threshold-based rollback."

## Future Work

1. **Per-Window Prediction**: Predict at each 10s window instead of aggregated features
2. **Adaptive Thresholds**: Learn optimal rollback thresholds from data
3. **Multi-Class Regression Type**: Improve classification of regression types
4. **Online Learning**: Update models as new deployments occur
5. **Feature Engineering**: Add more sophisticated time-series features (LSTM, attention)

## Troubleshooting

**No features extracted**:
- Ensure experiment runs have CSV files and events.json
- Check that deployment_start time is correct (default: 120s)

**Poor model performance**:
- Need more training data (run more experiments)
- Check feature distributions for outliers
- Try different feature windows (60s, 180s)

**Early warning metrics are 0**:
- Ensure rollback events are correctly detected
- Check that rollback_time is set in events.json
- Verify feature window overlaps with rollback time

## References

- Scikit-learn: https://scikit-learn.org/
- XGBoost: https://xgboost.readthedocs.io/
- ROC-AUC explanation: https://en.wikipedia.org/wiki/Receiver_operating_characteristic
