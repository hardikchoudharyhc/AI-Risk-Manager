# AI Risk Manager — Project Instructions

## 1. Project Objective

Build a defense-only, production-oriented AI Risk Manager for merchants.

The system must ingest heterogeneous merchant data from different sources and formats, normalize it into a canonical representation, detect the type of loss/risk case, route it to the appropriate verifier, make a cost-aware decision, and generate an appropriate defensive response.

The four supported risk/loss classes are:

1. Return Abuse
2. Transaction Fraud
3. Fraud Spike
4. Abuse Ring

The system must demonstrate:

- Multi-source data ingestion
- Schema mapping
- Data normalization
- Data validation
- Canonical data representation
- Feature engineering
- Four-class case detection
- Specialized verification
- Decision engine
- Automated defensive response
- Audit logging
- Feedback/outcome tracking
- Held-out test evaluation
- Precision
- Recall
- F1
- Confusion matrix
- False-positive cost
- False-negative cost
- Expected loss / loss prevented
- Explainability
- Demo UI
- REST API
- Dockerized deployment

The project must remain strictly defense-only.

Do NOT implement offensive fraud capabilities, attack automation, credential theft, evasion techniques, exploitation, bypass mechanisms, or anything intended to facilitate fraud.

---

# 2. Core Architecture

The complete logical pipeline is:

External Merchant Sources
        ↓
Data Ingestion
        ↓
Source Identification
        ↓
Schema Mapping
        ↓
Normalization
        ↓
Validation
        ↓
Canonical Data Layer
        ↓
Feature Engineering
        ↓
4-Class Case Detector
        ↓
Specialized Verifier
        ↓
Cost-Aware Decision Engine
        ↓
Approve / Review / Defensive Action
        ↓
Auto-Responder
        ↓
Audit Log
        ↓
Outcome / Feedback
        ↓
Evaluation / Monitoring
        ↓
Model Improvement

Do not bypass the canonical data layer.

Do not allow source-specific schemas to leak directly into model code.

---

# 3. Multi-Source Ingestion

The system must conceptually support:

- CSV
- JSON
- REST API
- Webhook
- SQL database
- Event stream

For the initial demo, implement reliable local connectors for:

- CSV
- JSON
- simulated REST API

Design interfaces so additional connectors can be added later without modifying downstream ML code.

Example architecture:

ingestion/
    base.py
    csv_connector.py
    json_connector.py
    api_connector.py
    webhook_connector.py
    database_connector.py

Use interfaces/abstract classes where appropriate.

---

# 4. Heterogeneous Merchant Schemas

Different merchants may use different field names.

Example:

Merchant A:

    cust_id
    order_total
    pay_type
    order_dt

Merchant B:

    customerId
    amount
    paymentMethod
    timestamp

Merchant C:

    user_id
    transaction_value
    payment
    date

All must be converted into the internal canonical schema.

Never write ML code specifically for Merchant A/B/C.

Use merchant-specific mapping configurations.

Example conceptual mapping:

merchant_a:
    cust_id -> customer_id
    order_total -> amount
    pay_type -> payment_method
    order_dt -> timestamp

merchant_b:
    customerId -> customer_id
    amount -> amount
    paymentMethod -> payment_method
    timestamp -> timestamp

Mappings should be configuration-driven wherever practical.

---

# 5. Canonical Data Model

Create a unified internal data representation.

Core entities should include:

## Customer

- customer_id
- account_age_days
- location
- account_created_at

## Order

- order_id
- customer_id
- product_id
- amount
- currency
- timestamp
- order_status
- delivery_status

## Transaction

- transaction_id
- order_id
- customer_id
- amount
- payment_method
- transaction_status
- timestamp

## Return

- return_id
- order_id
- customer_id
- return_reason
- return_status
- timestamp

## Chargeback

- chargeback_id
- transaction_id
- customer_id
- reason
- status
- timestamp

## Device

- device_id
- customer_id
- first_seen
- last_seen

## Address

- address_id
- customer_id
- location

The schema can evolve as implementation progresses, but maintain a clear contract.

---

# 6. Data Normalization

Normalize:

- data types
- timestamps
- currencies
- categorical values
- identifiers
- units
- text representations

Examples:

"23-08-2026"
"2026/08/23"
"2026-08-23"

must become one standardized timestamp representation.

Likewise:

"UPI"
"upi"
"Unified Payments Interface"

must map to:

"UPI"

Never silently discard data during normalization.

Record transformations where useful for auditability.

---

# 7. Data Validation

Before data reaches feature engineering or ML, validate:

- required fields
- data types
- nulls
- duplicate records
- invalid IDs
- impossible values
- negative amounts where invalid
- invalid timestamps
- invalid categories
- schema violations
- suspicious data quality anomalies

Invalid records should be quarantined or rejected with a clear reason.

Do not silently coerce invalid data into misleading values.

Maintain validation statistics.

Example:

    total_records
    valid_records
    invalid_records
    duplicate_records
    missing_required_fields

---

# 8. Canonical Storage

For the demo:

- Parquet/CSV
- SQLite if relational storage is needed

For deployment architecture:

- PostgreSQL
- object storage/data warehouse as appropriate

Do not introduce distributed infrastructure unless it is justified.

---

# 9. Feature Engineering

Features must only use information available at the prediction/decision time.

Avoid target leakage.

Potential features include:

Customer:

- order_count
- return_count
- return_rate
- chargeback_count
- average_order_value
- days_since_last_order
- account_age

Transaction:

- amount
- amount_vs_customer_average
- transaction_velocity
- payment_method
- failed_transaction_count

Return:

- customer_return_rate
- category_return_rate
- recent_return_frequency
- return_value_ratio

Fraud:

- transaction_velocity
- unusual_amount
- unusual_location
- payment_failure_rate
- device_behavior

Abuse ring:

- accounts_per_device
- accounts_per_address
- devices_per_customer
- shared_payment_entities
- graph degree
- suspicious connected components

Fraud spike:

- current_transaction_rate
- historical_transaction_rate
- current_fraud_rate
- historical_fraud_rate
- rolling averages
- rolling standard deviation
- geographic anomaly
- payment-method anomaly

Features should be generated in reusable modules.

---

# 10. Four-Class Detector

The Detector is a routing/classification layer.

Its purpose is:

"What type of risk/loss case is this?"

Classes:

0 = Return Abuse
1 = Transaction Fraud
2 = Fraud Spike
3 = Abuse Ring

The Detector must NOT automatically make the final business decision.

Output should contain:

- predicted_case_type
- confidence/probability
- model_version
- timestamp
- relevant feature/input metadata

Example:

{
    "case_type": "return_abuse",
    "confidence": 0.91
}

The architecture must allow future expansion of classes.

---

# 11. Detector Evaluation

Use proper train/validation/test separation.

The final test set must remain untouched during:

- feature selection
- model selection
- hyperparameter tuning
- threshold selection

Report:

- accuracy
- per-class precision
- per-class recall
- macro F1
- weighted F1
- confusion matrix
- PR-AUC where appropriate

Prefer a time-aware split where the data has meaningful temporal order.

Do not fabricate metrics.

Every metric must be generated from actual evaluation code.

---

# 12. Leakage Prevention

Be extremely strict about temporal leakage.

If predicting whether an order will be returned, do not use information that only exists after the return.

Examples of potentially leaked fields:

- return_processed_date
- refund_status
- return_reason if entered after prediction
- refund_amount
- post-return customer activity

Document every feature's availability time.

---

# 13. Specialized Verifiers

After detection, route the case to the appropriate verifier.

## Return Abuse Verifier

Use:

- customer return history
- order history
- product/category return rates
- return frequency
- return value
- policy conditions

Output:

- verification_status
- confidence
- evidence
- risk_score
- reasons

---

## Transaction Fraud Verifier

Use:

- transaction behavior
- payment behavior
- device information
- location
- historical behavior
- transaction velocity
- anomaly signals

Do not implement offensive fraud techniques.

The verifier only detects/assesses suspicious activity.

---

## Fraud Spike Verifier

Determine whether an apparent spike is:

- genuine anomaly
- expected seasonal/business change
- data pipeline problem
- localized event

Compare current behavior with historical baselines.

Output:

- spike_detected
- confidence
- baseline
- current_value
- deviation
- evidence

---

## Abuse Ring Verifier

Represent relationships between:

- customers
- devices
- addresses
- payment instruments
- orders

Use graph analysis.

Potential tools:

- NetworkX for prototype
- graph database only if justified for deployment

Output:

- suspicious_cluster
- cluster_size
- connected entities
- evidence
- confidence

---

# 14. Chargeback Handling

Chargeback should be treated primarily as an evidence/response workflow.

When a chargeback case occurs:

    Chargeback event
        ↓
    Evidence collection
        ↓
    Transaction verification
        ↓
    Order/delivery evidence
        ↓
    Customer history
        ↓
    Structured evidence package
        ↓
    Merchant review or approved response

The system must not fabricate evidence.

If evidence is missing, explicitly report that it is missing.

If an LLM is used, it must only summarize or organize available evidence.

---

# 15. Verification Principle

Detector asks:

    WHAT TYPE OF CASE IS THIS?

Verifier asks:

    IS THIS ACTUALLY SUSPICIOUS AND WHY?

Decision engine asks:

    WHAT SHOULD WE DO?

Responder asks:

    WHAT ACTION SHOULD BE EXECUTED?

Keep these responsibilities separate.

---

# 16. Decision Engine

The decision engine combines:

- detector result
- verifier result
- risk score
- confidence
- evidence
- merchant policy
- false-positive cost
- false-negative cost
- operational capacity

Possible outcomes:

    APPROVE
    MANUAL_REVIEW
    DEFENSIVE_ACTION

Do not hard-code arbitrary thresholds without documenting why.

Threshold selection should be evaluated against business cost.

---

# 17. Cost Model

At minimum support:

    FP_cost
    FN_cost

Example:

    total_cost =
        false_positives * FP_cost
        +
        false_negatives * FN_cost

Also calculate:

- expected loss
- estimated loss prevented
- review volume
- intervention rate

Allow costs to be configurable.

Do not claim monetary savings without clearly stating assumptions.

---

# 18. Auto-Responder

Responses must be defensive and policy-driven.

Examples:

Return abuse:

- request additional verification
- route to review
- flag case

Transaction fraud:

- alert
- route to review
- apply configured defensive control

Fraud spike:

- alert merchant/security team
- create incident
- recommend investigation

Abuse ring:

- create investigation case
- flag linked entities
- route to review

Chargeback:

- assemble available evidence
- generate structured response draft
- require appropriate merchant approval where necessary

The demo may simulate actions.

Do not integrate irreversible financial actions without explicit safeguards.

---

# 19. Audit Logging

Every decision should be auditable.

Log:

- request/event ID
- merchant ID
- timestamp
- input source
- detector result
- verifier result
- model version
- rule version
- decision
- response
- evidence references
- human override
- final outcome

Do not log sensitive data unnecessarily.

---

# 20. Feedback Loop

After the actual outcome becomes known:

    prediction
        ↓
    action
        ↓
    actual outcome
        ↓
    compare
        ↓
    evaluation dataset

Track:

- true positive
- false positive
- true negative
- false negative
- human override
- confirmed fraud
- confirmed abuse
- confirmed return
- chargeback outcome

This feedback can later be used for retraining.

---

# 21. Demo Application

Build a Streamlit dashboard.

Required screens/components:

## Input

Allow:

- CSV upload
- JSON upload
- sample merchant selection
- simulated event generation

## Detection

Display:

- detected class
- confidence
- probabilities

## Verification

Display:

- verification status
- risk score
- evidence
- reasons

## Decision

Display:

- final decision
- applicable policy
- estimated FP/FN cost

## Response

Display:

- action taken
- generated alert/evidence/response
- audit ID

## Evaluation

Display:

- precision
- recall
- F1
- confusion matrix
- FP/FN
- cost metrics

---

# 22. REST API

Use FastAPI.

Endpoints should eventually include:

    POST /ingest
    POST /detect
    POST /verify
    POST /risk/evaluate
    POST /process
    GET  /case/{case_id}
    GET  /health
    GET  /metrics

Prefer a unified endpoint:

    POST /process

that executes:

    ingestion/validation
        ↓
    detection
        ↓
    verification
        ↓
    decision
        ↓
    response

while retaining individual endpoints for debugging/testing.

---

# 23. Project Structure

Use a modular structure similar to:

    ai-risk-manager/
    │
    ├── AGENTS.md
    ├── README.md
    ├── requirements.txt
    ├── pyproject.toml
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .env.example
    ├── .gitignore
    │
    ├── config/
    │
    ├── data/
    │   ├── raw/
    │   ├── processed/
    │   ├── synthetic/
    │   └── schemas/
    │
    ├── ingestion/
    │
    ├── normalization/
    │
    ├── validation/
    │
    ├── features/
    │
    ├── models/
    │   ├── detector/
    │   ├── return/
    │   ├── fraud/
    │   ├── spike/
    │   └── abuse_ring/
    │
    ├── verification/
    │
    ├── decision/
    │
    ├── responder/
    │
    ├── evaluation/
    │
    ├── api/
    │
    ├── dashboard/
    │
    ├── tests/
    │
    └── scripts/

Adjust structure if implementation reveals a better organization.

---

# 24. Technology Stack

Initial stack:

Python
Pandas
NumPy
Scikit-learn
XGBoost or LightGBM if justified
NetworkX
Matplotlib
Seaborn
SHAP where useful
FastAPI
Pydantic
Streamlit
Pytest
SQLite/PostgreSQL
Docker

Do not introduce:

- Kubernetes
- Kafka
- Spark
- Airflow
- microservices

unless there is a concrete reason.

The prototype should remain understandable and runnable locally.

---

# 25. Development Strategy

Build incrementally.

## Milestone 1

Project foundation:

- repository
- configuration
- schemas
- sample heterogeneous merchant datasets
- ingestion
- mapping
- normalization
- validation

Do NOT build ML yet.

## Milestone 2

Canonical data + feature engineering.

## Milestone 3

Four-class Detector.

Evaluate it on a held-out test set.

## Milestone 4

Specialized verifiers.

## Milestone 5

Decision engine + cost model.

## Milestone 6

Auto-responder + audit logging.

## Milestone 7

End-to-end Streamlit demo.

## Milestone 8

FastAPI.

## Milestone 9

Tests and integration tests.

## Milestone 10

Dockerization and deployment configuration.

## Milestone 11

Monitoring, model versioning, and production hardening.

Do not attempt all milestones in one uncontrolled implementation.

---

# 26. Testing Requirements

Include:

## Unit tests

Test:

- schema mapping
- normalization
- validation
- feature generation
- detector
- verifiers
- decision engine
- responder

## Integration tests

Test:

    input
      ↓
    ingestion
      ↓
    normalization
      ↓
    detection
      ↓
    verification
      ↓
    decision
      ↓
    response

## API tests

Test all important endpoints.

## Data tests

Test:

- malformed input
- missing fields
- duplicate records
- invalid dates
- invalid amounts
- unknown categories
- unseen merchant schema

---

# 27. Real-World Edge Cases

Explicitly consider:

- new customer
- new product
- missing customer history
- missing device
- missing address
- duplicate events
- delayed events
- out-of-order events
- inconsistent merchant IDs
- currency differences
- timezone differences
- class imbalance
- temporal leakage
- concept drift
- model degradation
- API failure
- database failure
- duplicate webhook
- malicious/malformed input
- high request volume
- manual-review capacity limits

Never silently assume clean data.

---

# 28. Security

The system is defense-only.

Implement reasonable protections for:

- input validation
- API authentication design
- secrets through environment variables
- sensitive-data minimization
- secure logging
- request limits
- error handling

Never hard-code credentials.

Do not commit `.env`.

---

# 29. Deployment

The application must run locally using Docker.

Target architecture:

    API Gateway / Load Balancer
            ↓
        FastAPI
            ↓
        Risk Engine
            ↓
    Models + Verifiers
            ↓
        PostgreSQL
            ↓
    Audit / Feedback

For asynchronous/event-driven deployment, provide an extensible event interface.

Do not claim cloud deployment is complete unless it has actually been deployed and tested.

Provide deployment documentation for a reasonable cloud target later.

---

# 30. Model Management

Save:

- model artifact
- preprocessing artifact
- feature version
- model version
- training metadata
- evaluation metrics

The model must be reproducible.

Record:

- dataset version
- training timestamp
- random seed
- model parameters
- feature list

---

# 31. Explainability

For risk decisions, provide human-readable reasons.

Example:

    Risk: HIGH

    Reasons:
    - customer return rate significantly above baseline
    - unusual transaction velocity
    - multiple accounts linked to same device

Explanations must correspond to actual evidence/features.

Do not invent explanations after the fact.

---

# 32. Metrics Honesty

Never fabricate performance.

Never report:

    "95% accuracy"

unless generated from actual evaluation code.

Always distinguish:

- training metrics
- validation metrics
- held-out test metrics

If synthetic data is used, clearly label the evaluation as synthetic/simulated.

Do not imply synthetic metrics represent real-world fraud performance.

---

# 33. Coding Standards

Prefer:

- type hints
- Pydantic models
- clear function boundaries
- configuration-driven behavior
- logging
- docstrings for non-obvious logic
- tests
- deterministic pipelines
- reproducible experiments

Avoid:

- giant notebooks
- hard-coded paths
- hard-coded credentials
- duplicated logic
- hidden global state
- magic thresholds
- unnecessary abstractions

---

# 34. Notebook Policy

Notebooks may be used for:

- EDA
- experiments
- model comparison
- visualization

Production logic must live in Python modules.

The final application must not depend on manually executing notebook cells.

---

# 35. Codex Working Rules

Before modifying code:

1. Inspect the existing repository.
2. Read this AGENTS.md.
3. Identify relevant files.
4. Explain the implementation plan briefly.
5. Implement the smallest coherent change.
6. Run relevant tests.
7. Fix failures.
8. Report what changed and what was tested.

Do not rewrite unrelated files.

Do not delete working functionality without justification.

Do not fabricate external integrations.

If requirements are ambiguous, make the safest reasonable assumption and document it.

When a design decision materially affects architecture, explain it before implementing it.

---

# 36. First Task

Do NOT build the ML model yet.

First:

1. Inspect the repository.
2. Create the project structure.
3. Create canonical Pydantic/data schemas.
4. Create 3 simulated merchants with intentionally different schemas.
5. Implement CSV/JSON ingestion.
6. Implement merchant-specific schema mapping.
7. Implement normalization.
8. Implement validation.
9. Convert all sources into the canonical representation.
10. Add tests for the ingestion/normalization pipeline.
11. Create a simple README explaining how to run Milestone 1.

At the end of Milestone 1, demonstrate:

    Merchant A data
            ↓
    Merchant B data
            ↓
    Merchant C data
            ↓
    ingestion
            ↓
    schema mapping
            ↓
    normalization
            ↓
    validation
            ↓
    unified canonical data

Do not proceed to the detector until Milestone 1 passes its tests.