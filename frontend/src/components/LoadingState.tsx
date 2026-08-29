import React from 'react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Loading risk intelligence...' }) => {
  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <div
        style={{
          display: 'inline-block',
          width: '28px',
          height: '28px',
          border: '3px solid #E2E8F0',
          borderTopColor: '#2563EB',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          marginBottom: '0.75rem',
        }}
      />
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      <div style={{ fontSize: '0.875rem', color: '#64748B', fontWeight: 500 }}>{message}</div>
    </div>
  );
};
