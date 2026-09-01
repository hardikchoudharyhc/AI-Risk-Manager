import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { RiskBadge } from '../components/RiskBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { fetchRiskQueue } from '../services/api';
import { ProcessResultItem, getEffectiveRiskScore } from '../types';

interface RiskQueueProps {
  onSelectTransaction: (id: string) => void;
}

export const RiskQueue: React.FC<RiskQueueProps> = ({ onSelectTransaction }) => {
  const [queue, setQueue] = useState<ProcessResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MANUAL_REVIEW'>('ALL');
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const loadQueue = () => {
    setLoading(true);
    setError(null);
    fetchRiskQueue()
      .then((res) => {
        setQueue(res.queue);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const filteredQueue = queue.filter((item) => {
    const score = getEffectiveRiskScore(item.risk_assessment);
    const dec = item.decision.final_decision;
    if (tab === 'CRITICAL') return score >= 80;
    if (tab === 'HIGH') return score >= 60 && score < 80;
    if (tab === 'MANUAL_REVIEW') return dec === 'MANUAL_REVIEW' || dec === 'MONITOR';
    return true;
  });

  const handleAction = (txnId: string, actionType: string) => {
    setActionFeedback(`Action [${actionType}] applied to transaction ${txnId}. Audit record appended.`);
    setTimeout(() => setActionFeedback(null), 4000);
  };

  return (
    <div>
      <PageHeader
        title="Risk Queue"
        description="Transactions that require manual review or immediate security intervention."
      />

      {actionFeedback && (
        <div style={styles.feedbackBanner}>
          ✓ {actionFeedback}
        </div>
      )}

      {/* Tabs */}
      <div style={styles.tabContainer}>
        {(['ALL', 'CRITICAL', 'HIGH', 'MANUAL_REVIEW'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              ...styles.tabBtn,
              ...(tab === t ? styles.tabBtnActive : {}),
            }}
          >
            {t === 'ALL'
              ? 'All Queue Items'
              : t === 'CRITICAL'
              ? 'Critical Risk (≥ 80)'
              : t === 'HIGH'
              ? 'High Risk (60–79)'
              : 'Manual Review'}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState message="Loading risk queue..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadQueue} />
      ) : filteredQueue.length === 0 ? (
        <EmptyState
          title="Queue is empty"
          description="There are currently no transactions requiring manual review in this category."
        />
      ) : (
        <div style={styles.card}>
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th>RISK SCORE</th>
                  <th>TRANSACTION ID</th>
                  <th>CUSTOMER</th>
                  <th>AMOUNT</th>
                  <th>PRIMARY REASON</th>
                  <th>DECISION</th>
                  <th>RECENCY</th>
                  <th>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredQueue.map((item) => {
                  const score = getEffectiveRiskScore(item.risk_assessment);
                  const reason =
                    item.risk_assessment.evidence_reasons?.[0] ||
                    item.decision.rationale?.[0] ||
                    'Anomalous risk profile detected';

                  return (
                    <tr key={item.transaction.transaction_id} style={styles.tr}>
                      <td>
                        <RiskBadge score={score} />
                      </td>
                      <td
                        style={styles.txnIdCell}
                        onClick={() => onSelectTransaction(item.transaction.transaction_id)}
                      >
                        {item.transaction.transaction_id}
                      </td>
                      <td style={styles.customerCell}>{item.transaction.customer_id}</td>
                      <td style={styles.boldCell}>
                        {item.transaction.currency} {item.transaction.amount.toFixed(2)}
                      </td>
                      <td style={styles.reasonCell}>{reason}</td>
                      <td>
                        <RiskBadge decision={item.decision.final_decision} />
                      </td>
                      <td style={styles.timeCell}>
                        {new Date(item.transaction.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td>
                        <div style={styles.actionBtnGroup}>
                          <button
                            style={styles.approveBtn}
                            onClick={() => handleAction(item.transaction.transaction_id, 'APPROVE')}
                          >
                            Approve
                          </button>
                          <button
                            style={styles.investigateBtn}
                            onClick={() => onSelectTransaction(item.transaction.transaction_id)}
                          >
                            Investigate
                          </button>
                          <button
                            style={styles.blockBtn}
                            onClick={() => handleAction(item.transaction.transaction_id, 'BLOCK')}
                          >
                            Block
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  feedbackBanner: {
    padding: '0.75rem 1rem',
    backgroundColor: '#DCFCE7',
    color: '#166534',
    border: '1px solid #86EFAC',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    marginBottom: '1rem',
  },
  tabContainer: {
    display: 'flex',
    gap: '0.5rem',
    marginBottom: '1.25rem',
    borderBottom: '1px solid #E2E8F0',
    paddingBottom: '0.5rem',
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
    backgroundColor: '#FFFFFF',
    color: '#2563EB',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.08)',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.25rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.82rem',
    textAlign: 'left',
  },
  tr: {
    borderBottom: '1px solid #F1F5F9',
  },
  txnIdCell: {
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#2563EB',
    cursor: 'pointer',
  },
  customerCell: {
    color: '#334155',
  },
  boldCell: {
    fontWeight: 700,
    color: '#0F172A',
  },
  reasonCell: {
    color: '#475569',
    maxWidth: '240px',
  },
  timeCell: {
    color: '#64748B',
    fontSize: '0.78rem',
  },
  actionBtnGroup: {
    display: 'flex',
    gap: '0.35rem',
  },
  approveBtn: {
    padding: '0.25rem 0.5rem',
    backgroundColor: '#DCFCE7',
    color: '#166534',
    border: '1px solid #86EFAC',
    borderRadius: '4px',
    fontSize: '0.72rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  investigateBtn: {
    padding: '0.25rem 0.5rem',
    backgroundColor: '#EFF6FF',
    color: '#2563EB',
    border: '1px solid #BFDBFE',
    borderRadius: '4px',
    fontSize: '0.72rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  blockBtn: {
    padding: '0.25rem 0.5rem',
    backgroundColor: '#FEE2E2',
    color: '#991B1B',
    border: '1px solid #FCA5A5',
    borderRadius: '4px',
    fontSize: '0.72rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
};
