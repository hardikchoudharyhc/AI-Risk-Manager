import React, { useEffect, useState } from 'react';
import { Header } from '../components/Header';
import { connectRazorpay, syncRazorpay, fetchRazorpayStatus, sendRazorpayOutbound } from '../services/api';
import { RazorpayStatus, ProcessResultItem, getEffectiveRiskScore } from '../types';

interface IntegrationsProps {
  onSelectTransaction: (id: string) => void;
}

export const Integrations: React.FC<IntegrationsProps> = ({ onSelectTransaction }) => {
  const [keyId, setKeyId] = useState('rzp_test_mock');
  const [keySecret, setKeySecret] = useState('mock_secret');
  const [statusText, setStatusText] = useState<string>('');
  const [razorpayStatus, setRazorpayStatus] = useState<RazorpayStatus | null>(null);
  const [syncedResults, setSyncedResults] = useState<ProcessResultItem[]>([]);
  const [outboundAck, setOutboundAck] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadStatus = () => {
    fetchRazorpayStatus()
      .then((st) => setRazorpayStatus(st))
      .catch(() => {});
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleTestConnection = async () => {
    setLoading(true);
    setStatusText('');
    try {
      const res = await connectRazorpay({ key_id: keyId, key_secret: keySecret });
      setStatusText(res.message || 'Connection successful!');
      loadStatus();
    } catch (err: any) {
      setStatusText(`Connection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchTransactions = async () => {
    setLoading(true);
    setStatusText('');
    try {
      const res = await syncRazorpay({ count: 20 });
      setSyncedResults(res.pipeline_results);
      setStatusText(`Successfully fetched & evaluated ${res.synced_records} mock Razorpay transactions!`);
      loadStatus();
    } catch (err: any) {
      setStatusText(`Sync failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendResults = async () => {
    if (syncedResults.length === 0) {
      setStatusText('Fetch transactions first before sending outbound risk results.');
      return;
    }
    setLoading(true);
    setStatusText('');
    try {
      const ack = await sendRazorpayOutbound({ results: syncedResults });
      setOutboundAck(ack);
      setStatusText(`Outbound dispatch complete! ${ack.total_acknowledged} records acknowledged.`);
      loadStatus();
    } catch (err: any) {
      setStatusText(`Outbound failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Header
        title="Merchant Platform Connections"
        subtitle="Manage commercial integration adapters including mock two-way Razorpay sync."
      />

      <div style={styles.grid}>
        {/* Razorpay Integration Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <span style={styles.providerName}>Razorpay Platform Connection</span>
            <span
              style={{
                ...styles.statusBadge,
                backgroundColor: razorpayStatus?.status === 'CONNECTED' ? '#DCFCE7' : '#F1F5F9',
                color: razorpayStatus?.status === 'CONNECTED' ? '#166534' : '#64748B',
              }}
            >
              {razorpayStatus?.status || 'DISCONNECTED'}
            </span>
          </div>

          <div style={styles.envTag}>Environment: {razorpayStatus?.environment || 'MOCK / DEMO'}</div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Razorpay Key ID:</label>
            <input
              type="text"
              value={keyId}
              onChange={(e) => setKeyId(e.target.value)}
              style={styles.input}
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Razorpay Key Secret:</label>
            <input
              type="password"
              value={keySecret}
              onChange={(e) => setKeySecret(e.target.value)}
              style={styles.input}
            />
          </div>

          <div style={styles.btnRow}>
            <button onClick={handleTestConnection} disabled={loading} style={styles.btnSecondary}>
              Test Connection
            </button>
            <button onClick={handleFetchTransactions} disabled={loading} style={styles.btnPrimary}>
              Fetch Transactions
            </button>
            <button onClick={handleSendResults} disabled={loading || syncedResults.length === 0} style={styles.btnGreen}>
              Send Results
            </button>
          </div>

          {statusText && <div style={styles.statusMsg}>{statusText}</div>}
        </div>

        {/* Coming Soon Integrations */}
        <div style={styles.cardDisabled}>
          <div style={styles.cardHeader}>
            <span style={styles.providerName}>Shopify Integration</span>
            <span style={styles.disabledBadge}>Coming Soon</span>
          </div>
          <p style={styles.desc}>Automated Shopify order risk webhooks & dispute management.</p>
        </div>
      </div>

      {syncedResults.length > 0 && (
        <div style={styles.tableCard}>
          <div style={styles.tableTitle}>Fetched & Evaluated Mock Razorpay Transactions ({syncedResults.length})</div>
          <table style={styles.table}>
            <thead>
              <tr>
                <th>RAZORPAY ID</th>
                <th>AMOUNT</th>
                <th>PAYMENT METHOD</th>
                <th>RISK SCORE</th>
                <th>DECISION</th>
                <th>ACTION CODE</th>
                <th>INSPECT</th>
              </tr>
            </thead>
            <tbody>
              {syncedResults.map((item) => (
                <tr key={item.transaction.transaction_id} style={styles.tr}>
                  <td style={styles.idCell}>{item.transaction.transaction_id}</td>
                  <td style={styles.boldCell}>
                    {item.transaction.currency} {item.transaction.amount.toFixed(2)}
                  </td>
                  <td>{item.transaction.payment_method}</td>
                  <td>{(getEffectiveRiskScore(item.risk_assessment) * 100).toFixed(1)}%</td>
                  <td>{item.decision.final_decision}</td>
                  <td style={styles.monoCell}>{item.response.action_code}</td>
                  <td>
                    <button
                      style={styles.inspectBtn}
                      onClick={() => onSelectTransaction(item.transaction.transaction_id)}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.25rem' },
  card: { backgroundColor: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '1.15rem' },
  cardDisabled: { backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '1.15rem', opacity: 0.7 },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' },
  providerName: { fontSize: '0.95rem', fontWeight: 700, color: '#0F172A' },
  statusBadge: { padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700 },
  disabledBadge: { backgroundColor: '#F1F5F9', color: '#64748B', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600 },
  envTag: { fontSize: '0.75rem', color: '#2563EB', fontWeight: 600, marginBottom: '0.85rem' },
  formGroup: { marginBottom: '0.75rem' },
  label: { display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' },
  input: { width: '100%', padding: '0.45rem 0.65rem', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '0.82rem', fontFamily: 'monospace' },
  btnRow: { display: 'flex', gap: '0.5rem', marginTop: '1rem' },
  btnSecondary: { backgroundColor: '#FFFFFF', border: '1px solid #CBD5E1', color: '#334155', borderRadius: '6px', padding: '0.45rem 0.75rem', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer' },
  btnPrimary: { backgroundColor: '#2563EB', border: 'none', color: '#FFFFFF', borderRadius: '6px', padding: '0.45rem 0.75rem', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer' },
  btnGreen: { backgroundColor: '#166534', border: 'none', color: '#FFFFFF', borderRadius: '6px', padding: '0.45rem 0.75rem', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer' },
  statusMsg: { marginTop: '0.85rem', padding: '0.5rem', backgroundColor: '#F1F5F9', borderRadius: '4px', fontSize: '0.78rem', color: '#0F172A' },
  desc: { fontSize: '0.8rem', color: '#64748B' },
  tableCard: { backgroundColor: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '1.15rem' },
  tableTitle: { fontSize: '0.88rem', fontWeight: 700, color: '#0F172A', marginBottom: '0.75rem' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' },
  tr: { borderBottom: '1px solid #F1F5F9' },
  idCell: { fontFamily: 'monospace', color: '#2563EB', fontWeight: 600 },
  boldCell: { fontWeight: 700 },
  monoCell: { fontFamily: 'monospace', fontSize: '0.75rem' },
  inspectBtn: { backgroundColor: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: '4px', padding: '0.2rem 0.5rem', fontSize: '0.72rem', cursor: 'pointer' },
};
