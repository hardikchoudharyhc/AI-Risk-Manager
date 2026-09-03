# 🛡️ AI Risk Manager

An end-to-end, defense-only AI merchant risk & fraud management platform designed to detect, evaluate, and mitigate payment fraud, return abuse, velocity spikes, and organized abuse rings in real-time.

---

## 📌 Project Overview

AI Risk Manager provides an automated risk intelligence pipeline combining machine learning classification, domain-specific heuristic verifiers, SHAP explainability, cost-aware decisioning, automated defensive responses, and compliance-grade audit logging.

It supports heterogeneous merchant transaction ingestion from **CSV files**, **JSON payloads**, and **payment provider integrations (e.g., Razorpay)** while enforcing strict canonical normalization and zero-data-leakage feature engineering.

---

## ✨ Key Features

- **Multi-Source Data Ingestion**: Seamless parsing of raw CSV, JSON arrays, manual direct entries, and webhooks with automatic schema detection.
- **Canonical Schema Normalization**: Pydantic-validated transaction model mapping multi-merchant data into unified internal structures.
- **Zero-Temporal-Leakage Feature Engine**: 38 customer velocity, ratio, device graph, and historical risk features calculated strictly prior to transaction timestamp.
- **Multi-Class Fraud Detector**: Machine learning Random Forest classifier identifying 4 distinct threat classes (`return_abuse`, `transaction_fraud`, `fraud_spike`, `abuse_ring`).
- **Domain Verification & SHAP Explainability**: Post-detector verification combining heuristic business rules with SHAP feature contribution analysis.
- **Canonical 0–100 Risk Score & Level Mapping**: Standardized numeric score output (`0.0` to `100.0`) mapped directly to policy risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Cost-Aware Decision Engine**: Expected loss minimization minimizing false positive / false negative business costs under merchant-configurable policies (`ALLOW`, `MONITOR`, `MANUAL_REVIEW`, `BLOCK`).
- **Automated Defensive Auto-Responder**: Idempotent execution of defensive actions (e.g. 3DS challenge, refund holds, SecOps alerts) without offensive capability.
- **Immutable Compliance Audit Logger**: Automatic append-only audit trail logging every risk decision, rule evaluation, and policy receipt.
- **Interactive Modern React Dashboard**: Enterprise web interface built with React, Vite, and CSS providing real-time analytics, risk queues, investigation drawers, customer profiles, and integration management.

---

## 🏗️ System Architecture

```
                               ┌─────────────────────────┐
                               │ Heterogeneous Data      │
                               │ CSV / JSON / Provider   │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Canonical Normalization │
                               │ & Pydantic Security     │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Feature Engine (38 Feat)│
                               │ Temporal Leakage Free   │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ 4-Class ML Detector     │
                               │ Random Forest Classifier│
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Specialized Verifiers   │
                               │ Rule Engine + SHAP      │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Cost-Aware Decision     │
                               │ Expected Loss Engine    │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Auto-Responder &        │
                               │ Immutable Audit Trail   │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ React UI & FastAPI      │
                               │ Operational Store       │
                               └─────────────────────────┘
```

---

## 🎯 Risk Scoring & Decision Mapping

The system establishes a single canonical representation where **`risk_score` is strictly a floating-point numeric value from `0.0` to `100.0`**.

| Risk Score Range | Risk Level | Automated Decision | Policy Response |
|---|---|---|---|
| **0.0 – 29.9** | `LOW` | `ALLOW` | Auto-approve transaction. |
| **30.0 – 59.9** | `MEDIUM` | `MONITOR` | Log transaction and monitor velocity. |
| **60.0 – 79.9** | `HIGH` | `MANUAL_REVIEW` | Route to Security Analyst Risk Queue. |
| **80.0 – 100.0** | `CRITICAL` | `BLOCK` | Apply immediate defensive block / 3DS challenge. |

*Note: Underlying ML models output probabilities between `0.0` and `1.0`. Scores are converted exactly once at the risk-engine boundary (`score * 100.0`).*

---

## 📥 Ingestion Pipeline (CSV & JSON)

The ingestion pipeline handles raw file uploads or API requests:

1. **Format Auto-Detection**: Inspects raw strings or bytes to distinguish CSV formats from JSON arrays.
2. **Field Normalization**: Maps merchant-specific header aliases (e.g., `user_id` -> `customer_id`, `total` -> `amount`) to canonical schema.
3. **Pydantic Validation**: Validates required fields, numeric constraints (positive amounts), and date parsing.
4. **Deduplication**: Rejects duplicate `transaction_id` entries within identical source sessions.
5. **Quarantine Handling**: Isolates malformed or invalid records into quarantine errors without crashing batch processing.

---

## 🧪 DEMO / MOCK Simulation Environment

AI Risk Manager includes a fully functional, self-contained **DEMO / MOCK Simulation Mode**:

- **Seeded Datasets**: Pre-loaded with representative benchmark transactions (`TXN-NORM-100`, `TXN-RA-100`, `TXN-TF-100`, `TXN-FS-100`, `TXN-RING-100`) covering all 4 threat categories.
- **Explicit Labelling**: All synthetic/mock data sources are clearly tagged in the user interface as `DEMO / MOCK` or `Simulation Mode`.
- **Zero Credentials Needed**: Allows instant evaluation of the risk pipeline, dashboard, transactions list, risk queue, and audit trail out-of-the-box.

---

## 💳 Razorpay Provider Integration Status

- **Architecture**: Implements a dedicated provider adapter (`risk_manager/integrations/razorpay/adapter.py`) adhering to the unified `BaseIntegrationProvider` interface.
- **Real Test Mode Support**: Supports authenticating against `https://api.razorpay.com/v1/payments` using live Test Mode credentials (`rzp_test_*`).
- **Isolation & Error Surfacing**:
  - When real `rzp_test_*` credentials are active, the system fetches actual payment records directly from Razorpay's API.
  - If authentication fails (HTTP 401 Unauthorized) or API key invalidity occurs, the system surfaces the exact 401 error response.
  - **No mock records (`pay_RZP_MOCK_*`) are generated or fallback-injected during Real Test Mode.**
- **KYC Status Note**: Live onboarding/KYC is currently bypassed; production deployment is configured to run via Real Test Mode credentials or isolated Mock Simulation Mode.

---

## ⚙️ Environment Variables

Copy `.env.example` to create your local `.env` file:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `PORT` | FastAPI Backend Server Port | `8000` |
| `HOST` | FastAPI Backend Server Host | `0.0.0.0` |
| `ENVIRONMENT` | Operating environment (`development` / `production`) | `development` |
| `RAZORPAY_KEY_ID` | Razorpay Test Mode Key ID (Optional) | `""` |
| `RAZORPAY_KEY_SECRET` | Razorpay Test Mode Key Secret (Optional) | `""` |
| `VITE_API_BASE_URL` | Frontend API Proxy Endpoint | `http://localhost:8000` |

---

## 🚀 Local Setup & Running Frontend / Backend

### Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+
- **npm**: 10+

### 1. Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -e .
```

### 2. Run Backend (FastAPI Server)
```bash
# Start FastAPI server on http://localhost:8000
PYTHONPATH=. .venv/bin/uvicorn risk_manager.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Run Frontend (React Vite Dev Server)
```bash
# Install frontend dependencies
cd frontend
npm install

# Start Vite dev server on http://localhost:3000
npm run dev
```

Open `http://localhost:3000` in your web browser.

---

## 🧪 Testing

Run the complete backend test suite (131 tests):

```bash
# Run pytest with verbose output
PYTHONPATH=. .venv/bin/pytest -v
```

Build the frontend production bundle:

```bash
# Compile TypeScript & build static Vite bundle
npm run build --prefix frontend
```

---

## 🐳 Docker Usage

Run both the FastAPI backend service and Nginx frontend service using `docker-compose`:

```bash
# Build and launch Docker containers
docker-compose up --build -d
```

- **Frontend Access**: `http://localhost:3000`
- **Backend API Access**: `http://localhost:8000/api/health`

To stop services:
```bash
docker-compose down
```

---

## 🔐 Security & Privacy Controls

- **Zero Hardcoded Secrets**: Secrets and API keys are strictly loaded via environment variables or encrypted connection metadata.
- **Secret Masking**: Key secrets are never logged, stored in plain text, or returned in REST API responses.
- **Input Sanitization**: All file uploads and textual display fields pass through security sanitization against XSS and injection.
- **Version Control Guard**: `.gitignore` strictly excludes `.env`, credential stores, virtual environments, build output, and local databases.

---

## ⚠️ System Limitations & Future Integrations

### Limitations
- **In-Memory Operational Store**: Default storage uses an in-memory `evaluated_store` for instant demonstration. For enterprise multi-node deployments, persistent PostgreSQL or Redis backends are recommended.
- **Local Machine Learning**: Model training occurs on synthetic merchant baselines; re-training scripts require merchant-specific historical chargeback labels.

### Future Integration Roadmap
- **Shopify & WooCommerce Adapters**: Webhook listeners and order risk ingestion handlers for e-commerce platforms.
- **Stripe Integration**: Direct `PaymentIntent` event listener mapping into canonical normalization.
- **PostgreSQL / Redis Operational Store**: Persistent database layer for enterprise scale.