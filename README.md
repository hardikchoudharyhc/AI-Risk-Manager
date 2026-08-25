# AI Risk Manager

A defense-only merchant risk system for detecting Return Abuse, Transaction Fraud, Fraud Spike, and Abuse Ring.

## Milestone 2 — Feature Engineering

Builds on M1 canonical data. Extracts 38 features for four risk classes with strict temporal leakage prevention.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run Tests

```bash
./.venv/bin/python -m pytest tests/ -q
```

**M1 Tests:** 2 passed (ingestion, normalization, validation)  
**M2 Tests:** 10 passed (feature engineering, temporal leakage, edge cases)  
**Total:** 12/12 ✓

### Run Demos

**M1 — Ingestion & Canonicalization:**
```bash
./.venv/bin/python -m risk_manager.demo
```

**M2 — Feature Inspection:**
```bash
./.venv/bin/python -m risk_manager.demo_m2
```

### Project Structure

```
risk_manager/
  ├── models.py              # Canonical Pydantic schemas
  ├── normalize.py           # Field normalization
  ├── config.py              # Merchant field mappings
  ├── pipeline.py            # Validation pipeline
  ├── demo.py                # M1 end-to-end demo
  ├── demo_m2.py             # M2 feature inspection
  ├── ingestion/             # CSV, JSON, API connectors
  └── features/
      ├── base.py            # Feature base class
      ├── risk_classes.py    # 4-class feature dataclasses
      ├── engine.py          # FeatureEngine (main computation)
      └── __init__.py

tests/
  ├── test_pipeline.py       # M1 tests
  └── test_features.py       # M2 tests (10 tests)

data/synthetic/
  ├── dataset_generator.py   # Synthetic data factory
  └── *.csv/*.json           # Sample merchant data
```

### Feature Groups (38 Total)

**Return Abuse (9):** order_count, return_count, return_rate, avg_order_value, order_value_ratio, category_return_rate, recent_return_frequency, days_since_last_order, account_age

**Transaction Fraud (10):** amount, payment_method, avg_amount, amount_ratio, velocity_24h, velocity_1h, failed_count, failed_rate, unusual_method, days_since_last_txn, account_age

**Fraud Spike (10):** current_txn_rate_1h, historical_txn_rate_24h, txn_rate_deviation, current_fraud_rate_1h, historical_fraud_rate_24h, fraud_rate_deviation, unusual_location, unusual_payment_method, amount_stddev_deviation, spike_severity

**Abuse Ring (9):** accounts_per_device, accounts_per_address, devices_per_customer, shared_payment_methods, graph_degree, suspicious_cluster_size, cluster_density, shared_device_txns, unusual_acct_creation

### Key Design Principles

**Temporal Leakage Prevention:**
- All features computed using only pre-prediction data
- Future transactions/returns/chargebacks excluded
- Custom prediction_time parameter for reproducible evaluation

**Missing Entity Handling:**
- New customers: returns 0s for historical features
- Missing devices/addresses: gracefully degraded to defaults
- No crashes or silent assumptions

**Edge Cases Covered:**
- Zero denominator (safe_divide)
- Empty history
- Duplicate entities
- Timezone-aware datetimes

### Milestone 2 Status

✅ Feature engineering layer  
✅ 4-class feature extraction (38 total features)  
✅ Temporal leakage prevention  
✅ Missing/new entity handling  
✅ Comprehensive test suite (10 tests)  
✅ Feature inspection demo  
✅ Data serialization (Decimal → float, datetime → ISO)

## Milestone 3 — Case Detector

Builds 4-class detector with proper train/val/held-out test split, no leakage, and evaluation metrics.

### Setup

```bash
pip install -e .
```

### Run Tests

```bash
./.venv/bin/python -m pytest tests/ -q
```

**Total:** 26 tests passed (M1: 2, M2: 10, M3: 14)

### Run Demo

```bash
./.venv/bin/python -m risk_manager.demo_m3
```

Shows:
- Dataset composition
- Train/val/test split
- Held-out test metrics: accuracy, precision, recall, F1, PR-AUC
- Per-class evaluation
- Confusion matrix
- Example predictions
- Model metadata

### M3 Audit & Improvements

**Issue Identified:**
Initial synthetic data was unrealistically easy (perfect held-out metrics):
- Feature-label correlation: 0.81 (strong encoding)
- Class separability: 4.29 units apart (well-separated)

**Resolution:**
Improved synthetic data generator to create realistic, overlapping cases:
- Added Gaussian noise to all features
- Created overlapping ranges across classes
- Added ambiguous cases (e.g., fraud-like legit transactions, legit-like fraud)
- Randomized class modifiers to increase variance

**New Held-Out Test Metrics (n=80):**

**Aggregate Performance:**
- Accuracy: 71.25%
- Precision (macro): 70.48%
- Recall (macro): 72.68%
- F1 (macro): 70.08%

**Per-Class Metrics:**
```
Return Abuse:        P=0.6667  R=0.6250  F1=0.6452  PR-AUC=0.7608
Transaction Fraud:   P=0.5294  R=0.6923  F1=0.6000  PR-AUC=0.6655
Fraud Spike:         P=0.5385  R=0.8750  F1=0.6667  PR-AUC=0.8957
Abuse Ring:          P=1.0000  R=0.7273  F1=0.8421  PR-AUC=0.9753
Normal:              P=0.7895  R=0.7143  F1=0.7500  PR-AUC=0.8455
```

**Confusion Matrix (from 80 held-out samples):**
```
          Return  Fraud  Spike  Ring  Normal
Return      10      5      0     0      1
Fraud        0      9      4     0      0
Spike        0      0      7     0      1
Ring         1      1      2    16      2
Normal       4      2      0     0     15
```

**Key Audit Findings:**
- Feature-label correlation: 0.40 (was 0.81) — much weaker encoding
- Class separability: 1.84 units (was 4.29) — overlapping distributions
- Detector shows real confusion patterns (e.g., 50% fraud_spike misclassified)
- Performance varies by class (Ring=84% F1, Fraud=60% F1)

### Model Output Format

```python
DetectorPrediction(
    case_type="return_abuse",
    confidence=0.67,
    probabilities={
        "return_abuse": 0.67,
        "transaction_fraud": 0.15,
        "fraud_spike": 0.08,
        "abuse_ring": 0.05,
        "normal": 0.05,
    },
    model_version="1.0.0",
    timestamp="2026-08-23T12:00:00+00:00"
)
```

## Milestone 4 — Specialized Verifiers

Implements four post-detector verification flows with defense-only logic:
- Return Abuse
- Transaction Fraud
- Fraud Spike
- Abuse Ring

Each verifier combines three evidence channels:
1. Rules evidence: deterministic policy-style checks with explicit rule IDs.
2. ML evidence: verifier-local logistic model probability score.
3. Historical evidence: customer/entity history signal from canonical data.

SHAP is the default explanation layer in the project environment.
Coefficient-based explanation is retained only as an emergency fallback for runtime
environments where SHAP cannot be loaded.

### Verification Output Contract

Every verifier returns:
- verification_status: VERIFIED_SUSPICIOUS | VERIFIED_NOT_SUSPICIOUS | INCONCLUSIVE
- risk_score: 0-1
- confidence: 0-1
- evidence and reasons
- applicable_rules (rule evaluations)
- model explanation (SHAP when available)
- model_version and rule_version

### M4 Components

```
risk_manager/verification/
  ├── types.py         # RuleEvaluation, ModelExplanation, VerificationResult
  ├── ml_explainer.py  # ML evidence model + SHAP/fallback explanation
  ├── base.py          # Shared verification orchestration
  ├── verifiers.py     # 4 specialized verifiers
  ├── service.py       # Routing layer from case_type -> verifier
  └── __init__.py
```

### Edge Case Handling

- New/low-history entities: confidence is reduced and edge flags are attached.
- Missing customer/device/address links: handled without crashes.
- Missing ML features: imputed with safe defaults and flagged in evidence.

### Run Tests

```bash
./.venv/bin/python -m pytest tests/ -q
```

Includes:
- M1 ingestion tests
- M2 feature tests
- M3 detector tests
- M4 verifier unit/integration tests

## Milestone 5 — Cost-Aware Decision Engine

Adds a configuration-driven decision layer that consumes detector and verifier outputs,
computes expected loss per action, and returns the safest low-loss action.

### Supported Decisions

- APPROVE
- MANUAL_REVIEW
- DEFENSIVE_ACTION

### Inputs Used

- detector result (case type, confidence, probabilities, model version)
- verifier result (verification status, risk score, confidence, evidence, rules, versions)
- merchant policy thresholds and costs

### Configuration-Driven Policy

Policy file: [config/merchant_policies.json](config/merchant_policies.json)

Defines:
- merchant-to-policy mapping
- risk thresholds
- confidence thresholds
- false-positive and false-negative costs
- manual-review residual error/cost assumptions

No decision thresholds or FP/FN costs are hard-coded in business flow.

### Expected Loss Model

- APPROVE loss = risk_probability * false_negative_cost
- DEFENSIVE_ACTION loss = (1 - risk_probability) * false_positive_cost
- MANUAL_REVIEW loss = review_cost + residual FN + residual FP

Decision selection is restricted by policy/uncertainty guardrails, then minimizes expected loss.

### Uncertainty and Edge-Case Safety

- Missing customer or low-history entities reduce confidence.
- Missing features/links are flagged and trigger conservative routing.
- Low-confidence cases default to MANUAL_REVIEW unless emergency-risk threshold is exceeded.

### M5 Modules

```
risk_manager/decision/
  ├── policy.py       # Policy registry and config loading
  ├── engine.py       # Cost-aware decision logic
  ├── types.py        # Decision result contract
  └── __init__.py
```

### M5 Testing

Tests cover:
- policy loading and merchant resolution
- decision contract
- uncertainty-safe manual review behavior
- expected-loss calculation correctness
- end-to-end detector/verifier/decision integration

## Milestone 6 — Auto-Responder Layer & Audit Logging

Implements an automated, policy-driven defensive auto-responder layer and audit logger on top of the Decision Engine output.

### Key Capabilities

- **Strict Decision Consumption**: Consumes only Decision Engine results; never overrides detector, verifier, or decision-engine outputs.
- **Defense-Only Action Enforcement**: Strictly non-offensive actions tailored to the four risk classes (`return_abuse`, `transaction_fraud`, `fraud_spike`, `abuse_ring`).
- **Deterministic Response Templates**: Configurable templates defined in [config/response_templates.json](config/response_templates.json) mapping decisions and risk classes to specific machine instructions and user messages.
- **Event Idempotency**: `IdempotencyStore` caches `(merchant_id, event_id)` responses to prevent duplicate defense execution on replay.
- **Complete Audit Trail**: `AuditLogger` generates auditable records including evidence references, rationale, model/rule/policy/template versions, with support for JSONL persistence, human overrides, and final outcome tracking.
- **Safe Fallback Handling**: Gracefully handles missing evidence, edge flags, and unknown case types.

### M6 Modules

```
risk_manager/responder/
  ├── types.py        # ResponseResult, ResponseAction, AuditRecord
  ├── templates.py    # Deterministic template loader and resolver
  ├── idempotency.py  # Thread-safe event idempotency store
  ├── audit.py        # Auditing, override tracking, and JSONL logging
  ├── service.py      # AutoResponder orchestrator
  └── __init__.py
```

### M6 Testing

Tests cover:
- Template loading, resolution, and unknown case fallbacks
- Routing for all 4 risk classes under `DEFENSIVE_ACTION` and `MANUAL_REVIEW`
- Event idempotency and duplicate replay prevention
- Audit logging, version tracking, human override, and final outcome recording
- End-to-end M1 through M6 pipeline integration

## Milestone 7 — End-to-End Pipeline Demo

Presentation-ready demonstration of the complete AI Risk Manager defense-only pipeline across heterogeneous merchant inputs and all 4 risk classes.

### Complete Pipeline Flow

```
Heterogeneous Ingestion (CSV / JSON / REST API)
        ↓
Data Normalization & Validation (Canonical Data Model)
        ↓
Feature Engineering (Leakage-free Customer/Velocity/Graph Features)
        ↓
4-Class Case Detector (Random Forest Multi-Class Classification)
        ↓
Specialized Verifier + SHAP (Rule Checks + Feature Contribution Explanations)
        ↓
Cost-Aware Decision Engine (Expected Loss Minimization + Merchant Policies)
        ↓
Auto-Responder (Deterministic Action Template Selection + Idempotency)
        ↓
Mock Action Adapter (Safe Simulated External Execution & Receipts)
        ↓
Audit Trail (Comprehensive Audit Record Generation)
```

### Running the Demo

Execute the demo script via the CLI:

```bash
./.venv/bin/python -m risk_manager.demo
```

### Demonstration Scenarios Included

1. **Return Abuse (`merchant_a` via CSV)**:
   - Evaluates excessive return velocity / high return value ratios.
   - Triggers `ReturnAbuseVerifier` with SHAP explanations.
   - Minimizes expected loss under `standard` policy.
   - Executes simulated response: `FLAG_RETURN_FOR_STAFF_REVIEW` (holding instant refund and generating barcode drop-off ticket).

2. **Transaction Fraud (`merchant_b` via JSON)**:
   - Evaluates high transaction velocity and card authorization patterns.
   - Triggers `TransactionFraudVerifier` with SHAP explanations.
   - Minimizes expected loss under `strict` policy.
   - Executes simulated response: `STEP_UP_AUTHENTICATION_AND_REVIEW` (dispatching 3DS OTP challenge and queueing review).

3. **Fraud Spike (`merchant_a` via CSV)**:
   - Evaluates gateway traffic velocity anomalies against 24h baselines.
   - Triggers `FraudSpikeVerifier` with deviation metrics.
   - Executes simulated response: `ALERT_OPS_TEAM_FOR_REVIEW` (dispatching SecOps real-time alert).

4. **Abuse Ring (`merchant_c` via REST API)**:
   - Evaluates multi-device linkage and graph connection density.
   - Triggers `AbuseRingVerifier` with cluster connectivity evidence.
   - Executes simulated response: `INVESTIGATION_CASE_QUEUE` (clustering linked devices and applying provisional holds).

### M7 Testing

Run the full test suite:

```bash
./.venv/bin/python -m pytest -v
```