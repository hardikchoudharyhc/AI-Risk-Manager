export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Decision = 'ALLOW' | 'MONITOR' | 'MANUAL_REVIEW' | 'BLOCK' | 'APPROVE' | 'DEFENSIVE_ACTION';

export interface TransactionRef {
  transaction_id: string;
  order_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  transaction_status: string;
  timestamp: string;
  source_type?: string;
  source_id?: string;
}

export interface ShapFeature {
  feature: string;
  contribution: number;
  value: number;
}

export interface RiskAssessment {
  detected_case: string;
  detector_confidence: number;
  probabilities: Record<string, number>;
  verifier_status: string;
  verifier_risk_score: number;
  risk_score?: number;
  risk_level?: RiskLevel;
  evidence_reasons: string[];
  shap_top_features: ShapFeature[];
}

export interface DecisionDetails {
  final_decision: Decision;
  decision?: Decision;
  risk_level?: RiskLevel;
  policy: string;
  expected_losses_by_action: Record<string, number>;
  rationale: string[];
}

export interface ResponseDetails {
  action_code: string;
  action_type: string;
  defensive_message: string;
  execution_status: string;
}

export interface AuditDetails {
  audit_id: string;
  model_version: string;
  policy_version: string;
  timestamp: string;
}

export interface ProcessResultItem {
  case_id: string;
  source_type: string;
  source_id: string;
  ingestion_id: string;
  received_at: string;
  transaction: TransactionRef;
  risk_assessment: RiskAssessment;
  decision: DecisionDetails;
  response: ResponseDetails;
  audit: AuditDetails;
}

export interface ProcessSummary {
  total_records: number;
  valid_records: number;
  rejected_records: number;
  duplicate_records: number;
  merchant_id: string;
  format_detected: string;
}

export interface ProcessResponse {
  request_id: string;
  summary: ProcessSummary;
  results: ProcessResultItem[];
  quarantine: {
    rejected_count: number;
    errors: string[];
  };
}

export interface RazorpayStatus {
  status: string;
  connection_id?: string;
  environment: string;
  total_fetched: number;
  total_analyzed: number;
  outbound_status: string;
}

export interface RazorpayOutboundAck {
  success: boolean;
  provider: string;
  mode: string;
  total_sent: number;
  total_acknowledged: number;
  acknowledgements: Array<{
    transaction_id: string;
    status: string;
    risk_status: string;
    decision: string;
    action: string;
  }>;
  message?: string;
}

export interface AuditLogEntry {
  audit_id: string;
  transaction_id: string;
  merchant_id: string;
  decision: string;
  action_code: string;
  execution_status: string;
  model_version: string;
  timestamp: string;
}

export interface CustomerRef {
  customer_id: string;
  transaction_count: number;
  total_volume: number;
  avg_risk_score: number;
  max_risk_level: RiskLevel;
  last_activity: string;
}

export function getEffectiveRiskScore(ra?: RiskAssessment | null): number {
  if (!ra) return 0;
  let s = 0;
  if (typeof ra.risk_score === 'number' && !isNaN(ra.risk_score)) {
    s = ra.risk_score;
  } else if (typeof ra.verifier_risk_score === 'number' && !isNaN(ra.verifier_risk_score)) {
    s = ra.verifier_risk_score;
  }
  return s <= 1.0 && s > 0.0 ? s * 100.0 : s;
}

export function formatRiskScore(score: number): string {
  if (typeof score !== 'number' || isNaN(score)) return '0';
  const canonical = score <= 1.0 && score > 0.0 ? score * 100.0 : score;
  return canonical % 1 === 0 ? canonical.toFixed(0) : canonical.toFixed(1);
}


