import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { RiskBadge } from '../components/RiskBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { fetchTransactions } from '../services/api';
import { ProcessResultItem, CustomerRef } from '../types';

interface CustomersProps {
  onSelectTransaction?: (id: string) => void;
}

export const Customers: React.FC<CustomersProps> = ({ onSelectTransaction }) => {
  const [items, setItems] = useState<ProcessResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);

  useEffect(() => {
    fetchTransactions({ limit: 100 })
      .then((res) => {
        setItems(res.transactions);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Compute aggregated customer records from raw transactions
  const customerMap = new Map<string, ProcessResultItem[]>();
  items.forEach((item) => {
    const cid = item.transaction.customer_id;
    if (!customerMap.has(cid)) customerMap.set(cid, []);
    customerMap.get(cid)!.push(item);
  });

  const customers: CustomerRef[] = Array.from(customerMap.entries()).map(([cid, txns]) => {
    const totalVolume = txns.reduce((sum, t) => sum + t.transaction.amount, 0);
    const scores = txns.map((t) => t.risk_assessment.verifier_risk_score ?? t.risk_assessment.risk_score ?? 0);
    const avgScore = scores.reduce((a, b) => a + b, 0) / (scores.length || 1);
    const maxScore = Math.max(...scores, 0);

    let maxLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW';
    if (maxScore >= 0.80) maxLevel = 'CRITICAL';
    else if (maxScore >= 0.60) maxLevel = 'HIGH';
    else if (maxScore >= 0.30) maxLevel = 'MEDIUM';

    const sortedTxns = [...txns].sort(
      (a, b) => new Date(b.transaction.timestamp).getTime() - new Date(a.transaction.timestamp).getTime()
    );

    return {
      customer_id: cid,
      transaction_count: txns.length,
      total_volume: totalVolume,
      avg_risk_score: avgScore,
      max_risk_level: maxLevel,
      last_activity: sortedTxns[0]?.transaction.timestamp || '',
    };
  });

  if (loading) return <LoadingState message="Loading customer risk profiles..." />;
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;

  // Detailed Customer Profile View
  if (selectedCustomerId) {
    const customerTxns = customerMap.get(selectedCustomerId) || [];
    const customerData = customers.find((c) => c.customer_id === selectedCustomerId);
    const highRiskTxns = customerTxns.filter(
      (t) => (t.risk_assessment.verifier_risk_score ?? t.risk_assessment.risk_score ?? 0) >= 0.60
    );

    return (
      <div>
        <div style={{ marginBottom: '1rem' }}>
          <button
            onClick={() => setSelectedCustomerId(null)}
            style={styles.backBtn}
          >
            ← Back to Customers
          </button>
        </div>

        <PageHeader
          title={`Customer Profile: ${selectedCustomerId}`}
          description="Customer-level transaction history, aggregated risk score, and profile activity."
        />

        <div style={styles.profileGrid}>
          {/* Risk Overview Card */}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Current Risk Status</h3>
            <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0F172A' }}>
                {( (customerData?.avg_risk_score ?? 0) * 100).toFixed(0)} / 100
              </div>
              <RiskBadge level={customerData?.max_risk_level} />
            </div>
            <p style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '0.5rem' }}>
              Average risk score across {customerData?.transaction_count} transaction(s).
            </p>
          </div>

          {/* Activity Metrics Card */}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Transaction Summary</h3>
            <div style={styles.summaryStats}>
              <div>
                <div style={styles.statLabel}>Total Volume</div>
                <div style={styles.statVal}>${customerData?.total_volume.toFixed(2)}</div>
              </div>
              <div>
                <div style={styles.statLabel}>High Risk Count</div>
                <div style={styles.statVal}>{highRiskTxns.length}</div>
              </div>
              <div>
                <div style={styles.statLabel}>Last Activity</div>
                <div style={styles.statVal}>
                  {customerData?.last_activity ? new Date(customerData.last_activity).toLocaleDateString() : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Customer Recent Transactions */}
        <div style={{ ...styles.card, marginTop: '1.5rem' }}>
          <h3 style={styles.cardTitle}>Customer Transactions</h3>
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th>TRANSACTION ID</th>
                  <th>AMOUNT</th>
                  <th>PAYMENT METHOD</th>
                  <th>RISK SCORE</th>
                  <th>DECISION</th>
                  <th>TIMESTAMP</th>
                </tr>
              </thead>
              <tbody>
                {customerTxns.map((item) => {
                  const score = item.risk_assessment.verifier_risk_score ?? item.risk_assessment.risk_score ?? 0;
                  return (
                    <tr
                      key={item.transaction.transaction_id}
                      onClick={() => onSelectTransaction && onSelectTransaction(item.transaction.transaction_id)}
                      style={styles.tr}
                    >
                      <td style={styles.txnIdCell}>{item.transaction.transaction_id}</td>
                      <td style={styles.boldCell}>
                        {item.transaction.currency} {item.transaction.amount.toFixed(2)}
                      </td>
                      <td>{item.transaction.payment_method}</td>
                      <td>
                        <RiskBadge score={score} />
                      </td>
                      <td>
                        <RiskBadge decision={item.decision.final_decision} />
                      </td>
                      <td style={styles.timeCell}>
                        {new Date(item.transaction.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // Customer List View
  return (
    <div>
      <PageHeader
        title="Customers"
        description="Monitor customer-level risk metrics, activity history, and exposure."
      />

      {customers.length === 0 ? (
        <EmptyState
          title="No customer records found"
          description="Customer data will be populated automatically when transactions are processed."
        />
      ) : (
        <div style={styles.card}>
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th>CUSTOMER ID</th>
                  <th>TRANSACTIONS</th>
                  <th>TOTAL VOLUME</th>
                  <th>AVG RISK SCORE</th>
                  <th>HIGHEST RISK LEVEL</th>
                  <th>LAST ACTIVITY</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.customer_id} style={styles.tr}>
                    <td style={styles.customerCell}>{c.customer_id}</td>
                    <td style={styles.boldCell}>{c.transaction_count}</td>
                    <td style={styles.boldCell}>${c.total_volume.toFixed(2)}</td>
                    <td style={styles.scoreCell}>{(c.avg_risk_score * 100).toFixed(0)} / 100</td>
                    <td>
                      <RiskBadge level={c.max_risk_level} />
                    </td>
                    <td style={styles.timeCell}>
                      {c.last_activity ? new Date(c.last_activity).toLocaleString() : 'N/A'}
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedCustomerId(c.customer_id)}
                        style={styles.viewBtn}
                      >
                        View Profile
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
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
  profileGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1.5fr',
    gap: '1.25rem',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.25rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  cardTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  summaryStats: {
    display: 'flex',
    gap: '2rem',
    marginTop: '1rem',
  },
  statLabel: {
    fontSize: '0.72rem',
    fontWeight: 600,
    color: '#64748B',
    textTransform: 'uppercase',
  },
  statVal: {
    fontSize: '1.2rem',
    fontWeight: 700,
    color: '#0F172A',
    marginTop: '0.25rem',
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
  customerCell: {
    fontWeight: 600,
    color: '#0F172A',
  },
  boldCell: {
    fontWeight: 700,
    color: '#0F172A',
  },
  scoreCell: {
    fontWeight: 600,
    color: '#334155',
  },
  txnIdCell: {
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#2563EB',
    cursor: 'pointer',
  },
  timeCell: {
    color: '#64748B',
    fontSize: '0.78rem',
  },
  viewBtn: {
    padding: '0.25rem 0.65rem',
    backgroundColor: '#EFF6FF',
    color: '#2563EB',
    border: '1px solid #BFDBFE',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
};
