import React from 'react';

interface PipelineTrackerProps {
  currentStage?: number;
  results?: any;
}

export const PipelineTracker: React.FC<PipelineTrackerProps> = ({ currentStage = 9, results }) => {
  const stages = [
    { code: 'M1', title: 'Detection', desc: 'RF Classifier' },
    { code: 'M2', title: 'Verification', desc: 'SHAP & Evidence' },
    { code: 'M3', title: 'Scoring', desc: 'Composite Risk' },
    { code: 'M4', title: 'Decision', desc: 'Cost-Loss Engine' },
    { code: 'M5', title: 'Responder', desc: 'Defensive Action' },
    { code: 'M6', title: 'Audit', desc: 'Immutable Log' },
    { code: 'M7', title: 'Feedback', desc: 'Label Sync' },
    { code: 'M8', title: 'Adaptive', desc: 'Model Update' },
    { code: 'M9', title: 'Compliance', desc: 'Policy Check' },
  ];

  return (
    <div style={styles.container}>
      <div style={styles.header}>M1–M9 Risk Intelligence Pipeline Execution</div>
      <div style={styles.stagesGrid}>
        {stages.map((stage, idx) => {
          const isComplete = idx + 1 <= currentStage;
          return (
            <div
              key={stage.code}
              style={{
                ...styles.stageCard,
                ...(isComplete ? styles.stageComplete : {}),
              }}
            >
              <div style={styles.stageCode}>{stage.code}</div>
              <div style={styles.stageTitle}>{stage.title}</div>
              <div style={styles.stageDesc}>{stage.desc}</div>
              <div style={{ ...styles.statusDot, backgroundColor: isComplete ? '#166534' : '#94A3B8' }} />
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1rem 1.15rem',
    marginBottom: '1.25rem',
  },
  header: {
    fontSize: '0.78rem',
    fontWeight: 700,
    color: '#475569',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '0.75rem',
  },
  stagesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(9, 1fr)',
    gap: '0.4rem',
  },
  stageCard: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.5rem 0.35rem',
    textAlign: 'center',
    position: 'relative',
  },
  stageComplete: {
    backgroundColor: '#F0FDF4',
    borderColor: '#BBF7D0',
  },
  stageCode: {
    fontSize: '0.75rem',
    fontWeight: 800,
    color: '#0F172A',
  },
  stageTitle: {
    fontSize: '0.68rem',
    fontWeight: 600,
    color: '#334155',
    marginTop: '0.1rem',
  },
  stageDesc: {
    fontSize: '0.6rem',
    color: '#64748B',
    marginTop: '0.1rem',
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    margin: '0.35rem auto 0 auto',
  },
};
