import React from 'react';

interface RiskBadgeProps {
  score?: number;
  level?: string;
  decision?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ score, level, decision }) => {
  let displayLevel = level;
  let bg = '#F1F5F9';
  let color = '#475569';

  if (score !== undefined) {
    const s = score <= 1.0 && score > 0 ? score * 100 : score;
    if (s >= 80) {
      displayLevel = 'CRITICAL';
      bg = '#FEE2E2';
      color = '#991B1B';
    } else if (s >= 60) {
      displayLevel = 'HIGH';
      bg = '#FFEDD5';
      color = '#9A3412';
    } else if (s >= 30) {
      displayLevel = 'MEDIUM';
      bg = '#FEF3C7';
      color = '#92400E';
    } else {
      displayLevel = 'LOW';
      bg = '#DCFCE7';
      color = '#166534';
    }
  } else if (level) {
    const l = level.toUpperCase();
    if (l === 'CRITICAL') {
      displayLevel = 'CRITICAL';
      bg = '#FEE2E2';
      color = '#991B1B';
    } else if (l === 'HIGH') {
      displayLevel = 'HIGH';
      bg = '#FFEDD5';
      color = '#9A3412';
    } else if (l === 'MEDIUM') {
      displayLevel = 'MEDIUM';
      bg = '#FEF3C7';
      color = '#92400E';
    } else {
      displayLevel = 'LOW';
      bg = '#DCFCE7';
      color = '#166534';
    }
  } else if (decision) {
    const d = decision.toUpperCase();
    if (d === 'BLOCK' || d === 'DEFENSIVE_ACTION') {
      displayLevel = 'BLOCK';
      bg = '#FEE2E2';
      color = '#991B1B';
    } else if (d === 'MANUAL_REVIEW' || d === 'HIGH') {
      displayLevel = 'MANUAL REVIEW';
      bg = '#FFEDD5';
      color = '#9A3412';
    } else if (d === 'MONITOR' || d === 'MEDIUM') {
      displayLevel = 'MONITOR';
      bg = '#FEF3C7';
      color = '#92400E';
    } else {
      displayLevel = 'ALLOW';
      bg = '#DCFCE7';
      color = '#166534';
    }
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.2rem 0.55rem',
        borderRadius: '4px',
        backgroundColor: bg,
        color: color,
        fontSize: '0.72rem',
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        lineHeight: 1.2,
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: color,
        }}
      />
      {displayLevel} {score !== undefined ? `(${((score <= 1.0 && score > 0) ? score * 100 : score).toFixed(0)}%)` : ''}
    </span>
  );
};
