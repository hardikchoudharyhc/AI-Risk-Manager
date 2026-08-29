import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const s = status.toUpperCase();
  let bg = '#F1F5F9';
  let color = '#475569';

  if (s === 'CONNECTED' || s === 'COMPLETED' || s === 'SETTLED' || s === 'SUCCESS') {
    bg = '#DCFCE7';
    color = '#166534';
  } else if (s === 'PENDING' || s === 'PROCESSING' || s === 'QUEUED') {
    bg = '#FEF3C7';
    color = '#92400E';
  } else if (s === 'FAILED' || s === 'REJECTED' || s === 'DISCONNECTED' || s === 'ERROR') {
    bg = '#FEE2E2';
    color = '#991B1B';
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0.15rem 0.5rem',
        borderRadius: '4px',
        backgroundColor: bg,
        color: color,
        fontSize: '0.72rem',
        fontWeight: 600,
        textTransform: 'capitalize',
      }}
    >
      {status}
    </span>
  );
};
