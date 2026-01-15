"""
ChangeLens ML Model Evaluation
Evaluates trained models with research-grade metrics including early warning capability.
"""

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    roc_curve, roc_auc_score,
    precision_recall_curve, average_precision_score,
    confusion_matrix, f1_score, precision_score, recall_score
)
import xgboost as xgb


def load_model_and_scaler(models_dir: Path, model_type: str = 'logistic'):
    """Load trained model and scaler."""
    if model_type == 'logistic':
        with open(models_dir / 'logistic_regression.pkl', 'rb') as f:
            model = pickle.load(f)
        with open(models_dir / 'scaler.pkl', 'rb') as f:
            scaler = pickle.load(f)
        return model, scaler
    elif model_type == 'xgboost':
        model = xgb.XGBClassifier()
        model.load_model(str(models_dir / 'xgboost.json'))
        return model, None
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def load_feature_names(models_dir: Path) -> List[str]:
    """Load feature names from saved JSON."""
    with open(models_dir / 'feature_names.json', 'r') as f:
        return json.load(f)


def load_test_data(dataset_file: str, feature_names: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    """Load test data matching training features."""
    df = pd.read_csv(dataset_file)
    
    # Select only features used in training
    X = df[feature_names].fillna(0).values
    y = df['will_rollback'].values
    
    # Also return metadata for early warning analysis
    metadata = df[['run_path', 'rollback_time', 'deployment_start']].to_dict('records')
    
    return X, y, metadata


def evaluate_classification(y_true, y_pred, y_pred_proba):
    """Evaluate classification performance."""
    metrics = {
        'roc_auc': float(roc_auc_score(y_true, y_pred_proba)),
        'pr_auc': float(average_precision_score(y_true, y_pred_proba)),
        'f1_score': float(f1_score(y_true, y_pred)),
        'precision': float(precision_score(y_true, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, zero_division=0)),
    }
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    metrics['confusion_matrix'] = {
        'tn': int(cm[0, 0]),
        'fp': int(cm[0, 1]),
        'fn': int(cm[1, 0]),
        'tp': int(cm[1, 1])
    }
    
    # False positive/negative rates
    if len(y_true) > 0:
        metrics['false_positive_rate'] = float(metrics['confusion_matrix']['fp'] / 
                                               (metrics['confusion_matrix']['fp'] + metrics['confusion_matrix']['tn']))
        metrics['false_negative_rate'] = float(metrics['confusion_matrix']['fn'] / 
                                                (metrics['confusion_matrix']['fn'] + metrics['confusion_matrix']['tp']))
    else:
        metrics['false_positive_rate'] = 0.0
        metrics['false_negative_rate'] = 0.0
    
    return metrics


def calculate_early_warning_stats(dataset_file: str, model, scaler, feature_names: List[str],
                                  model_type: str, threshold: float = 0.5):
    """Calculate early warning capability metrics."""
    # Load full dataset with metadata
    df = pd.read_csv(dataset_file)
    
    # Prepare features
    X = df[feature_names].fillna(0).values
    
    # Scale if needed
    if scaler is not None:
        X_scaled = scaler.transform(X)
        y_pred_proba = model.predict_proba(X_scaled)[:, 1]
    else:
        y_pred_proba = model.predict_proba(X)[:, 1]
    
    # Get predictions
    y_pred = (y_pred_proba >= threshold).astype(int)
    
    # Early warning analysis
    early_warning_stats = {
        'early_detection_rate_10s': 0.0,
        'early_detection_rate_20s': 0.0,
        'early_detection_rate_30s': 0.0,
        'early_detection_rate_60s': 0.0,
        'early_detection_rate_120s': 0.0,
        'mean_early_warning_time': 0.0,
        'early_warning_times': []
    }
    
    rollback_runs = df[df['will_rollback'] == 1]
    total_rollbacks = len(rollback_runs)
    
    if total_rollbacks == 0:
        return early_warning_stats
    
    early_warning_times = []
    
    for idx, row in rollback_runs.iterrows():
        rollback_time = row.get('rollback_time')
        deployment_start = row.get('deployment_start', 120.0)
        
        if pd.isna(rollback_time) or rollback_time is None:
            continue
        
        # Get prediction probability for this run
        run_proba = y_pred_proba[idx]
        run_pred = y_pred[idx]
        
        if run_pred == 1:  # Model predicted rollback
            # Calculate when prediction was made (simplified: assume prediction at feature extraction time)
            # In reality, this would be calculated from per-window predictions
            # For now, we use the feature window (120s) as proxy
            prediction_time = deployment_start + 120.0  # Feature window ends at deployment_start + 120s
            
            if prediction_time < rollback_time:
                early_warning_time = rollback_time - prediction_time
                early_warning_times.append(early_warning_time)
    
    if len(early_warning_times) > 0:
        early_warning_stats['mean_early_warning_time'] = float(np.mean(early_warning_times))
        early_warning_stats['early_warning_times'] = [float(t) for t in early_warning_times]
        
        # Calculate detection rates at different thresholds
        for threshold_sec in [10, 20, 30, 60, 120]:
            detected = sum(1 for t in early_warning_times if t >= threshold_sec)
            rate = detected / total_rollbacks
            key = f'early_detection_rate_{threshold_sec}s'
            early_warning_stats[key] = float(rate)
    
    return early_warning_stats


def plot_roc_curve(y_true, y_pred_proba, output_file: str, model_name: str):
    """Plot ROC curve."""
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    roc_auc = roc_auc_score(y_true, y_pred_proba)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'{model_name} (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], 'k--', label='Random')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'ROC Curve - {model_name}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"ROC curve saved to {output_file}")


def plot_pr_curve(y_true, y_pred_proba, output_file: str, model_name: str):
    """Plot Precision-Recall curve."""
    precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
    pr_auc = average_precision_score(y_true, y_pred_proba)
    
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f'{model_name} (AUC = {pr_auc:.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title(f'Precision-Recall Curve - {model_name}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"PR curve saved to {output_file}")


def plot_early_warning_distribution(early_warning_times: List[float], output_file: str):
    """Plot distribution of early warning times."""
    if len(early_warning_times) == 0:
        print("No early warning data to plot")
        return
    
    plt.figure(figsize=(8, 6))
    plt.hist(early_warning_times, bins=20, edgecolor='black', alpha=0.7)
    plt.xlabel('Early Warning Time (seconds)')
    plt.ylabel('Frequency')
    plt.title('Distribution of Early Warning Times')
    plt.axvline(np.mean(early_warning_times), color='r', linestyle='--', 
                label=f'Mean: {np.mean(early_warning_times):.1f}s')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"Early warning distribution saved to {output_file}")


def evaluate_model(models_dir: Path, dataset_file: str, results_dir: Path, model_type: str = 'logistic'):
    """Evaluate a trained model."""
    print(f"\n=== Evaluating {model_type.upper()} Model ===")
    
    # Load model and scaler
    model, scaler = load_model_and_scaler(models_dir, model_type)
    feature_names = load_feature_names(models_dir)
    
    # Load test data
    X, y_true, metadata = load_test_data(dataset_file, feature_names)
    
    # Make predictions
    if scaler is not None:
        X_scaled = scaler.transform(X)
        y_pred_proba = model.predict_proba(X_scaled)[:, 1]
    else:
        y_pred_proba = model.predict_proba(X)[:, 1]
    
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    # Classification metrics
    classification_metrics = evaluate_classification(y_true, y_pred, y_pred_proba)
    
    # Early warning metrics
    early_warning_stats = calculate_early_warning_stats(
        dataset_file, model, scaler, feature_names, model_type
    )
    
    # Combine metrics
    all_metrics = {
        'model_type': model_type,
        'classification': classification_metrics,
        'early_warning': early_warning_stats
    }
    
    # Generate plots
    results_dir.mkdir(parents=True, exist_ok=True)
    
    plot_roc_curve(y_true, y_pred_proba, 
                   results_dir / f'roc_curve_{model_type}.png', 
                   model_type.capitalize())
    
    plot_pr_curve(y_true, y_pred_proba,
                  results_dir / f'pr_curve_{model_type}.png',
                  model_type.capitalize())
    
    if len(early_warning_stats['early_warning_times']) > 0:
        plot_early_warning_distribution(
            early_warning_stats['early_warning_times'],
            results_dir / f'early_warning_dist_{model_type}.png'
        )
    
    return all_metrics


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate ML models for rollback prediction'
    )
    parser.add_argument(
        '--models-dir',
        type=str,
        default='ml/models',
        help='Directory containing trained models'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='ml/dataset.csv',
        help='Test dataset CSV file'
    )
    parser.add_argument(
        '--results-dir',
        type=str,
        default='ml/results',
        help='Output directory for evaluation results'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        choices=['logistic', 'xgboost', 'both'],
        default='both',
        help='Which model(s) to evaluate'
    )
    
    args = parser.parse_args()
    
    models_dir = Path(args.models_dir)
    results_dir = Path(args.results_dir)
    
    if not models_dir.exists():
        print(f"Error: Models directory {models_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not Path(args.dataset).exists():
        print(f"Error: Dataset file {args.dataset} does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Evaluate models
    all_results = {}
    
    if args.model_type in ['logistic', 'both']:
        logistic_metrics = evaluate_model(models_dir, args.dataset, results_dir, 'logistic')
        all_results['logistic_regression'] = logistic_metrics
        
        print("\nLogistic Regression Results:")
        print(f"  ROC-AUC: {logistic_metrics['classification']['roc_auc']:.4f}")
        print(f"  PR-AUC: {logistic_metrics['classification']['pr_auc']:.4f}")
        print(f"  F1-Score: {logistic_metrics['classification']['f1_score']:.4f}")
        print(f"  Early Detection Rate (30s): {logistic_metrics['early_warning']['early_detection_rate_30s']:.2%}")
        print(f"  Mean Early Warning Time: {logistic_metrics['early_warning']['mean_early_warning_time']:.2f}s")
    
    if args.model_type in ['xgboost', 'both']:
        xgboost_metrics = evaluate_model(models_dir, args.dataset, results_dir, 'xgboost')
        all_results['xgboost'] = xgboost_metrics
        
        print("\nXGBoost Results:")
        print(f"  ROC-AUC: {xgboost_metrics['classification']['roc_auc']:.4f}")
        print(f"  PR-AUC: {xgboost_metrics['classification']['pr_auc']:.4f}")
        print(f"  F1-Score: {xgboost_metrics['classification']['f1_score']:.4f}")
        print(f"  Early Detection Rate (30s): {xgboost_metrics['early_warning']['early_detection_rate_30s']:.2%}")
        print(f"  Mean Early Warning Time: {xgboost_metrics['early_warning']['mean_early_warning_time']:.2f}s")
    
    # Save evaluation report
    report_file = results_dir / 'evaluation_report.json'
    with open(report_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nEvaluation report saved to {report_file}")
    
    # Print summary
    print("\n=== Evaluation Summary ===")
    for model_name, metrics in all_results.items():
        print(f"\n{model_name.upper()}:")
        print(f"  Classification Performance:")
        print(f"    ROC-AUC: {metrics['classification']['roc_auc']:.4f}")
        print(f"    PR-AUC: {metrics['classification']['pr_auc']:.4f}")
        print(f"    F1-Score: {metrics['classification']['f1_score']:.4f}")
        print(f"  Early Warning Capability:")
        print(f"    10s advance: {metrics['early_warning']['early_detection_rate_10s']:.2%}")
        print(f"    30s advance: {metrics['early_warning']['early_detection_rate_30s']:.2%}")
        print(f"    60s advance: {metrics['early_warning']['early_detection_rate_60s']:.2%}")
        print(f"    Mean warning time: {metrics['early_warning']['mean_early_warning_time']:.2f}s")


if __name__ == '__main__':
    main()
