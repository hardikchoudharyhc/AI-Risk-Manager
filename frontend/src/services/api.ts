import {
  ProcessResponse,
  ProcessResultItem,
  RazorpayStatus,
  RazorpayOutboundAck,
  AuditLogEntry,
} from '../types';

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function ingestData(payload: {
  data: any;
  merchant_id?: string;
  source_type?: string;
  source_id?: string;
}): Promise<ProcessResponse> {
  const res = await fetch(`${API_BASE}/ingestion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || 'Ingestion failed');
  }
  return res.json();
}

export async function fetchTransactions(params?: {
  search?: string;
  risk_level?: string;
  decision?: string;
  source_type?: string;
  page?: number;
  limit?: number;
}): Promise<{ total: number; page: number; limit: number; transactions: ProcessResultItem[] }> {
  const query = new URLSearchParams();
  if (params?.search) query.append('search', params.search);
  if (params?.risk_level && params.risk_level !== 'ALL') query.append('risk_level', params.risk_level);
  if (params?.decision && params.decision !== 'ALL') query.append('decision', params.decision);
  if (params?.source_type && params.source_type !== 'ALL') query.append('source_type', params.source_type);
  if (params?.page) query.append('page', String(params.page));
  if (params?.limit) query.append('limit', String(params.limit));

  const res = await fetch(`${API_BASE}/transactions?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
}

export async function fetchTransactionDetail(transactionId: string): Promise<ProcessResultItem> {
  const res = await fetch(`${API_BASE}/transactions/${encodeURIComponent(transactionId)}`);
  if (!res.ok) throw new Error(`Transaction ${transactionId} not found`);
  return res.json();
}

export async function fetchRiskQueue(): Promise<{ queue: ProcessResultItem[] }> {
  const res = await fetch(`${API_BASE}/risk/queue`);
  if (!res.ok) throw new Error('Failed to fetch risk queue');
  return res.json();
}

export async function fetchAuditTrail(): Promise<{ audit_trail: AuditLogEntry[] }> {
  const res = await fetch(`${API_BASE}/audit`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function connectRazorpay(credentials: { key_id: string; key_secret: string; merchant_id?: string }) {
  const res = await fetch(`${API_BASE}/integrations/razorpay/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || 'Razorpay connection failed');
  }
  return res.json();
}

export async function syncRazorpay(params?: { connection_id?: string; count?: number }) {
  const res = await fetch(`${API_BASE}/integrations/razorpay/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params || {}),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || 'Razorpay sync failed');
  }
  return res.json();
}

export async function fetchRazorpayStatus(): Promise<RazorpayStatus> {
  const res = await fetch(`${API_BASE}/integrations/razorpay/status`);
  if (!res.ok) throw new Error('Failed to fetch Razorpay status');
  return res.json();
}

export async function sendRazorpayOutbound(params: { connection_id?: string; results: any[] }): Promise<RazorpayOutboundAck> {
  const res = await fetch(`${API_BASE}/integrations/razorpay/send-results`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || 'Outbound dispatch failed');
  }
  return res.json();
}

export async function fetchModelPerformance() {
  const res = await fetch(`${API_BASE}/model/performance`);
  if (!res.ok) throw new Error('Failed to fetch model performance metrics');
  return res.json();
}
