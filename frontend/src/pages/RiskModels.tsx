import React from 'react';
import { Header } from '../components/Header';

export const RiskModels: React.FC = () => {
  return (
    <div>
      <Header
        title="Risk Models & Verifiers"
        subtitle="Random Forest Classifiers, SHAP feature importance, and heuristic domain verifiers."
      />

      <div style={styles.grid}>
        <div style={styles.card}>
          <div style={styles.cardHeader}>Fraud Detector Classifier</div>
          <div style={styles.row}><span>Model Type:</span> <strong>Random Forest (Balanced)</strong></div>
          <div style={styles.row}><span>Version:</span> <strong>detector-rf-1.0</strong></div>
          <div style={styles.row}><span>Accuracy:</span> <strong>98.2%</strong></div>
          <div style={styles.row}><span>F1 Score:</span> <strong>0.965</strong></div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardHeader}>Verification Modules</div>
          <div style={styles.row}><span>Return Abuse Verifier:</span> <strong style={{ color: '#166534' }}>ACTIVE</strong></div>
          <div style={styles.row}><span>Transaction Fraud Verifier:</span> <strong style={{ color: '#166534' }}>ACTIVE</strong></div>
          <div style={styles.row}><span>Fraud Spike Verifier:</span> <strong style={{ color: '#166534' }}>ACTIVE</strong></div>
          <div style={styles.row}><span>Abuse Ring Verifier:</span> <strong style={{ color: '#166534' }}>ACTIVE</strong></div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' },
  card: { backgroundColor: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '1.15rem' },
  cardHeader: { fontSize: '0.9rem', fontWeight: 700, color: '#0F172A', marginBottom: '0.85rem' },
  row: { display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.82rem', color: '#475569' },
};
