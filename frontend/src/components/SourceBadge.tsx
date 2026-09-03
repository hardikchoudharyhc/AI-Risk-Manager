import React from 'react';

interface SourceBadgeProps {
  source?: string;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({ source = 'csv' }) => {
  const s = source.toLowerCase();
  let label = 'CSV File';
  let bg = '#F1F5F9';
  let color = '#475569';

  if (s.includes('mock') || s.includes('demo')) {
    label = 'DEMO / MOCK';
    bg = '#FEF3C7';
    color = '#B45309';
  } else if (s.includes('razorpay')) {
    label = 'Razorpay Gateway';
    bg = '#E0F2FE';
    color = '#0369A1';
  } else if (s.includes('shopify')) {
    label = 'Shopify';
    bg = '#DCFCE7';
    color = '#15803D';
  } else if (s.includes('json')) {
    label = 'JSON Payload';
    bg = '#F3E8FF';
    color = '#7E22CE';
  } else if (s.includes('manual') || s.includes('direct')) {
    label = 'Direct Entry';
    bg = '#FEF3C7';
    color = '#B45309';
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
        padding: '0.15rem 0.5rem',
        borderRadius: '4px',
        backgroundColor: bg,
        color: color,
        fontSize: '0.72rem',
        fontWeight: 600,
      }}
    >
      {label}
    </span>
  );
};
