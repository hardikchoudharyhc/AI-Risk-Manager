"""Milestone 3: Case Detector Demo and Evaluation."""
from pathlib import Path
import tempfile
import json

from risk_manager.detector import generate_labeled_dataset, train_detector, Predictor


def main():
    print("=" * 80)
    print("Milestone 3: 4-Class Case Detector")
    print("=" * 80)
    
    # Generate dataset
    print("\n1. Generating synthetic labeled dataset...")
    dataset = generate_labeled_dataset(num_samples=400, seed=42)
    
    class_counts = {}
    for _, case_type in dataset:
        class_counts[case_type] = class_counts.get(case_type, 0) + 1
    
    print(f"   Dataset size: {len(dataset)}")
    print(f"   Class distribution:")
    for case_type, count in sorted(class_counts.items()):
        pct = count / len(dataset) * 100
        print(f"     {case_type:20s}: {count:3d} ({pct:5.1f}%)")
    
    # Train detector
    print("\n2. Training detector (Random Forest)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = Path(tmpdir)
        
        result = train_detector(
            dataset,
            model_type="random_forest",
            test_size=0.2,
            val_size=0.2,
            seed=42,
            save_dir=model_dir,
        )
        
        print(f"   Train: {result['train_size']}")
        print(f"   Validation: {result['val_size']}")
        print(f"   Test (held-out): {result['test_size']}")
        
        # Test metrics
        print("\n3. Held-Out Test Set Evaluation")
        print("-" * 80)
        test_metrics = result["test_metrics"]
        
        print(f"\nAggregate Metrics:")
        print(f"  Accuracy:       {test_metrics['accuracy']:.4f}")
        print(f"  Precision (weighted): {test_metrics['precision_weighted']:.4f}")
        print(f"  Recall (weighted):    {test_metrics['recall_weighted']:.4f}")
        print(f"  F1 (weighted):        {test_metrics['f1_weighted']:.4f}")
        print(f"  Precision (macro):    {test_metrics['precision_macro']:.4f}")
        print(f"  Recall (macro):       {test_metrics['recall_macro']:.4f}")
        print(f"  F1 (macro):           {test_metrics['f1_macro']:.4f}")
        
        # Per-class metrics
        print(f"\nPer-Class Metrics:")
        for case_type in ["return_abuse", "transaction_fraud", "fraud_spike", "abuse_ring", "normal"]:
            prec_key = f"{case_type}_precision"
            rec_key = f"{case_type}_recall"
            f1_key = f"{case_type}_f1"
            pr_auc_key = f"{case_type}_pr_auc"
            
            if prec_key in test_metrics:
                print(f"\n  {case_type.upper()}:")
                print(f"    Precision: {test_metrics[prec_key]:.4f}")
                print(f"    Recall:    {test_metrics[rec_key]:.4f}")
                print(f"    F1:        {test_metrics[f1_key]:.4f}")
                if pr_auc_key in test_metrics:
                    print(f"    PR-AUC:    {test_metrics[pr_auc_key]:.4f}")
        
        # Confusion matrix
        print(f"\nConfusion Matrix:")
        cm = test_metrics["confusion_matrix"]
        case_types = ["return_abuse", "transaction_fraud", "fraud_spike", "abuse_ring", "normal"]
        print("       ", end="")
        for ct in case_types[:5]:
            print(f" {ct[:3]:>4s}", end="")
        print()
        for i, row in enumerate(cm):
            print(f"{case_types[i][:8]:>8s}", end="")
            for val in row[:5]:
                print(f" {val:>4d}", end="")
            print()
        
        # Demo prediction
        print("\n4. Example Predictions")
        print("-" * 80)
        
        predictor = Predictor(model_dir, model_version="1.0.0")
        
        # Sample from each class
        samples_by_class = {}
        for features, case_type in dataset[:100]:
            if case_type not in samples_by_class:
                samples_by_class[case_type] = features
        
        for case_type, features in sorted(samples_by_class.items()):
            pred = predictor.predict(features)
            
            print(f"\n  True Class: {case_type}")
            print(f"  Predicted:  {pred.case_type}")
            print(f"  Confidence: {pred.confidence:.4f}")
            print(f"  Model Version: {pred.model_version}")
            top_probs = sorted(
                pred.probabilities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            print(f"  Top Probabilities:")
            for case, prob in top_probs:
                print(f"    {case:20s}: {prob:.4f}")
        
        # Model metadata
        print("\n5. Model Metadata")
        print("-" * 80)
        with open(model_dir / "metadata.json") as f:
            metadata = json.load(f)
        
        print(f"  Model Type: {metadata['model_type']}")
        print(f"  Training Time: {metadata['training_time']}")
        print(f"  Classes: {', '.join(metadata['classes'])}")
    
    print("\n" + "=" * 80)
    print("M3 Summary:")
    print("  ✓ 4-class detector trained")
    print("  ✓ Held-out test set evaluated")
    print("  ✓ Precision, recall, F1, PR-AUC computed")
    print("  ✓ Class imbalance handled (class_weight='balanced')")
    print("  ✓ Model and preprocessor saved")
    print("  ✓ Inference pipeline functional")
    print("=" * 80)


if __name__ == "__main__":
    main()
