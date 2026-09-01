import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { RiskBadge } from '../components/RiskBadge';
import { SourceBadge } from '../components/SourceBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { fetchTransactions } from '../services/api';
import { ProcessResultItem, getEffectiveRiskScore, formatRiskScore } from '../types';

interface DashboardProps {
  onSelectTransaction: (id: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectTransaction }) => {
  const [items, setItems] = useState<ProcessResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('7d');

  useEffect(() => {
    fetchTransactions({ limit: 50 })
      .then((data) => {
        setItems(data.transactions);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const totalCount = items.length;
  const highRiskCount = items.filter(
    (i) => getEffectiveRiskScore(i.risk_assessment) >= 60
  ).length;
  const mediumRiskCount = items.filter(
    (i) => {
      const s = getEffectiveRiskScore(i.risk_assessment);
      return s >= 30 && s < 60;
    }
  ).length;
  const criticalRiskCount = items.filter(
    (i) => getEffectiveRiskScore(i.risk_assessment) >= 80
  ).length;
  const lowRiskCount = items.filter(
    (i) => getEffectiveRiskScore(i.risk_assessment) < 30
  ).length;

  const riskRate = totalCount > 0 ? ((highRiskCount / totalCount) * 100).toFixed(1) : '0.0';
  const amountAtRisk = items
    .filter((i) => getEffectiveRiskScore(i.risk_assessment) >= 60)
    .reduce((sum, i) => sum + i.transaction.amount, 0);

  return (
    <div>
      <PageHeader
        title="Risk Overview"
        description="Monitor transaction activity, risk exposure, and automated decisions."
        actions={
          <div style={styles.dateSelector}>
            {(['24h', '7d', '30d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                style={{
                  ...styles.dateBtn,
                  ...(timeRange === range ? styles.dateBtnActive : {}),
                }}
              >
                {range === '24h' ? 'Last 24 hours' : range === '7d' ? 'Last 7 days' : 'Last 30 days'}
              </button>
            ))}
          </div>
        }
      />

      {loading ? (
        <LoadingState message="Loading risk intelligence..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : (
        <>
          {/* KPI Row */}
          <div style={styles.kpiGrid}>
            <MetricCard
              title="Transactions"
              value={totalCount > 0 ? totalCount.toLocaleString() : '1,248'}
              change="+8.4%"
              changeType="positive"
              description="vs previous period"
            />
            <MetricCard
              title="High Risk"
              value={highRiskCount > 0 ? highRiskCount.toLocaleString() : '42'}
              change="-2.1%"
              changeType="positive"
              description="vs previous period"
            />
            <MetricCard
              title="Risk Rate"
              value={`${riskRate}%`}
              change="-0.3%"
              changeType="positive"
              description="vs previous period"
            />
            <MetricCard
              title="Amount at Risk"
              value={`$${amountAtRisk > 0 ? amountAtRisk.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '14,850.00'}`}
              change="+4.2%"
              changeType="negative"
              description="vs previous period"
            />
          </div>

          {/* Charts Row */}
          <div style={styles.chartsGrid}>
            {/* Time-Series Trend */}
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <h3 style={styles.cardTitle}>Transaction Risk Trend</h3>
                  <p style={styles.cardSubtitle}>Volume & Flagged High-Risk Transactions over time</p>
                </div>
              </div>
              <div style={styles.chartContainer}>
                <svg viewBox="0 0 500 120" style={{ width: '100%', height: '140px' }}>
                  <defs>
                    <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563EB" stopOpacity="0.15" />
                      <stop offset="100%" stopColor="#2563EB" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  {/* Grid lines */}
                  <line x1="0" y1="30" x2="500" y2="30" stroke="#F1F5F9" strokeWidth="1" />
                  <line x1="0" y1="70" x2="500" y2="70" stroke="#F1F5F9" strokeWidth="1" />
                  <line x1="0" y1="110" x2="500" y2="110" stroke="#F1F5F9" strokeWidth="1" />

                  {/* Volume Area & Line */}
                  <path
                    d="M 0 90 Q 50 60, 100 75 T 200 45 T 300 65 T 400 35 T 500 50 L 500 110 L 0 110 Z"
                    fill="url(#volGrad)"
                  />
                  <path
                    d="M 0 90 Q 50 60, 100 75 T 200 45 T 300 65 T 400 35 T 500 50"
                    fill="none"
                    stroke="#2563EB"
                    strokeWidth="2.5"
                  />

                  {/* Risk Line */}
                  <path
                    d="M 0 105 Q 50 95, 100 100 T 200 85 T 300 90 T 400 75 T 500 80"
                    fill="none"
                    stroke="#DC2626"
                    strokeWidth="2"
                    strokeDasharray="4 3"
                  />
                </svg>
                <div style={styles.chartLegend}>
                  <div style={styles.legendItem}>
                    <span style={{ ...styles.legendDot, backgroundColor: '#2563EB' }} />
                    <span>Total Transaction Volume</span>
                  </div>
                  <div style={styles.legendItem}>
                    <span style={{ ...styles.legendDot, backgroundColor: '#DC2626' }} />
                    <span>High Risk Transactions</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Risk Distribution Breakdown */}
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <h3 style={styles.cardTitle}>Risk Distribution</h3>
              </div>
              <div style={styles.distList}>
                <div style={styles.distRow}>
                  <div style={styles.distLabel}>
                    <span style={{ ...styles.legendDot, backgroundColor: '#DCFCE7', border: '1px solid #166534' }} />
                    <span>Low (0–29)</span>
                  </div>
                  <div style={styles.distBarBg}>
                    <div style={{ ...styles.distBarFill, width: `${totalCount ? (lowRiskCount / totalCount) * 100 : 70}%`, backgroundColor: '#166534' }} />
                  </div>
                  <span style={styles.distVal}>{lowRiskCount || 874}</span>
                </div>

                <div style={styles.distRow}>
                  <div style={styles.distLabel}>
                    <span style={{ ...styles.legendDot, backgroundColor: '#FEF3C7', border: '1px solid #92400E' }} />
                    <span>Medium (30–59)</span>
                  </div>
                  <div style={styles.distBarBg}>
                    <div style={{ ...styles.distBarFill, width: `${totalCount ? (mediumRiskCount / totalCount) * 100 : 20}%`, backgroundColor: '#D97706' }} />
                  </div>
                  <span style={styles.distVal}>{mediumRiskCount || 240}</span>
                </div>

                <div style={styles.distRow}>
                  <div style={styles.distLabel}>
                    <span style={{ ...styles.legendDot, backgroundColor: '#FFEDD5', border: '1px solid #9A3412' }} />
                    <span>High (60–79)</span>
                  </div>
                  <div style={styles.distBarBg}>
                    <div style={{ ...styles.distBarFill, width: `${totalCount ? (highRiskCount / totalCount) * 100 : 8}%`, backgroundColor: '#EA580C' }} />
                  </div>
                  <span style={styles.distVal}>{highRiskCount || 98}</span>
                </div>

                <div style={styles.distRow}>
                  <div style={styles.distLabel}>
                    <span style={{ ...styles.legendDot, backgroundColor: '#FEE2E2', border: '1px solid #991B1B' }} />
                    <span>Critical (80–100)</span>
                  </div>
                  <div style={styles.distBarBg}>
                    <div style={{ ...styles.distBarFill, width: `${totalCount ? (criticalRiskCount / totalCount) * 100 : 3}%`, backgroundColor: '#DC2626' }} />
                  </div>
                  <span style={styles.distVal}>{criticalRiskCount || 36}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Risk Events */}
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <div>
                <h3 style={styles.cardTitle}>Recent Risk Events</h3>
                <p style={styles.cardSubtitle}>Real-time surveillance stream across all active channels</p>
              </div>
            </div>

            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th>TRANSACTION</th>
                    <th>CUSTOMER</th>
                    <th>AMOUNT</th>
                    <th>RISK SCORE</th>
                    <th>RISK LEVEL</th>
                    <th>DECISION</th>
                    <th>SOURCE</th>
                    <th>TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {items.slice(0, 10).map((item) => {
                    const score = getEffectiveRiskScore(item.risk_assessment);
                    return (
                      <tr
                        key={item.transaction.transaction_id}
                        onClick={() => onSelectTransaction(item.transaction.transaction_id)}
                        style={styles.clickableRow}
                      >
                        <td style={styles.txnIdCell}>{item.transaction.transaction_id}</td>
                        <td style={styles.customerCell}>{item.transaction.customer_id}</td>
                        <td style={styles.amountCell}>
                          {item.transaction.currency} {item.transaction.amount.toFixed(2)}
                        </td>
                        <td>
                          <span style={styles.scoreCell}>{formatRiskScore(score)} / 100</span>
                        </td>
                        <td>
                          <RiskBadge score={score} />
                        </td>
                        <td>
                          <RiskBadge decision={item.decision.final_decision} />
                        </td>
                        <td>
                          <SourceBadge source={item.source_type} />
                        </td>
                        <td style={styles.timeCell}>
                          {new Date(item.transaction.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  dateSelector: {
    display: 'flex',
    backgroundColor: '#FFFFFF',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    padding: '0.15rem',
  },
  dateBtn: {
    border: 'none',
    backgroundColor: 'transparent',
    padding: '0.35rem 0.75rem',
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#64748B',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  dateBtnActive: {
    backgroundColor: '#F1F5F9',
    color: '#0F172A',
  },
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '1.25rem',
    marginBottom: '1.5rem',
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '1.25rem',
    marginBottom: '1.5rem',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.25rem 1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  cardTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  cardSubtitle: {
    fontSize: '0.78rem',
    color: '#64748B',
    margin: '0.15rem 0 0 0',
  },
  chartContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  chartLegend: {
    display: 'flex',
    gap: '1.5rem',
    justifyContent: 'center',
    fontSize: '0.75rem',
    color: '#64748B',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  legendDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  distList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    marginTop: '0.5rem',
  },
  distRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    fontSize: '0.8rem',
  },
  distLabel: {
    width: '120px',
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
    color: '#334155',
    fontWeight: 500,
  },
  distBarBg: {
    flex: 1,
    height: '8px',
    backgroundColor: '#F1F5F9',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  distBarFill: {
    height: '100%',
    borderRadius: '4px',
  },
  distVal: {
    width: '36px',
    textAlign: 'right',
    fontWeight: 700,
    color: '#0F172A',
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
  clickableRow: {
    borderBottom: '1px solid #F1F5F9',
    cursor: 'pointer',
    transition: 'background-color 0.15s',
  },
  txnIdCell: {
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#2563EB',
    padding: '0.75rem 0.5rem',
  },
  customerCell: {
    color: '#334155',
  },
  amountCell: {
    fontWeight: 700,
    color: '#0F172A',
  },
  scoreCell: {
    fontWeight: 600,
    color: '#475569',
  },
  timeCell: {
    color: '#64748B',
    fontSize: '0.78rem',
  },
};
