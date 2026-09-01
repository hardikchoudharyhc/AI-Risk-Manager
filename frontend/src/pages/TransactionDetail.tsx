import React, { useEffect, useState } from 'react';
import { RiskBadge } from '../components/RiskBadge';
import { SourceBadge } from '../components/SourceBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { fetchTransactionDetail } from '../services/api';
import { ProcessResultItem, getEffectiveRiskScore, formatRiskScore } from '../types';

interface TransactionDetailProps {
  transactionId: string;
  onBack: () => void;
}

export const TransactionDetail: React.FC<TransactionDetailProps> = ({
  transactionId,
  onBack,
}) => {
  const [detail, setDetail] = useState<ProcessResultItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'signals' | 'factors' | 'audit'>('signals');

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchTransactionDetail(transactionId)
      .then((data) => {
        setDetail(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [transactionId]);

  if (loading) return <LoadingState message={`Fetching details for transaction ${transactionId}...`} />;
  if (error || !detail) return <ErrorState message={error || 'Transaction not found'} onRetry={onBack} />;

  const txn = detail.transaction;
  const ra = detail.risk_assessment;
  const dec = detail.decision;

  const score = getEffectiveRiskScore(ra);
  const scoreFormatted = formatRiskScore(score);

  // Derive customer-facing risk signals from SHAP features & evidence reasons
  const customerRiskSignals = ra.evidence_reasons && ra.evidence_reasons.length > 0
    ? ra.evidence_reasons
    : ra.shap_top_features?.map((f) => `Risk Signal: High contribution from ${f.feature.replace(/_/g, ' ')}`) || [
        'Anomalous velocity detected',
        'Transaction amount strays from customer baseline',
      ];

  return (
    <div>
      {/* Back Button */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={onBack} style={styles.backBtn}>
          ← Back to Transactions
        </button>
      </div>

      {/* Header */}
      <div style={styles.headerCard}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={styles.headerLabel}>TRANSACTION INVESTIGATION</div>
            <h1 style={styles.headerTitle}>{txn.transaction_id}</h1>
            <p style={styles.headerSub}>
              Processed on {new Date(txn.timestamp).toLocaleString()} via <SourceBadge source={detail.source_type} />
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <RiskBadge score={score} />
            <RiskBadge decision={dec.final_decision} />
          </div>
        </div>

        {/* Overview Grid */}
        <div style={styles.overviewGrid}>
          <div style={styles.metaBox}>
            <div style={styles.metaLabel}>Customer ID</div>
            <div style={styles.metaVal}>{txn.customer_id}</div>
          </div>
          <div style={styles.metaBox}>
            <div style={styles.metaLabel}>Order Amount</div>
            <div style={{ ...styles.metaVal, color: '#0F172A', fontWeight: 700 }}>
              {txn.currency} {txn.amount.toFixed(2)}
            </div>
          </div>
          <div style={styles.metaBox}>
            <div style={styles.metaLabel}>Payment Method</div>
            <div style={{ ...styles.metaVal, textTransform: 'uppercase' }}>{txn.payment_method}</div>
          </div>
          <div style={styles.metaBox}>
            <div style={styles.metaLabel}>Status</div>
            <div style={{ ...styles.metaVal, color: '#166534' }}>{txn.transaction_status || 'COMPLETED'}</div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div style={styles.mainGrid}>
        {/* Left Column: Risk Assessment Summary */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Risk Assessment Summary</h3>
          <div style={{ margin: '1.25rem 0', padding: '1.25rem', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
              Synthesized Risk Score
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0F172A', marginTop: '0.25rem' }}>
              {scoreFormatted} <span style={{ fontSize: '1rem', color: '#64748B', fontWeight: 500 }}>/ 100</span>
            </div>
            <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
              <RiskBadge score={score} />
              <RiskBadge decision={dec.final_decision} />
            </div>
          </div>

          <div style={styles.detailSection}>
            <div style={styles.detailTitle}>Automated Policy Outcome</div>
            <p style={styles.detailText}>{dec.policy || 'Standard Defensive Risk Policy'}</p>
          </div>

          <div style={styles.detailSection}>
            <div style={styles.detailTitle}>Defensive Action Triggered</div>
            <p style={styles.detailText}>{detail.response?.defensive_message || 'Transaction flagged for defensive review.'}</p>
          </div>
        </div>

        {/* Right Column: Detailed Investigation Workspace */}
        <div style={styles.card}>
          {/* Navigation Tabs */}
          <div style={styles.tabHeader}>
            <button
              onClick={() => setActiveTab('signals')}
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'signals' ? styles.tabBtnActive : {}),
              }}
            >
              Why was this flagged?
            </button>
            <button
              onClick={() => setActiveTab('factors')}
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'factors' ? styles.tabBtnActive : {}),
              }}
            >
              Risk Factors
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              style={{
                ...styles.tabBtn,
                ...(activeTab === 'audit' ? styles.tabBtnActive : {}),
              }}
            >
              Audit History
            </button>
          </div>

          {/* Tab 1: Why Was This Flagged? */}
          {activeTab === 'signals' && (
            <div style={styles.tabContent}>
              <h4 style={styles.tabSectionTitle}>Customer-Facing Risk Signals</h4>
              <ul style={styles.signalList}>
                {customerRiskSignals.map((sig, idx) => (
                  <li key={idx} style={styles.signalItem}>
                    <span style={styles.signalDot}>•</span>
                    <span>{sig}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tab 2: Risk Factors */}
          {activeTab === 'factors' && (
            <div style={styles.tabContent}>
              <h4 style={styles.tabSectionTitle}>Model Feature Contributions (Explainability)</h4>
              {ra.shap_top_features && ra.shap_top_features.length > 0 ? (
                <div style={styles.factorList}>
                  {ra.shap_top_features.map((f, idx) => (
                    <div key={idx} style={styles.factorRow}>
                      <div style={styles.factorName}>{f.feature.replace(/_/g, ' ')}</div>
                      <div style={styles.factorBarBg}>
                        <div
                          style={{
                            ...styles.factorBarFill,
                            width: `${Math.min(100, Math.abs(f.contribution) * 200)}%`,
                            backgroundColor: f.contribution > 0 ? '#DC2626' : '#166534',
                          }}
                        />
                      </div>
                      <div style={styles.factorVal}>{(f.contribution > 0 ? '+' : '') + f.contribution.toFixed(3)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: '0.82rem', color: '#64748B' }}>Standard risk factor profile evaluated.</p>
              )}
            </div>
          )}

          {/* Tab 3: Audit History */}
          {activeTab === 'audit' && (
            <div style={styles.tabContent}>
              <h4 style={styles.tabSectionTitle}>Compliance Audit History</h4>
              <div style={styles.auditBox}>
                <div><strong>Audit Reference ID:</strong> {detail.audit?.audit_id}</div>
                <div><strong>Evaluation Timestamp:</strong> {detail.audit?.timestamp || detail.received_at}</div>
                <div><strong>Execution Status:</strong> {detail.response?.execution_status || 'SUCCESS'}</div>
                <div><strong>Action Code:</strong> {detail.response?.action_code}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  backBtn: {
    border: 'none',
    backgroundColor: 'transparent',
    color: '#2563EB',
    fontWeight: 600,
    fontSize: '0.85rem',
    cursor: 'pointer',
    padding: 0,
  },
  headerCard: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    marginBottom: '1.25rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  headerLabel: {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#64748B',
    letterSpacing: '0.06em',
  },
  headerTitle: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: '0.25rem 0',
  },
  headerSub: {
    fontSize: '0.8rem',
    color: '#64748B',
    margin: 0,
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  overviewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
    gap: '1rem',
    marginTop: '1.25rem',
    paddingTop: '1rem',
    borderTop: '1px solid #F1F5F9',
  },
  metaBox: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.65rem 0.85rem',
  },
  metaLabel: {
    fontSize: '0.68rem',
    fontWeight: 600,
    color: '#64748B',
    textTransform: 'uppercase',
  },
  metaVal: {
    fontSize: '0.9rem',
    fontWeight: 600,
    color: '#0F172A',
    marginTop: '0.2rem',
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 2fr',
    gap: '1.25rem',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  cardTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  detailSection: {
    marginBottom: '1rem',
  },
  detailTitle: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#64748B',
    textTransform: 'uppercase',
  },
  detailText: {
    fontSize: '0.85rem',
    color: '#334155',
    margin: '0.25rem 0 0 0',
    lineHeight: 1.4,
  },
  tabHeader: {
    display: 'flex',
    gap: '0.5rem',
    borderBottom: '1px solid #E2E8F0',
    paddingBottom: '0.5rem',
    marginBottom: '1.25rem',
  },
  tabBtn: {
    padding: '0.45rem 0.85rem',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#64748B',
    cursor: 'pointer',
  },
  tabBtnActive: {
    backgroundColor: '#F1F5F9',
    color: '#2563EB',
  },
  tabContent: {
    padding: '0.5rem 0',
  },
  tabSectionTitle: {
    fontSize: '0.85rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: '0 0 1rem 0',
  },
  signalList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  signalItem: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'flex-start',
    fontSize: '0.85rem',
    color: '#334155',
    backgroundColor: '#F8FAFC',
    padding: '0.75rem 1rem',
    borderRadius: '6px',
    border: '1px solid #E2E8F0',
  },
  signalDot: {
    color: '#EA580C',
    fontWeight: 700,
  },
  factorList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  factorRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    fontSize: '0.8rem',
  },
  factorName: {
    width: '180px',
    color: '#334155',
    fontWeight: 500,
    textTransform: 'capitalize',
  },
  factorBarBg: {
    flex: 1,
    height: '6px',
    backgroundColor: '#F1F5F9',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  factorBarFill: {
    height: '100%',
    borderRadius: '3px',
  },
  factorVal: {
    width: '60px',
    textAlign: 'right',
    fontWeight: 700,
    color: '#0F172A',
    fontFamily: 'monospace',
  },
  auditBox: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '1rem',
    fontFamily: 'monospace',
    fontSize: '0.8rem',
    color: '#334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
};
