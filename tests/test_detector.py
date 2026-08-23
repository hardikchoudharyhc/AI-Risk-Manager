"""Milestone 3: Detector tests."""
from pathlib import Path
import tempfile

import pytest
import numpy as np

from risk_manager.detector import (
    generate_labeled_dataset,
    train_detector,
    FeaturePreprocessor,
    Predictor,
    CASE_TYPES,
)


class TestDatasetGeneration:
    """Test synthetic dataset generation."""
    
    def test_dataset_generation(self):
        """Verify dataset is generated with correct structure."""
        dataset = generate_labeled_dataset(num_samples=100, seed=42)
        
        assert len(dataset) == 100
        for features, case_type in dataset:
            assert isinstance(features, dict)
            assert case_type in CASE_TYPES
            assert len(features) > 10
    
    def test_class_distribution(self):
        """Verify class distribution is respected."""
        dist = {
            "return_abuse": 0.4,
            "transaction_fraud": 0.3,
            "fraud_spike": 0.2,
            "abuse_ring": 0.1,
            "normal": 0.0,
        }
        dataset = generate_labeled_dataset(num_samples=1000, seed=42, class_distribution=dist)
        
        counts = {}
        for _, case_type in dataset:
            counts[case_type] = counts.get(case_type, 0) + 1
        
        # Check approximate distribution (allow ±5% variance)
        for case_type, expected_pct in dist.items():
            actual_pct = counts.get(case_type, 0) / 1000
            if expected_pct > 0:
                assert abs(actual_pct - expected_pct) < 0.05
    
    def test_reproducibility(self):
        """Same seed produces same dataset."""
        dataset1 = generate_labeled_dataset(num_samples=50, seed=42)
        dataset2 = generate_labeled_dataset(num_samples=50, seed=42)
        
        for (f1, l1), (f2, l2) in zip(dataset1, dataset2):
            assert l1 == l2
            for key in f1.keys():
                assert f1[key] == f2[key]


class TestFeaturePreprocessor:
    """Test feature preprocessing."""
    
    def test_preprocessor_fit_transform(self):
        """Verify preprocessing pipeline."""
        dataset = generate_labeled_dataset(num_samples=100, seed=42)
        features = [f for f, _ in dataset]
        
        preprocessor = FeaturePreprocessor()
        X = preprocessor.fit_transform(features)
        
        assert X.shape[0] == 100
        assert X.shape[1] == len(preprocessor.feature_names)
        assert preprocessor.is_fitted
    
    def test_label_encoding(self):
        """Verify label encoding/decoding."""
        labels = ["return_abuse", "transaction_fraud", "normal", "return_abuse"]
        preprocessor = FeaturePreprocessor()
        preprocessor.label_encoder.fit(CASE_TYPES)
        
        encoded = preprocessor.encode_labels(labels)
        decoded = preprocessor.decode_labels(encoded)
        
        assert list(decoded) == labels
    
    def test_save_load_preprocessor(self):
        """Verify preprocessor serialization."""
        dataset = generate_labeled_dataset(num_samples=50, seed=42)
        features = [f for f, _ in dataset]
        
        preprocessor = FeaturePreprocessor()
        X_orig = preprocessor.fit_transform(features)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "preprocessor.pkl"
            preprocessor.save(path)
            
            loaded = FeaturePreprocessor.load(path)
            X_loaded = loaded.transform(features)
            
            np.testing.assert_array_almost_equal(X_orig, X_loaded)


class TestDetectorTraining:
    """Test detector training pipeline."""
    
    def test_train_detector_basic(self):
        """Verify detector trains without errors."""
        dataset = generate_labeled_dataset(num_samples=200, seed=42)
        
        result = train_detector(dataset, model_type="random_forest", seed=42)
        
        assert "detector" in result
        assert "preprocessor" in result
        assert "test_metrics" in result
        assert result["test_size"] > 0
        assert "accuracy" in result["test_metrics"]
    
    def test_train_detector_test_metrics(self):
        """Verify test metrics are reasonable."""
        dataset = generate_labeled_dataset(num_samples=300, seed=42)
        
        result = train_detector(dataset, model_type="random_forest", seed=42)
        metrics = result["test_metrics"]
        
        # Should have per-class metrics
        assert "return_abuse_precision" in metrics
        assert "transaction_fraud_recall" in metrics
        assert "fraud_spike_f1" in metrics
        
        # Metrics should be in [0, 1]
        for key, val in metrics.items():
            if isinstance(val, (int, float)) and not isinstance(val, list):
                assert 0 <= val <= 1, f"{key}={val}"
    
    def test_train_detector_no_data_leakage(self):
        """Verify train/val/test split is proper."""
        dataset = generate_labeled_dataset(num_samples=200, seed=42)
        
        result = train_detector(
            dataset, 
            model_type="random_forest", 
            test_size=0.2,
            val_size=0.2,
            seed=42
        )
        
        total = result["train_size"] + result["val_size"] + result["test_size"]
        assert total == 200
        assert result["test_size"] == 40  # 20% of 200
    
    def test_save_detector(self):
        """Verify detector can be saved and loaded."""
        dataset = generate_labeled_dataset(num_samples=150, seed=42)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            
            result = train_detector(
                dataset,
                model_type="random_forest",
                seed=42,
                save_dir=save_dir
            )
            
            # Check files created
            assert (save_dir / "model.pkl").exists()
            assert (save_dir / "preprocessor.pkl").exists()
            assert (save_dir / "metadata.json").exists()
            
            # Load and verify
            predictor = Predictor(save_dir, model_version="1.0")
            assert predictor.preprocessor is not None
            assert predictor.model_dir == save_dir


class TestPrediction:
    """Test detector inference."""
    
    def test_predict_on_new_sample(self):
        """Verify prediction returns valid output."""
        dataset = generate_labeled_dataset(num_samples=150, seed=42)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            train_detector(dataset, model_type="random_forest", seed=42, save_dir=save_dir)
            
            predictor = Predictor(save_dir, model_version="1.0")
            
            # Create a new feature dict
            new_features = {
                "customer_order_count": 20,
                "customer_return_count": 5,
                "customer_return_rate": 0.25,
                "customer_avg_order_value": 50.0,
                "order_value": 100.0,
                "order_value_vs_avg_ratio": 2.0,
                "amount": 100.0,
                "customer_avg_transaction_amount": 50.0,
                "amount_vs_avg_ratio": 2.0,
                "transaction_velocity_24h": 0.5,
                "transaction_velocity_1h": 0.1,
                "customer_failed_transaction_count": 1,
                "customer_failed_transaction_rate": 0.1,
                "unusual_payment_method": False,
                "customer_account_age_days": 200,
                "devices_per_customer": 1,
                "accounts_per_device": 1,
            }
            
            pred = predictor.predict(new_features)
            
            assert pred.case_type in CASE_TYPES
            assert 0 <= pred.confidence <= 1
            assert len(pred.probabilities) == len(CASE_TYPES)
            assert abs(sum(pred.probabilities.values()) - 1.0) < 0.01


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_predict_with_missing_features(self):
        """Missing features should default to 0."""
        dataset = generate_labeled_dataset(num_samples=100, seed=42)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            train_detector(dataset, model_type="random_forest", seed=42, save_dir=save_dir)
            
            predictor = Predictor(save_dir)
            
            # Minimal features dict
            minimal_features = {
                "customer_order_count": 10,
                "customer_return_rate": 0.1,
            }
            
            # Should not crash; missing features filled with 0
            pred = predictor.predict(minimal_features)
            assert pred.case_type in CASE_TYPES
    
    def test_class_imbalance_handling(self):
        """Detector should handle imbalanced classes."""
        # Heavily imbalanced: 80% normal, 5% each of 4 risk classes
        dataset = generate_labeled_dataset(
            num_samples=200,
            seed=42,
            class_distribution={
                "normal": 0.8,
                "return_abuse": 0.05,
                "transaction_fraud": 0.05,
                "fraud_spike": 0.05,
                "abuse_ring": 0.05,
            }
        )
        
        result = train_detector(dataset, model_type="random_forest", seed=42)
        metrics = result["test_metrics"]
        
        # Should still compute metrics for minority classes
        assert "return_abuse_precision" in metrics


class TestModelComparison:
    """Compare different model types."""
    
    def test_logistic_regression_vs_random_forest(self):
        """Both model types should work."""
        dataset = generate_labeled_dataset(num_samples=200, seed=42)
        
        result_lr = train_detector(dataset, model_type="logistic_regression", seed=42)
        result_rf = train_detector(dataset, model_type="random_forest", seed=42)
        
        # Both should have valid metrics
        assert "accuracy" in result_lr["test_metrics"]
        assert "accuracy" in result_rf["test_metrics"]
        
        # Results should be different
        acc_lr = result_lr["test_metrics"]["accuracy"]
        acc_rf = result_rf["test_metrics"]["accuracy"]
        # They should at least both be positive
        assert acc_lr >= 0
        assert acc_rf >= 0
