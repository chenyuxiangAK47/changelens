"""
ChangeLens ML Model Training
Trains Logistic Regression and XGBoost models for rollback prediction.
"""

import argparse
import json
import pickle
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, precision_score, recall_score
import xgboost as xgb


def load_dataset(dataset_file: str) -> pd.DataFrame:
    """Load dataset from CSV file."""
    df = pd.read_csv(dataset_file)
    
    # Check required columns
    required_cols = ['will_rollback']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Error: Missing required columns: {missing_cols}", file=sys.stderr)
        sys.exit(1)
    
    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """Prepare feature matrix and labels."""
    # Exclude non-feature columns
    exclude_cols = [
        'run_id', 'run_path', 'will_rollback', 'regression_type',
        'rollback_time', 'deployment_start'
    ]
    
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    # Check for missing values
    if df[feature_cols].isnull().any().any():
        print("Warning: Found missing values in features, filling with 0", file=sys.stderr)
        df[feature_cols] = df[feature_cols].fillna(0)
    
    X = df[feature_cols].values
    y = df['will_rollback'].values
    
    return X, y, feature_cols


def train_logistic_regression(X_train, y_train, X_test, y_test, feature_names):
    """Train Logistic Regression model."""
    print("\n=== Training Logistic Regression ===")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight='balanced'  # Handle imbalanced data
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    
    # Feature importance (coefficients)
    feature_importance = {
        name: abs(coef) for name, coef in zip(feature_names, model.coef_[0])
    }
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    
    return model, scaler, {
        'accuracy': float(accuracy),
        'f1_score': float(f1),
        'roc_auc': float(roc_auc),
        'precision': float(precision),
        'recall': float(recall),
        'feature_importance': feature_importance
    }


def train_xgboost(X_train, y_train, X_test, y_test, feature_names):
    """Train XGBoost model."""
    print("\n=== Training XGBoost ===")
    
    # Train model
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss',
        scale_pos_weight=len(y_train[y_train == 0]) / len(y_train[y_train == 1]) if sum(y_train) > 0 else 1
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    
    # Feature importance
    feature_importance = {
        name: importance for name, importance in zip(feature_names, model.feature_importances_)
    }
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    
    return model, {
        'accuracy': float(accuracy),
        'f1_score': float(f1),
        'roc_auc': float(roc_auc),
        'precision': float(precision),
        'recall': float(recall),
        'feature_importance': feature_importance
    }


def save_models(models_dir: Path, logistic_model, logistic_scaler, xgboost_model, 
                feature_names, metrics):
    """Save trained models and metadata."""
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Save Logistic Regression
    with open(models_dir / 'logistic_regression.pkl', 'wb') as f:
        pickle.dump(logistic_model, f)
    
    with open(models_dir / 'scaler.pkl', 'wb') as f:
        pickle.dump(logistic_scaler, f)
    
    # Save XGBoost
    xgboost_model.save_model(str(models_dir / 'xgboost.json'))
    
    # Save feature names
    with open(models_dir / 'feature_names.json', 'w') as f:
        json.dump(feature_names, f, indent=2)
    
    # Save metrics (convert numpy types to native Python types)
    def convert_to_native(obj):
        if isinstance(obj, np.generic):
            return obj.item()  # Convert numpy scalar to Python native type
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_native(item) for item in obj]
        return obj
    
    metrics_native = convert_to_native(metrics)
    with open(models_dir / 'training_metrics.json', 'w') as f:
        json.dump(metrics_native, f, indent=2)
    
    print(f"\nModels saved to {models_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Train ML models for rollback prediction'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='ml/dataset.csv',
        help='Input dataset CSV file'
    )
    parser.add_argument(
        '--models-dir',
        type=str,
        default='ml/models',
        help='Output directory for saved models'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set size (default: 0.2)'
    )
    parser.add_argument(
        '--random-state',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    args = parser.parse_args()
    
    # Load dataset
    print(f"Loading dataset from {args.dataset}")
    df = load_dataset(args.dataset)
    print(f"Dataset shape: {df.shape}")
    print(f"Rollback samples: {df['will_rollback'].sum()}")
    print(f"Non-rollback samples: {len(df) - df['will_rollback'].sum()}")
    
    # Check for class imbalance
    n_rollback = df['will_rollback'].sum()
    n_non_rollback = len(df) - n_rollback
    
    if n_rollback == 0:
        print("\nERROR: No rollback samples found in dataset!")
        print("To train the model, you need experiments that triggered rollbacks.")
        print("\nSuggestions:")
        print("1. Run experiments with regressions enabled (REG_CPU=1, REG_DB=1, REG_DOWNSTREAM=1)")
        print("2. Ensure rollback thresholds are set appropriately (P99_THRESHOLD_MS=500, ERR_THRESHOLD=0.05)")
        print("3. Run more experiments: python scripts/run_experiment_suite.py --scenario canary --n-runs 10")
        sys.exit(1)
    
    if n_non_rollback == 0:
        print("\nERROR: No non-rollback samples found in dataset!")
        print("You need both rollback and non-rollback samples to train a classifier.")
        sys.exit(1)
    
    if len(df) < 10:
        print(f"\nWARNING: Only {len(df)} samples available. For reliable results, recommend at least 20-30 samples.")
    
    # Prepare features
    X, y, feature_names = prepare_features(df)
    print(f"\nNumber of features: {len(feature_names)}")
    print(f"Feature names: {', '.join(feature_names[:10])}..." if len(feature_names) > 10 else f"Feature names: {', '.join(feature_names)}")
    
    # Split data
    # Use stratify only if both classes are present
    stratify_param = y if len(set(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=stratify_param  # Maintain class distribution if possible
    )
    
    print(f"\nTrain set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    # Train models
    logistic_model, logistic_scaler, logistic_metrics = train_logistic_regression(
        X_train, y_train, X_test, y_test, feature_names
    )
    
    xgboost_model, xgboost_metrics = train_xgboost(
        X_train, y_train, X_test, y_test, feature_names
    )
    
    # Save models
    models_dir = Path(args.models_dir)
    metrics = {
        'logistic_regression': logistic_metrics,
        'xgboost': xgboost_metrics
    }
    
    save_models(models_dir, logistic_model, logistic_scaler, xgboost_model, 
                feature_names, metrics)
    
    # Print summary
    print("\n=== Training Summary ===")
    print("Logistic Regression:")
    print(f"  ROC-AUC: {logistic_metrics['roc_auc']:.4f}")
    print(f"  F1-Score: {logistic_metrics['f1_score']:.4f}")
    print("\nXGBoost:")
    print(f"  ROC-AUC: {xgboost_metrics['roc_auc']:.4f}")
    print(f"  F1-Score: {xgboost_metrics['f1_score']:.4f}")
    
    print("\nTop 5 Important Features (Logistic Regression):")
    for i, (feat, importance) in enumerate(list(logistic_metrics['feature_importance'].items())[:5]):
        print(f"  {i+1}. {feat}: {importance:.4f}")
    
    print("\nTop 5 Important Features (XGBoost):")
    for i, (feat, importance) in enumerate(list(xgboost_metrics['feature_importance'].items())[:5]):
        print(f"  {i+1}. {feat}: {importance:.4f}")


if __name__ == '__main__':
    main()
