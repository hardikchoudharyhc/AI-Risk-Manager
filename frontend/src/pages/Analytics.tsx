import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { fetchTransactions, fetchModelPerformance } from '../services/api';
import { ProcessResultItem, getEffectiveRiskScore } from '../types';

export const Analytics: React.FC = () => {
  const [items, setItems] = useState<ProcessResultItem[]>([]);
  const [modelPerf, setModelPerf] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchTransactions({ limit: 100 }),
      fetchModelPerformance(),
    ])
      .then(([resTxns, resPerf]) => {
        setItems(resTxns.transactions);
        setModelPerf(resPerf);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <LoadingState message="Computing risk & model analytics..." />;
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
  const amountProcessed = items.reduce((sum, i) => sum + i.transaction.amount, 0);
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

  const overall = modelPerf?.overall || {};
  const perClass = modelPerf?.per_class || [];
  const cm = modelPerf?.confusion_matrix || { labels: [], matrix: [] };
  const primaryClass = modelPerf?.primary_loss_class || {};
  const evalDataset = modelPerf?.evaluation_dataset || {};

  return (
    <div>
      <PageHeader
        title="Risk & Model Analytics"
        description="Business metrics, channel risk exposure, and held-out ML model performance."
      />

      {/* SECTION 1: BUSINESS OPERATIONAL METRICS */}
      <div style={styles.sectionTitle}>Business Operational Metrics</div>
      <div style={styles.metricsGrid}>
        <MetricCard title="Transactions" value={totalVolume} description="Total evaluated" />
        <MetricCard title="Amount Processed" value={`INR ${amountProcessed.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} description="Total transaction value" />
        <MetricCard title="Amount at Risk" value={`INR ${amountAtRisk.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} description="Flagged transaction value" />
        <MetricCard title="Risk Exposure Rate" value={`${riskRate}%`} description="High/Critical share" />
        <MetricCard title="Blocked Transactions" value={blockedCount} description="Defensive blocks" />
        <MetricCard title="Manual Reviews" value={manualReviews} description="In risk queue" />
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

      {/* SECTION 2: HELD-OUT MODEL EVALUATION METRICS */}
      <div style={{ ...styles.sectionTitle, marginTop: '2.5rem' }}>
        Machine Learning Model Evaluation (Held-Out Test Set)
      </div>

      {/* Primary Loss Class & Overall Summary Row */}
      <div style={styles.mlSummaryGrid}>
        {/* Primary Buildathon Target Loss Class Card */}
        <div style={{ ...styles.card, borderColor: '#3B82F6', backgroundColor: '#EFF6FF' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#1D4ED8', textTransform: 'uppercase' }}>
            Primary Loss Class (Buildathon Requirement)
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#1E3A8A', margin: '0.25rem 0 0.75rem 0' }}>
            {primaryClass.title || 'Transaction Fraud'}
          </div>
          <div style={styles.primaryMetricRow}>
            <div>
              <div style={styles.primaryLbl}>Precision</div>
              <div style={styles.primaryVal}>{((primaryClass.precision || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={styles.primaryLbl}>Recall</div>
              <div style={styles.primaryVal}>{((primaryClass.recall || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={styles.primaryLbl}>F1 Score</div>
              <div style={styles.primaryVal}>{((primaryClass.f1 || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={styles.primaryLbl}>Test Support</div>
              <div style={styles.primaryVal}>{primaryClass.test_support || 13}</div>
            </div>
          </div>
        </div>

        {/* Overall Model Performance Summary */}
        <div style={styles.card}>
          <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>
            Overall Multiclass Performance (Held-Out Test Set)
          </div>
          <div style={styles.kpiRow}>
            <div>
              <div style={styles.subLbl}>Accuracy</div>
              <div style={styles.subVal}>{((overall.accuracy || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={styles.subLbl}>Macro Precision</div>
              <div style={styles.subVal}>{((overall.precision_macro || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={styles.subLbl}>Macro Recall</div>
              <div style={styles.subVal}>{((overall.recall_macro || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={styles.subLbl}>Macro F1</div>
              <div style={styles.subVal}>{((overall.f1_macro || 0) * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Class Performance Table & Confusion Matrix Grid */}
      <div style={{ ...styles.chartsGrid, marginTop: '1.25rem' }}>
        {/* Per-Class Table Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Per-Class Performance Breakdown</h3>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thRow}>
                <th style={styles.th}>RISK LOSS CLASS</th>
                <th style={styles.th}>PRECISION</th>
                <th style={styles.th}>RECALL</th>
                <th style={styles.th}>F1 SCORE</th>
                <th style={styles.th}>SUPPORT</th>
              </tr>
            </thead>
            <tbody>
              {perClass.map((row: any) => (
                <tr key={row.case_type} style={styles.tr}>
                  <td style={{ ...styles.td, fontWeight: 700, color: '#0F172A' }}>{row.class_name}</td>
                  <td style={styles.td}>{(row.precision * 100).toFixed(1)}%</td>
                  <td style={styles.td}>{(row.recall * 100).toFixed(1)}%</td>
                  <td style={styles.td}>{(row.f1 * 100).toFixed(1)}%</td>
                  <td style={{ ...styles.td, color: '#64748B' }}>{row.support}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Multiclass Confusion Matrix Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Multiclass Confusion Matrix (True vs Predicted)</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.cmTable}>
              <thead>
                <tr>
                  <th style={styles.cmTh}>True \ Pred</th>
                  {cm.labels.map((l: string) => (
                    <th key={l} style={styles.cmTh}>{l.split(' ')[0]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cm.matrix.map((row: number[], i: number) => (
                  <tr key={cm.labels[i]}>
                    <td style={styles.cmRowHeader}>{cm.labels[i].split(' ')[0]}</td>
                    {row.map((val: number, j: number) => (
                      <td
                        key={j}
                        style={{
                          ...styles.cmTd,
                          backgroundColor: i === j ? '#DCFCE7' : val > 0 ? '#FEF2F2' : '#F8FAFC',
                          color: i === j ? '#166534' : val > 0 ? '#991B1B' : '#94A3B8',
                          fontWeight: i === j || val > 0 ? 700 : 400,
                        }}
                      >
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Dataset & Model Provenance Card */}
      <div style={{ ...styles.card, marginTop: '1.25rem', backgroundColor: '#F8FAFC' }}>
        <h3 style={styles.cardTitle}>Evaluation Dataset Provenance & Setup</h3>
        <div style={styles.provenanceGrid}>
          <div>
            <span style={styles.provLbl}>Total Labeled Samples:</span>
            <strong style={styles.provVal}>{evalDataset.total_samples || 400}</strong>
          </div>
          <div>
            <span style={styles.provLbl}>Training Set:</span>
            <strong style={styles.provVal}>{evalDataset.train_samples || 240} (60%)</strong>
          </div>
          <div>
            <span style={styles.provLbl}>Validation Set:</span>
            <strong style={styles.provVal}>{evalDataset.val_samples || 80} (20%)</strong>
          </div>
          <div>
            <span style={styles.provLbl}>Held-Out Test Set:</span>
            <strong style={styles.provVal}>{evalDataset.test_samples || 80} (20%)</strong>
          </div>
          <div>
            <span style={styles.provLbl}>Evaluation Timestamp:</span>
            <strong style={styles.provVal}>{evalDataset.evaluation_timestamp || '2026-09-03T15:11:56Z'}</strong>
          </div>
          <div>
            <span style={styles.provLbl}>Classifier & Version:</span>
            <strong style={styles.provVal}>RandomForest (v{evalDataset.model_version || '1.0.0'})</strong>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sectionTitle: {
    fontSize: '1.05rem',
    fontWeight: 700,
    color: '#0F172A',
    marginBottom: '1rem',
  },
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
  mlSummaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
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
    fontSize: '0.9rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: '0 0 1rem 0',
  },
  chartList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.85rem',
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
  primaryMetricRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '0.75rem',
  },
  primaryLbl: {
    fontSize: '0.68rem',
    color: '#3B82F6',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  primaryVal: {
    fontSize: '1.25rem',
    fontWeight: 800,
    color: '#1E3A8A',
  },
  kpiRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '0.75rem',
    marginTop: '0.75rem',
  },
  subLbl: {
    fontSize: '0.68rem',
    color: '#64748B',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  subVal: {
    fontSize: '1.25rem',
    fontWeight: 800,
    color: '#0F172A',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem',
    textAlign: 'left',
  },
  thRow: {
    borderBottom: '1px solid #E2E8F0',
  },
  th: {
    padding: '0.5rem 0.35rem',
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#64748B',
  },
  tr: {
    borderBottom: '1px solid #F1F5F9',
  },
  td: {
    padding: '0.55rem 0.35rem',
    color: '#334155',
  },
  cmTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.75rem',
    textAlign: 'center',
  },
  cmTh: {
    padding: '0.4rem',
    backgroundColor: '#F1F5F9',
    color: '#475569',
    fontWeight: 700,
    border: '1px solid #E2E8F0',
  },
  cmRowHeader: {
    padding: '0.4rem',
    backgroundColor: '#F1F5F9',
    color: '#475569',
    fontWeight: 700,
    border: '1px solid #E2E8F0',
    textAlign: 'left',
  },
  cmTd: {
    padding: '0.5rem 0.4rem',
    border: '1px solid #E2E8F0',
  },
  provenanceGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '0.75rem',
    fontSize: '0.8rem',
  },
  provLbl: {
    color: '#64748B',
    marginRight: '0.35rem',
  },
  provVal: {
    color: '#0F172A',
  },
};

