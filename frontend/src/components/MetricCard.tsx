import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  description?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  changeType = 'positive',
  description,
}) => {
  let changeColor = '#64748B';
  if (changeType === 'positive') changeColor = '#166534';
  if (changeType === 'negative') changeColor = '#991B1B';

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '1.25rem 1.5rem',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
        flex: 1,
        minWidth: '200px',
      }}
    >
      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {title}
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0F172A', marginTop: '0.35rem', marginBottom: '0.35rem' }}>
        {value}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem' }}>
        {change && (
          <span style={{ fontWeight: 600, color: changeColor }}>
            {change}
          </span>
        )}
        {description && (
          <span style={{ color: '#64748B' }}>
            {description}
          </span>
        )}
      </div>
    </div>
  );
};
