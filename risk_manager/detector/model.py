"""Detector model training and evaluation."""
import json
import pickle
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score, recall_score, f1_score, confusion_matrix,
    precision_recall_curve, auc, classification_report
)


CASE_TYPES = ["return_abuse", "transaction_fraud", "fraud_spike", "abuse_ring", "normal"]


class FeaturePreprocessor:
    """Convert feature dicts to numeric arrays, handle Decimal types."""
    
    def __init__(self, feature_names: list[str] = None):
        self.feature_names = feature_names or [
            "customer_order_count", "customer_return_count", "customer_return_rate",
            "customer_avg_order_value", "order_value", "order_value_vs_avg_ratio",
            "amount", "customer_avg_transaction_amount", "amount_vs_avg_ratio",
            "transaction_velocity_24h", "transaction_velocity_1h",
            "customer_failed_transaction_count", "customer_failed_transaction_rate",
            "unusual_payment_method", "customer_account_age_days",
            "devices_per_customer", "accounts_per_device",
        ]
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_fitted = False
    
    def fit(self, features_list: list[dict]):
        """Fit preprocessor on training data."""
        X = self._to_numeric(features_list)
        self.scaler.fit(X)
        self.label_encoder.fit(CASE_TYPES)
        self.is_fitted = True
    
    def transform(self, features_list: list[dict]) -> np.ndarray:
        """Transform feature dicts to scaled numeric array."""
        X = self._to_numeric(features_list)
        return self.scaler.transform(X)
    
    def fit_transform(self, features_list: list[dict]) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(features_list)
        return self.transform(features_list)
    
    def encode_labels(self, labels: list[str]) -> np.ndarray:
        """Encode case type labels to numeric."""
        return self.label_encoder.transform(labels)
    
    def decode_labels(self, encoded: np.ndarray) -> list[str]:
        """Decode numeric labels to case types."""
        return self.label_encoder.inverse_transform(encoded)
    
    def _to_numeric(self, features_list: list[dict]) -> np.ndarray:
        """Convert feature dicts to numeric array."""
        rows = []
        for feat_dict in features_list:
            row = []
            for name in self.feature_names:
                val = feat_dict.get(name, 0)
                if isinstance(val, Decimal):
                    val = float(val)
                elif isinstance(val, bool):
                    val = 1.0 if val else 0.0
                row.append(float(val))
            rows.append(row)
        return np.array(rows)
    
    def save(self, path: Path):
        """Save preprocessor to disk."""
        with open(path, "wb") as f:
            pickle.dump(self, f)
    
    @staticmethod
    def load(path: Path) -> "FeaturePreprocessor":
        """Load preprocessor from disk."""
        with open(path, "rb") as f:
            return pickle.load(f)


class DetectorModel:
    """4-class case detector using Random Forest."""
    
    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        if model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            )
        elif model_type == "logistic_regression":
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight="balanced",
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.preprocessor = None
        self.metadata = {}
    
    def train(self, X_train, y_train):
        """Train model on training data."""
        self.model.fit(X_train, y_train)
    
    def predict_proba(self, X) -> np.ndarray:
        """Predict class probabilities."""
        return self.model.predict_proba(X)
    
    def predict(self, X) -> np.ndarray:
        """Predict class labels."""
        return self.model.predict(X)
    
    def save(self, path: Path):
        """Save model to disk."""
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
    
    @staticmethod
    def load(path: Path) -> "DetectorModel":
        """Load model from disk."""
        detector = DetectorModel()
        with open(path, "rb") as f:
            detector.model = pickle.load(f)
        return detector


def evaluate_detector(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    label_decoder,
) -> dict:
    """Compute evaluation metrics."""
    y_true_decoded = label_decoder.decode_labels(y_true)
    y_pred_decoded = label_decoder.decode_labels(y_pred)
    
    metrics = {
        "accuracy": float(np.mean(y_pred == y_true)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro")),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro")),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro")),
        "precision_weighted": float(precision_score(y_true, y_pred, average="weighted")),
        "recall_weighted": float(recall_score(y_true, y_pred, average="weighted")),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted")),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    
    # Per-class metrics
    for i, case_type in enumerate(CASE_TYPES):
        y_binary = (y_true == i).astype(int)
        if y_binary.sum() > 0:
            precision = precision_score(y_binary, (y_pred == i).astype(int), zero_division=0)
            recall = recall_score(y_binary, (y_pred == i).astype(int), zero_division=0)
            f1 = f1_score(y_binary, (y_pred == i).astype(int), zero_division=0)
            
            metrics[f"{case_type}_precision"] = float(precision)
            metrics[f"{case_type}_recall"] = float(recall)
            metrics[f"{case_type}_f1"] = float(f1)
            
            # PR-AUC (one-vs-rest)
            if y_proba is not None and y_binary.sum() > 0:
                prec, rec, _ = precision_recall_curve(y_binary, y_proba[:, i])
                pr_auc = auc(rec, prec)
                metrics[f"{case_type}_pr_auc"] = float(pr_auc)
    
    return metrics


def train_detector(
    dataset: list[tuple],
    model_type: str = "random_forest",
    test_size: float = 0.2,
    val_size: float = 0.2,
    seed: int = 42,
    save_dir: Path = None,
) -> dict:
    """Train detector on dataset with proper train/val/test split.
    
    Returns dict with model, preprocessor, and test metrics.
    """
    # Extract features and labels
    features_list = [feat for feat, _ in dataset]
    labels = [label for _, label in dataset]
    
    # Split: train+val, test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        features_list, labels, test_size=test_size, random_state=seed, stratify=labels
    )
    
    # Split train+val into train and val
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, 
        test_size=val_size / (1 - test_size),
        random_state=seed,
        stratify=y_train_val
    )
    
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Preprocess
    preprocessor = FeaturePreprocessor()
    X_train_scaled = preprocessor.fit_transform([f for f in X_train])
    X_val_scaled = preprocessor.transform([f for f in X_val])
    X_test_scaled = preprocessor.transform([f for f in X_test])
    
    y_train_enc = preprocessor.encode_labels(y_train)
    y_val_enc = preprocessor.encode_labels(y_val)
    y_test_enc = preprocessor.encode_labels(y_test)
    
    # Train
    detector = DetectorModel(model_type=model_type)
    detector.preprocessor = preprocessor
    detector.train(X_train_scaled, y_train_enc)
    
    # Validate
    y_val_pred = detector.predict(X_val_scaled)
    val_metrics = evaluate_detector(y_val_enc, y_val_pred, None, preprocessor)
    
    # Test (held-out)
    y_test_pred = detector.predict(X_test_scaled)
    y_test_proba = detector.predict_proba(X_test_scaled)
    test_metrics = evaluate_detector(y_test_enc, y_test_pred, y_test_proba, preprocessor)
    
    # Save if directory provided
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        detector.save(save_dir / "model.pkl")
        preprocessor.save(save_dir / "preprocessor.pkl")
        
        metadata = {
            "model_type": model_type,
            "training_time": datetime.now(datetime.now().astimezone().tzinfo).isoformat(),
            "train_size": len(X_train),
            "val_size": len(X_val),
            "test_size": len(X_test),
            "classes": CASE_TYPES,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
        }
        with open(save_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
    
    return {
        "detector": detector,
        "preprocessor": preprocessor,
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
    }
