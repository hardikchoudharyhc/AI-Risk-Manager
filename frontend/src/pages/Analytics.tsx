import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { fetchTransactions } from '../services/api';
import { ProcessResultItem, getEffectiveRiskScore } from '../types';

export const Analytics: React.FC = () => {
  const [items, setItems] = useState<ProcessResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  if (loading) return <LoadingState message="Computing risk analytics..." />;
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;

  const totalVolume = items.length;
  const highRiskCount = items.filter(
    (i) => getEffectiveRiskScore(i.risk_assessment) >= 60
  ).length;
  const criticalCount = items.filter(
    (i) => getEffectiveRiskScore(i.risk_assessment) >= 80
  ).length;
  const manualReviews = items.filter(
    (i) => i.decision.final_decision === 'MANUAL_REVIEW' || i.decision.final_decision === 'MONITOR'
  ).length;
  const blockedCount = items.filter(
    (i) => i.decision.final_decision === 'BLOCK' || i.decision.final_decision === 'DEFENSIVE_ACTION'
  ).length;

  const riskRate = totalVolume > 0 ? ((highRiskCount / totalVolume) * 100).toFixed(1) : '0.0';
  const amountAtRisk = items
    .filter((i) => getEffectiveRiskScore(i.risk_assessment) >= 60)
    .reduce((sum, i) => sum + i.transaction.amount, 0);

  // Breakdown by Source
  const sourceCounts: Record<string, number> = {};
  items.forEach((i) => {
    const src = i.source_type || 'CSV';
    sourceCounts[src] = (sourceCounts[src] || 0) + 1;
  });

  // Breakdown by Payment Method
  const methodCounts: Record<string, number> = {};
  items.forEach((i) => {
    const pm = i.transaction.payment_method || 'CARD';
    methodCounts[pm] = (methodCounts[pm] || 0) + 1;
  });

  return (
    <div>
      <PageHeader
        title="Risk Analytics"
        description="Understand transaction behavior, risk exposure, and decision trends across all channels."
      />

      {/* Metrics Row */}
      <div style={styles.metricsGrid}>
        <MetricCard title="Transaction Volume" value={totalVolume} description="Total evaluated" />
        <MetricCard title="Risk Exposure Rate" value={`${riskRate}%`} description="High/Critical share" />
        <MetricCard title="Amount at Risk" value={`$${amountAtRisk.toFixed(2)}`} description="Flagged transaction value" />
        <MetricCard title="High-Risk Items" value={highRiskCount} description="Score ≥ 60" />
        <MetricCard title="Critical Risk Items" value={criticalCount} description="Score ≥ 80" />
        <MetricCard title="Manual Reviews" value={manualReviews} description="In investigation queue" />
        <MetricCard title="Blocked Transactions" value={blockedCount} description="Defensive blocks" />
      </div>

      {/* Analytics Charts Grid */}
      <div style={styles.chartsGrid}>
        {/* Risk by Source Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Risk Exposure by Data Source</h3>
          <div style={styles.chartList}>
            {Object.entries(sourceCounts).map(([src, count]) => (
              <div key={src} style={styles.barRow}>
                <div style={styles.barLabel}>{src.toUpperCase()}</div>
                <div style={styles.barBg}>
                  <div
                    style={{
                      ...styles.barFill,
                      width: `${(count / (totalVolume || 1)) * 100}%`,
                      backgroundColor: '#2563EB',
                    }}
                  />
                </div>
                <div style={styles.barVal}>{count}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Risk by Payment Method Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Volume by Payment Method</h3>
          <div style={styles.chartList}>
            {Object.entries(methodCounts).map(([pm, count]) => (
              <div key={pm} style={styles.barRow}>
                <div style={styles.barLabel}>{pm.toUpperCase()}</div>
                <div style={styles.barBg}>
                  <div
                    style={{
                      ...styles.barFill,
                      width: `${(count / (totalVolume || 1)) * 100}%`,
                      backgroundColor: '#059669',
                    }}
                  />
                </div>
                <div style={styles.barVal}>{count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '1rem',
    marginBottom: '1.5rem',
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
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
    margin: '0 0 1.25rem 0',
  },
  chartList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  barRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    fontSize: '0.8rem',
  },
  barLabel: {
    width: '120px',
    fontWeight: 600,
    color: '#334155',
  },
  barBg: {
    flex: 1,
    height: '8px',
    backgroundColor: '#F1F5F9',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: '4px',
  },
  barVal: {
    width: '40px',
    textAlign: 'right',
    fontWeight: 700,
    color: '#0F172A',
  },
};
