import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { fetchRazorpayStatus, syncRazorpay } from '../services/api';
import { RazorpayStatus } from '../types';

interface ConnectedSourcesProps {
  onNavigateRazorpay: () => void;
  onViewTransactions: () => void;
}

export const ConnectedSources: React.FC<ConnectedSourcesProps> = ({
  onNavigateRazorpay,
  onViewTransactions,
}) => {
  const [rzpStatus, setRzpStatus] = useState<RazorpayStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadStatus = () => {
    setLoading(true);
    setError(null);
    fetchRazorpayStatus()
      .then((data) => {
        setRzpStatus(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await syncRazorpay({ count: 20 });
      setMessage(`Successfully synced ${res.fetched_count} mock Razorpay transactions.`);
      loadStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <LoadingState message="Fetching connected sources..." />;

  const isConnected = rzpStatus?.status === 'CONNECTED';

  return (
    <div>
      <PageHeader
        title="Connected Sources"
        description="Connect payment providers and commerce platforms to continuously monitor transaction risk."
      />

      {message && (
        <div style={styles.successBanner}>
          ✓ {message}
        </div>
      )}
      {error && <ErrorState message={error} onRetry={loadStatus} />}

      {/* Connected Sources Section */}
      <div style={styles.sectionHeader}>CONNECTED SOURCES</div>
      <div style={styles.sourcesGrid}>
        {/* Razorpay Integration Card */}
        <div style={styles.card}>
          <div style={styles.cardTop}>
            <div style={styles.providerHeader}>
              <div style={styles.providerIcon}>💳</div>
              <div>
                <h3 style={styles.providerName}>Razorpay</h3>
                <span style={styles.providerCategory}>Payment Gateway Integration</span>
              </div>
            </div>
            <StatusBadge status={isConnected ? 'CONNECTED' : 'DISCONNECTED'} />
          </div>

          <div style={styles.detailsGrid}>
            <div>
              <div style={styles.detailLabel}>Environment</div>
              <div style={styles.detailVal}>{rzpStatus?.environment || 'Demo'}</div>
            </div>
            <div>
              <div style={styles.detailLabel}>Synced Transactions</div>
              <div style={styles.detailVal}>{rzpStatus?.total_fetched || 0}</div>
            </div>
            <div>
              <div style={styles.detailLabel}>Risk Analyzed</div>
              <div style={styles.detailVal}>{rzpStatus?.total_analyzed || 0}</div>
            </div>
          </div>

          <div style={styles.cardActions}>
            {isConnected ? (
              <>
                <button
                  onClick={handleSync}
                  disabled={syncing}
                  style={styles.primaryBtn}
                >
                  {syncing ? 'Syncing...' : 'Sync Now'}
                </button>
                <button
                  onClick={onViewTransactions}
                  style={styles.secondaryBtn}
                >
                  View Transactions
                </button>
                <button
                  onClick={onNavigateRazorpay}
                  style={styles.outlineBtn}
                >
                  Manage Connection
                </button>
              </>
            ) : (
              <button
                onClick={onNavigateRazorpay}
                style={styles.primaryBtn}
              >
                Connect Razorpay Account
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Available Sources Section */}
      <div style={{ ...styles.sectionHeader, marginTop: '2rem' }}>AVAILABLE SOURCES</div>
      <div style={styles.sourcesGrid}>
        {/* Shopify Card */}
        <div style={styles.cardDisabled}>
          <div style={styles.cardTop}>
            <div style={styles.providerHeader}>
              <div style={styles.providerIcon}>🛍️</div>
              <div>
                <h3 style={styles.providerName}>Shopify</h3>
                <span style={styles.providerCategory}>Commerce Platform</span>
              </div>
            </div>
            <span style={styles.comingSoonBadge}>AVAILABLE NEXT</span>
          </div>
          <p style={styles.disabledDesc}>
            Connect your Shopify storefront to continuously ingest orders and fulfillments.
          </p>
          <button style={styles.disabledBtn} disabled>
            Connect Shopify (Coming Soon)
          </button>
        </div>

        {/* WooCommerce Card */}
        <div style={styles.cardDisabled}>
          <div style={styles.cardTop}>
            <div style={styles.providerHeader}>
              <div style={styles.providerIcon}>🛒</div>
              <div>
                <h3 style={styles.providerName}>WooCommerce</h3>
                <span style={styles.providerCategory}>Commerce Platform</span>
              </div>
            </div>
            <span style={styles.comingSoonBadge}>PLANNED</span>
          </div>
          <p style={styles.disabledDesc}>
            Ingest WooCommerce webhooks for real-time payment risk assessment.
          </p>
          <button style={styles.disabledBtn} disabled>
            Connect WooCommerce
          </button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sectionHeader: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#64748B',
    letterSpacing: '0.06em',
    marginBottom: '0.85rem',
  },
  successBanner: {
    padding: '0.75rem 1rem',
    backgroundColor: '#DCFCE7',
    color: '#166534',
    border: '1px solid #86EFAC',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    marginBottom: '1rem',
  },
  sourcesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '1.25rem',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  cardDisabled: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    opacity: 0.85,
  },
  cardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1rem',
  },
  providerHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  providerIcon: {
    fontSize: '1.5rem',
  },
  providerName: {
    fontSize: '1rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  providerCategory: {
    fontSize: '0.75rem',
    color: '#64748B',
  },
  detailsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '0.75rem',
    padding: '0.75rem 0',
    borderTop: '1px solid #F1F5F9',
    borderBottom: '1px solid #F1F5F9',
    marginBottom: '1.25rem',
  },
  detailLabel: {
    fontSize: '0.68rem',
    color: '#64748B',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  detailVal: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#0F172A',
    marginTop: '0.2rem',
  },
  cardActions: {
    display: 'flex',
    gap: '0.5rem',
    flexWrap: 'wrap',
  },
  primaryBtn: {
    padding: '0.5rem 1rem',
    backgroundColor: '#2563EB',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryBtn: {
    padding: '0.5rem 1rem',
    backgroundColor: '#EFF6FF',
    color: '#2563EB',
    border: '1px solid #BFDBFE',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  outlineBtn: {
    padding: '0.5rem 1rem',
    backgroundColor: '#FFFFFF',
    color: '#334155',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  comingSoonBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#64748B',
    backgroundColor: '#E2E8F0',
    padding: '0.15rem 0.4rem',
    borderRadius: '4px',
  },
  disabledDesc: {
    fontSize: '0.8rem',
    color: '#64748B',
    margin: '0.5rem 0 1.25rem 0',
    lineHeight: 1.4,
  },
  disabledBtn: {
    padding: '0.5rem 1rem',
    backgroundColor: '#E2E8F0',
    color: '#94A3B8',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'not-allowed',
  },
};
