"""Audit M3: Investigate synthetic data quality and model overfitting."""
import numpy as np
from collections import Counter
from sklearn.preprocessing import StandardScaler

from risk_manager.detector import (
    generate_labeled_dataset,
    FeaturePreprocessor,
    CASE_TYPES,
)


def audit_dataset():
    """Comprehensive audit of synthetic dataset."""
    print("=" * 80)
    print("M3 AUDIT: Synthetic Data Quality & Feature Leakage")
    print("=" * 80)
    
    dataset = generate_labeled_dataset(num_samples=400, seed=42)
    features_list = [f for f, _ in dataset]
    labels = [l for _, l in dataset]
    
    # 1. Check for duplicates
    print("\n1. DUPLICATE SAMPLES")
    print("-" * 80)
    
    preprocessor = FeaturePreprocessor()
    X = preprocessor.fit_transform(features_list)
    
    # Convert to tuples for hashing
    X_tuples = [tuple(row) for row in X]
    counter = Counter(X_tuples)
    duplicates = {k: v for k, v in counter.items() if v > 1}
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate feature vectors:")
        for i, (feat_tuple, count) in enumerate(list(duplicates.items())[:5]):
            print(f"  Duplicate {i+1}: {count} occurrences")
    else:
        print("✓ No exact duplicates found")
    
    # 2. Class separability
    print("\n2. CLASS SEPARABILITY (Euclidean Distance)")
    print("-" * 80)
    
    y_enc = preprocessor.encode_labels(labels)
    
    # Compute class centroids
    centroids = {}
    for class_idx, case_type in enumerate(CASE_TYPES):
        mask = y_enc == class_idx
        if mask.sum() > 0:
            centroids[case_type] = X[mask].mean(axis=0)
    
    # Compute pairwise distances between centroids
    from scipy.spatial.distance import euclidean
    
    print("\nCentroid Distances (lower = more overlap):")
    case_types_with_samples = [k for k in CASE_TYPES if k in centroids]
    for i, ct1 in enumerate(case_types_with_samples):
        for ct2 in case_types_with_samples[i+1:]:
            dist = euclidean(centroids[ct1], centroids[ct2])
            print(f"  {ct1:20s} ↔ {ct2:20s}: {dist:.2f}")
    
    # 3. Feature importance via variance analysis
    print("\n3. FEATURE VARIANCE BY CLASS")
    print("-" * 80)
    
    print("\nWithin-class vs between-class variance:")
    for case_type in CASE_TYPES[:3]:  # Show first 3
        class_idx = CASE_TYPES.index(case_type)
        mask = y_enc == class_idx
        if mask.sum() > 0:
            within_var = X[mask].var()
            between_var = X[~mask].var()
            ratio = within_var / between_var if between_var > 0 else 0
            print(f"  {case_type:20s}: within={within_var:.3f}, between={between_var:.3f}, ratio={ratio:.3f}")
    
    # 4. Feature correlation with labels
    print("\n4. FEATURE-LABEL CORRELATION")
    print("-" * 80)
    
    correlations = {}
    for feature_idx, feature_name in enumerate(preprocessor.feature_names):
        feature_col = X[:, feature_idx]
        # Correlation with class (as numeric)
        correlation = np.corrcoef(feature_col, y_enc)[0, 1]
        correlations[feature_name] = abs(correlation)
    
    top_corr = sorted(correlations.items(), key=lambda x: x[1], reverse=True)[:5]
    print("\nTop 5 most correlated features with labels:")
    for feat, corr in top_corr:
        print(f"  {feat:35s}: {corr:.4f}")
    
    # 5. Check if features directly encode labels
    print("\n5. LABEL DETERMINISM CHECK")
    print("-" * 80)
    
    # Try a simple decision rule: sort by top feature
    if top_corr:
        top_feat = top_corr[0][0]
        feat_idx = preprocessor.feature_names.index(top_feat)
        feature_vals = X[:, feat_idx]
        
        print(f"\nUsing top feature '{top_feat}' (correlation={top_corr[0][1]:.4f}):")
        
        # Quantile-based rule
        thresholds = np.percentile(feature_vals, [25, 50, 75])
        
        for class_idx, case_type in enumerate(CASE_TYPES):
            mask = y_enc == class_idx
            if mask.sum() > 0:
                vals = feature_vals[mask]
                print(f"  {case_type:20s}: mean={vals.mean():.2f}, std={vals.std():.2f}, "
                      f"min={vals.min():.2f}, max={vals.max():.2f}")
    
    # 6. Class imbalance
    print("\n6. CLASS DISTRIBUTION")
    print("-" * 80)
    
    counts = Counter(labels)
    print("\nClass counts:")
    for case_type, count in sorted(counts.items()):
        pct = count / len(labels) * 100
        print(f"  {case_type:20s}: {count:3d} ({pct:5.1f}%)")
    
    # 7. Feature range comparison
    print("\n7. FEATURE RANGES BY CLASS")
    print("-" * 80)
    
    feat_to_check = "customer_return_rate"
    if feat_to_check in preprocessor.feature_names:
        feat_idx = preprocessor.feature_names.index(feat_to_check)
        print(f"\nRaw feature '{feat_to_check}' by class:")
        for case_type in CASE_TYPES[:3]:
            idx = CASE_TYPES.index(case_type)
            mask = y_enc == idx
            if mask.sum() > 0:
                # Get raw values from original features_list
                raw_vals = [f.get(feat_to_check, 0) for i, (f, l) in enumerate(dataset) if l == case_type]
                raw_vals = [float(v) if not isinstance(v, float) else v for v in raw_vals]
                if raw_vals:
                    print(f"  {case_type:20s}: mean={np.mean(raw_vals):.3f}, "
                          f"std={np.std(raw_vals):.3f}, "
                          f"overlap with others")
    
    # 8. Check separability in raw feature space
    print("\n8. RAW FEATURE DISTRIBUTIONS")
    print("-" * 80)
    
    print("\nSample raw features for return_abuse vs transaction_fraud:")
    ra_samples = [f for f, l in dataset if l == "return_abuse"][:3]
    tf_samples = [f for f, l in dataset if l == "transaction_fraud"][:3]
    
    if ra_samples and tf_samples:
        print("\nReturn Abuse samples:")
        for i, sample in enumerate(ra_samples[:1]):
            print(f"  Sample {i+1}:")
            print(f"    return_rate: {sample.get('customer_return_rate', 0):.3f}")
            print(f"    velocity_24h: {sample.get('transaction_velocity_24h', 0):.3f}")
            print(f"    failed_rate: {sample.get('customer_failed_transaction_rate', 0):.3f}")
        
        print("\nTransaction Fraud samples:")
        for i, sample in enumerate(tf_samples[:1]):
            print(f"  Sample {i+1}:")
            print(f"    return_rate: {sample.get('customer_return_rate', 0):.3f}")
            print(f"    velocity_24h: {sample.get('transaction_velocity_24h', 0):.3f}")
            print(f"    failed_rate: {sample.get('customer_failed_transaction_rate', 0):.3f}")
    
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    
    # Heuristic: if centroid distances > 5 and top correlation > 0.8, data is separable
    if case_types_with_samples:
        min_dist = min(
            euclidean(centroids[case_types_with_samples[i]], centroids[case_types_with_samples[j]])
            for i in range(len(case_types_with_samples))
            for j in range(i+1, len(case_types_with_samples))
        )
        max_corr = max(correlations.values()) if correlations else 0
        
        print(f"\nKey Metrics:")
        print(f"  Min centroid distance: {min_dist:.2f} (>5 = well-separated)")
        print(f"  Max feature-label correlation: {max_corr:.4f} (>0.8 = strong encoding)")
        print(f"  Duplicates found: {len(duplicates)}")
        
        if min_dist > 5 and max_corr > 0.7:
            print("\n⚠️  WARNING: Data appears UNREALISTICALLY SEPARABLE")
            print("   - Classes have distinct centroids (>5 units apart)")
            print("   - Features strongly encode labels (correlation >0.7)")
            print("   - Perfect metrics likely due to easy classification")
            print("\n   RECOMMENDATION: Add noise, overlapping ranges, ambiguous cases")
        else:
            print("\n✓ Data appears reasonably realistic")


if __name__ == "__main__":
    audit_dataset()
