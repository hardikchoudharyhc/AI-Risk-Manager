import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { connectRazorpay, syncRazorpay, fetchRazorpayStatus } from '../services/api';
import { RazorpayStatus } from '../types';

interface RazorpayConnectionProps {
  onBack: () => void;
  onViewTransactions: () => void;
}

export const RazorpayConnection: React.FC<RazorpayConnectionProps> = ({
  onBack,
  onViewTransactions,
}) => {
  const [status, setStatus] = useState<RazorpayStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Inputs
  const [keyId, setKeyId] = useState('rzp_test_mock_123456');
  const [keySecret, setKeySecret] = useState('mock_secret_key_7890');

  const loadStatus = () => {
    setLoading(true);
    setError(null);
    fetchRazorpayStatus()
      .then((data) => {
        setStatus(data);
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

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    setError(null);
    setMessage(null);

    try {
      const res = await connectRazorpay({
        key_id: keyId,
        key_secret: keySecret,
        merchant_id: 'merchant_a',
      });
      setMessage(res.message || 'Successfully connected to Razorpay account.');
      loadStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setConnecting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    setMessage(null);

    try {
      const res = await syncRazorpay({ count: 50 });
      const syncedCount = res.synced_records ?? res.fetched ?? 0;
      const inserted = res.inserted ?? syncedCount;
      const dups = res.duplicates ?? 0;
      const rej = res.rejected ?? 0;
      setMessage(`Successfully synced ${syncedCount} Razorpay transaction records into pipeline. (${inserted} inserted, ${dups} duplicates, ${rej} rejected)`);
      loadStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <LoadingState message="Checking Razorpay connection status..." />;

  const isConnected = status?.status === 'CONNECTED';
  const isMock = status?.environment === 'MOCK / DEMO';

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={onBack} style={styles.backBtn}>
          ← Back to Connected Sources
        </button>
      </div>

      <PageHeader
        title="Razorpay Connection"
        description="Connect your Razorpay API credentials to continuously analyze incoming payment risk."
      />

      {message && (
        <div style={styles.successBanner}>
          ✓ {message}
        </div>
      )}
      {error && <ErrorState message={error} onRetry={loadStatus} />}

      <div style={styles.card}>
        <div style={styles.cardHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.5rem' }}>💳</span>
            <div>
              <h3 style={styles.cardTitle}>Razorpay API Integration</h3>
              <p style={styles.cardSubtitle}>Direct payment gateway API key connection</p>
            </div>
          </div>
          <StatusBadge status={isConnected ? 'CONNECTED' : 'DISCONNECTED'} />
        </div>

        {isConnected ? (
          <div>
            <div style={styles.connectionDetails}>
              <div style={styles.detailBox}>
                <div style={styles.detailLabel}>Environment</div>
                <div style={styles.detailVal}>{status?.environment || 'RAZORPAY TEST MODE'}</div>
              </div>
              <div style={styles.detailBox}>
                <div style={styles.detailLabel}>Masked Key ID</div>
                <div style={styles.detailVal}>rzp_test_••••••••</div>
              </div>
              <div style={styles.detailBox}>
                <div style={styles.detailLabel}>Transactions Synced</div>
                <div style={styles.detailVal}>{status?.total_fetched ?? 0}</div>
              </div>
              <div style={styles.detailBox}>
                <div style={styles.detailLabel}>Risk Analysis Status</div>
                <div style={styles.detailVal}>{status?.total_analyzed ?? 0} evaluated</div>
              </div>
            </div>

            {status?.total_fetched === 0 && !isMock && (
              <div style={styles.emptyAccountBanner}>
                ℹ️ <strong>Razorpay Connected (0 payments found):</strong> Create a Test Mode payment in your Razorpay Dashboard and click "Sync Now" to ingest transactions.
              </div>
            )}

            <div style={styles.btnRow}>
              <button
                onClick={handleSync}
                disabled={syncing}
                style={styles.primaryBtn}
              >
                {syncing ? 'Syncing Transactions...' : 'Sync Now'}
              </button>
              <button
                onClick={onViewTransactions}
                style={styles.secondaryBtn}
              >
                View Synced Transactions
              </button>
              <button
                onClick={() => setStatus({ ...status!, status: 'DISCONNECTED' })}
                style={styles.dangerBtn}
              >
                Disconnect
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleConnect} style={styles.form}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Razorpay Key ID</label>
              <input
                type="text"
                value={keyId}
                onChange={(e) => setKeyId(e.target.value)}
                placeholder="rzp_test_..."
                required
                style={styles.input}
              />
              <span style={styles.hint}>Enter your Razorpay Key ID (Mock keys accepted in Demo environment)</span>
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>Razorpay Key Secret</label>
              <input
                type="password"
                value={keySecret}
                onChange={(e) => setKeySecret(e.target.value)}
                placeholder="••••••••••••••••"
                required
                style={styles.input}
              />
              <span style={styles.hint}>Key secrets are encrypted and masked before transmission</span>
            </div>

            <div style={styles.btnRow}>
              <button
                type="submit"
                disabled={connecting}
                style={styles.primaryBtn}
              >
                {connecting ? 'Testing API Credentials...' : 'Connect Razorpay Account'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  backBtn: {
    border: 'none',
    backgroundColor: 'transparent',
    color: '#2563EB',
    fontWeight: 600,
    fontSize: '0.85rem',
    cursor: 'pointer',
    padding: 0,
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
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1.5rem',
    paddingBottom: '1rem',
    borderBottom: '1px solid #F1F5F9',
  },
  cardTitle: {
    fontSize: '1rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  cardSubtitle: {
    fontSize: '0.78rem',
    color: '#64748B',
    margin: '0.15rem 0 0 0',
  },
  connectionDetails: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    marginBottom: '1.5rem',
  },
  detailBox: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.85rem 1rem',
  },
  detailLabel: {
    fontSize: '0.7rem',
    fontWeight: 600,
    color: '#64748B',
    textTransform: 'uppercase',
  },
  detailVal: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#0F172A',
    marginTop: '0.25rem',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
    maxWidth: '520px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
  },
  label: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#334155',
  },
  input: {
    padding: '0.55rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #CBD5E1',
    fontSize: '0.85rem',
    outline: 'none',
    color: '#0F172A',
  },
  hint: {
    fontSize: '0.72rem',
    color: '#64748B',
  },
  btnRow: {
    display: 'flex',
    gap: '0.75rem',
    marginTop: '0.5rem',
  },
  primaryBtn: {
    padding: '0.55rem 1.25rem',
    backgroundColor: '#2563EB',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryBtn: {
    padding: '0.55rem 1.25rem',
    backgroundColor: '#EFF6FF',
    color: '#2563EB',
    border: '1px solid #BFDBFE',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  dangerBtn: {
    padding: '0.55rem 1.25rem',
    backgroundColor: '#FFFFFF',
    color: '#991B1B',
    border: '1px solid #FCA5A5',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  emptyAccountBanner: {
    padding: '0.85rem 1rem',
    backgroundColor: '#EFF6FF',
    color: '#1E40AF',
    border: '1px solid #BFDBFE',
    borderRadius: '6px',
    fontSize: '0.83rem',
    marginBottom: '1.25rem',
  },
};
