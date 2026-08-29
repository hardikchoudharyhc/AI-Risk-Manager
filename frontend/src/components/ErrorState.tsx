import React from 'react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to load data',
  message,
  onRetry,
}) => {
  return (
    <div
      style={{
        backgroundColor: '#FEF2F2',
        border: '1px solid #FCA5A5',
        borderRadius: '8px',
        padding: '1.5rem 2rem',
        margin: '1rem 0',
      }}
    >
      <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#991B1B', margin: '0 0 0.5rem 0' }}>
        {title}
      </h3>
      <p style={{ fontSize: '0.875rem', color: '#7F1D1D', margin: '0 0 1rem 0' }}>
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '0.4rem 1rem',
            backgroundColor: '#991B1B',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '4px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
      )}
    </div>
  );
};
