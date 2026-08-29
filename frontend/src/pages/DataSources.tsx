import React, { useState, useEffect } from 'react';
import { connectRazorpay, syncRazorpay, fetchRazorpayStatus, sendRazorpayOutbound } from '../services/api';
import { RazorpayStatus, ProcessResultItem } from '../types';

interface DataSourcesProps {
  onSelectTransaction: (id: string) => void;
  onNavigatePipeline?: () => void;
}

export const DataSources: React.FC<DataSourcesProps> = ({ onSelectTransaction, onNavigatePipeline }) => {
  const [rzpStatus, setRzpStatus] = useState<RazorpayStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Connection Modal state
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [keyId, setKeyId] = useState('rzp_test_mock');
  const [keySecret, setKeySecret] = useState('mock_secret');
  const [testResult, setTestResult] = useState<string | null>(null);

  // Sync Progress State
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [syncStep, setSyncStep] = useState<'idle' | 'connecting' | 'fetching' | 'ingesting' | 'validating' | 'analyzing' | 'complete'>('idle');
  const [syncMetrics, setSyncMetrics] = useState<{
    fetched: number;
    valid: number;
    rejected: number;
    duplicates: number;
    analyzed: number;
    riskFlagged: number;
    results: ProcessResultItem[];
  } | null>(null);

  // Outbound Dispatch state
  const [outboundLoading, setOutboundLoading] = useState(false);
  const [outboundAck, setOutboundAck] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      const data = await fetchRazorpayStatus();
      setRzpStatus(data);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleTestConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setTestResult(null);

    try {
      const res = await connectRazorpay({ key_id: keyId, key_secret: keySecret, merchant_id: 'merchant_razorpay' });
      setTestResult(`Successfully authenticated! Connection ID: ${res.connection_id}`);
      await loadStatus();
      setTimeout(() => setShowConnectModal(false), 1200);
    } catch (err: any) {
      setError(err.message || 'Connection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncNow = async () => {
    setShowSyncModal(true);
    setSyncStep('connecting');
    setSyncMetrics(null);

    try {
      await new Promise((r) => setTimeout(r, 400));
      setSyncStep('fetching');
      await new Promise((r) => setTimeout(r, 400));
      setSyncStep('ingesting');
      await new Promise((r) => setTimeout(r, 400));
      setSyncStep('validating');
      await new Promise((r) => setTimeout(r, 400));
      setSyncStep('analyzing');

      const res = await syncRazorpay();

      const results: ProcessResultItem[] = res.pipeline_results || [];
      const flagged = results.filter(
        (r) => r.risk_assessment.verifier_risk_score >= 0.7 || r.decision.final_decision !== 'APPROVE'
      ).length;

      setSyncMetrics({
        fetched: res.synced_records || 20,
        valid: res.synced_records || 20,
        rejected: 0,
        duplicates: 0,
        analyzed: results.length,
        riskFlagged: flagged,
        results,
      });

      setSyncStep('complete');
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Sync failed');
      setShowSyncModal(false);
    }
  };

  const handleOutboundDispatch = async () => {
    if (!syncMetrics || syncMetrics.results.length === 0) return;
    setOutboundLoading(true);
    setOutboundAck(null);

    try {
      const outboundPayload = syncMetrics.results.map((r) => ({
        transaction_id: r.transaction.transaction_id,
        risk_level: r.risk_assessment.verifier_risk_score >= 0.8 ? 'HIGH' : 'LOW',
        decision: r.decision.final_decision,
        response_action_code: r.response.action_code,
      }));

      const ack = await sendRazorpayOutbound({
        connection_id: rzpStatus?.connection_id,
        results: outboundPayload,
      });

      setOutboundAck(`Dispatched ${ack.total_acknowledged}/${ack.total_sent} decisions to Mock Razorpay Provider`);
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Outbound dispatch failed');
    } finally {
      setOutboundLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.pageTitle}>Data Sources & Integrations</h1>
          <p style={styles.pageSubtitle}>
            Manage connected merchant payment gateways, e-commerce platforms, and ingestion adapters.
          </p>
        </div>
        <button style={styles.btnPrimary} onClick={() => setShowConnectModal(true)}>
          + Connect Source
        </button>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <span>{error}</span>
          <button style={styles.closeBtn} onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Grid of Data Sources */}
      <div style={styles.grid}>
        {/* Razorpay Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <div style={styles.providerInfo}>
              <div style={styles.providerBadgeRzp}>RZP</div>
              <div>
                <h3 style={styles.cardTitle}>Razorpay Integration</h3>
                <span style={styles.envTag}>Environment: {rzpStatus?.environment || 'MOCK / DEMO'}</span>
              </div>
            </div>
            <span style={rzpStatus?.status === 'active' || rzpStatus?.status === 'CONNECTED' ? styles.statusActive : styles.statusInactive}>
              {rzpStatus?.status === 'active' || rzpStatus?.status === 'CONNECTED' ? '● CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>

          <div style={styles.cardBody}>
            <div style={styles.metricRow}>
              <span style={styles.metricLabel}>Connection ID:</span>
              <span style={styles.metricValue}>{rzpStatus?.connection_id || 'conn_rzp_mock_demo'}</span>
            </div>
            <div style={styles.metricRow}>
              <span style={styles.metricLabel}>Total Synced Records:</span>
              <span style={styles.metricValue}>{rzpStatus?.total_fetched || 0}</span>
            </div>
            <div style={styles.metricRow}>
              <span style={styles.metricLabel}>Analyzed by M1–M9:</span>
              <span style={styles.metricValue}>{rzpStatus?.total_analyzed || 0}</span>
            </div>
            <div style={styles.metricRow}>
              <span style={styles.metricLabel}>Outbound Status:</span>
              <span style={styles.metricValue}>{rzpStatus?.outbound_status || 'IDLE'}</span>
            </div>
          </div>

          <div style={styles.cardFooter}>
            <button style={styles.btnSync} onClick={handleSyncNow}>
              Sync Now
            </button>
            <button style={styles.btnSecondary} onClick={() => setShowConnectModal(true)}>
              Settings
            </button>
          </div>
        </div>

        {/* Shopify Card (Coming Soon) */}
        <div style={{ ...styles.card, opacity: 0.85 }}>
          <div style={styles.cardHeader}>
            <div style={styles.providerInfo}>
              <div style={styles.providerBadgeShopify}>SHO</div>
              <div>
                <h3 style={styles.cardTitle}>Shopify Store Sync</h3>
                <span style={styles.envTag}>E-Commerce Platform</span>
              </div>
            </div>
            <span style={styles.badgeComingSoon}>Coming Soon</span>
          </div>
          <div style={styles.cardBody}>
            <p style={styles.cardDesc}>
              Automated webhook and order ingestion adapter for Shopify merchants. Unified schema mapper ready.
            </p>
          </div>
          <div style={styles.cardFooter}>
            <button style={styles.btnDisabled} disabled>Connect Shopify</button>
          </div>
        </div>

        {/* WooCommerce Card (Coming Soon) */}
        <div style={{ ...styles.card, opacity: 0.85 }}>
          <div style={styles.cardHeader}>
            <div style={styles.providerInfo}>
              <div style={styles.providerBadgeWoo}>WOO</div>
              <div>
                <h3 style={styles.cardTitle}>WooCommerce Adapter</h3>
                <span style={styles.envTag}>WordPress Commerce</span>
              </div>
            </div>
            <span style={styles.badgeComingSoon}>Coming Soon</span>
          </div>
          <div style={styles.cardBody}>
            <p style={styles.cardDesc}>
              Direct transaction and cart checkout risk evaluation adapter for WooCommerce plugin users.
            </p>
          </div>
          <div style={styles.cardFooter}>
            <button style={styles.btnDisabled} disabled>Connect WooCommerce</button>
          </div>
        </div>

        {/* Stripe Card (Coming Soon) */}
        <div style={{ ...styles.card, opacity: 0.85 }}>
          <div style={styles.cardHeader}>
            <div style={styles.providerInfo}>
              <div style={styles.providerBadgeStripe}>STR</div>
              <div>
                <h3 style={styles.cardTitle}>Stripe Gateway</h3>
                <span style={styles.envTag}>Payment Infrastructure</span>
              </div>
            </div>
            <span style={styles.badgeComingSoon}>Coming Soon</span>
          </div>
          <div style={styles.cardBody}>
            <p style={styles.cardDesc}>
              PaymentIntent and Charge event listener feeding into the unified canonical normalization layer.
            </p>
          </div>
          <div style={styles.cardFooter}>
            <button style={styles.btnDisabled} disabled>Connect Stripe</button>
          </div>
        </div>
      </div>

      {/* Connect Drawer / Modal */}
      {showConnectModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>Connect Razorpay Integration</h3>
              <button style={styles.closeBtn} onClick={() => setShowConnectModal(false)}>✕</button>
            </div>
            <form onSubmit={handleTestConnection} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Provider</label>
                <input style={styles.inputDisabled} value="Razorpay Payment Gateway" disabled />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Environment</label>
                <select style={styles.input}>
                  <option value="MOCK">Mock / Demo Simulation Mode</option>
                  <option value="LIVE">Live API Key Mode</option>
                </select>
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>API Key ID</label>
                <input
                  style={styles.input}
                  value={keyId}
                  onChange={(e) => setKeyId(e.target.value)}
                  placeholder="rzp_test_mock"
                  required
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>API Key Secret</label>
                <input
                  type="password"
                  style={styles.input}
                  value={keySecret}
                  onChange={(e) => setKeySecret(e.target.value)}
                  placeholder="mock_secret"
                  required
                />
                <span style={styles.fieldNote}>Secrets are masked and encrypted. Never returned in API responses.</span>
              </div>

              {testResult && <div style={styles.successBanner}>{testResult}</div>}

              <div style={styles.modalFooter}>
                <button type="button" style={styles.btnSecondary} onClick={() => setShowConnectModal(false)}>
                  Cancel
                </button>
                <button type="submit" style={styles.btnPrimary} disabled={loading}>
                  {loading ? 'Testing Connection...' : 'Test Connection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sync Operational Progress Modal */}
      {showSyncModal && (
        <div style={styles.modalOverlay}>
          <div style={{ ...styles.modalContent, width: '560px' }}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>Razorpay Integration Sync</h3>
              {syncStep === 'complete' && (
                <button style={styles.closeBtn} onClick={() => setShowSyncModal(false)}>✕</button>
              )}
            </div>

            <div style={styles.syncProgressBody}>
              <div style={styles.pipelineSteps}>
                <div style={styles.stepItem(syncStep !== 'idle')}>
                  <span style={styles.stepBadge}>1</span> Connecting to Razorpay Provider
                </div>
                <div style={styles.stepItem(['fetching', 'ingesting', 'validating', 'analyzing', 'complete'].includes(syncStep))}>
                  <span style={styles.stepBadge}>2</span> Fetching 20 Transaction Records
                </div>
                <div style={styles.stepItem(['ingesting', 'validating', 'analyzing', 'complete'].includes(syncStep))}>
                  <span style={styles.stepBadge}>3</span> Unified Ingestion & Schema Normalization
                </div>
                <div style={styles.stepItem(['validating', 'analyzing', 'complete'].includes(syncStep))}>
                  <span style={styles.stepBadge}>4</span> Pydantic Security & Deduplication Validation
                </div>
                <div style={styles.stepItem(['analyzing', 'complete'].includes(syncStep))}>
                  <span style={styles.stepBadge}>5</span> M1–M9 Risk Engine Evaluation
                </div>
              </div>

              {syncStep === 'complete' && syncMetrics && (
                <div style={styles.metricsSummaryCard}>
                  <h4 style={styles.summaryTitle}>Sync & Analysis Results</h4>
                  <div style={styles.metricsGrid}>
                    <div style={styles.mTile}>
                      <span style={styles.mVal}>{syncMetrics.fetched}</span>
                      <span style={styles.mLbl}>Fetched</span>
                    </div>
                    <div style={styles.mTile}>
                      <span style={styles.mVal}>{syncMetrics.valid}</span>
                      <span style={styles.mLbl}>Valid</span>
                    </div>
                    <div style={styles.mTile}>
                      <span style={styles.mVal}>{syncMetrics.rejected}</span>
                      <span style={styles.mLbl}>Rejected</span>
                    </div>
                    <div style={styles.mTile}>
                      <span style={styles.mVal}>{syncMetrics.duplicates}</span>
                      <span style={styles.mLbl}>Duplicates</span>
                    </div>
                    <div style={styles.mTile}>
                      <span style={styles.mVal}>{syncMetrics.analyzed}</span>
                      <span style={styles.mLbl}>M1–M9 Evaluated</span>
                    </div>
                    <div style={{ ...styles.mTile, backgroundColor: '#FEF3F2' }}>
                      <span style={{ ...styles.mVal, color: '#D92D20' }}>{syncMetrics.riskFlagged}</span>
                      <span style={{ ...styles.mLbl, color: '#B42318' }}>Risk Flagged</span>
                    </div>
                  </div>

                  {outboundAck && <div style={styles.successBanner}>{outboundAck}</div>}

                  <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <button style={styles.btnSecondary} onClick={() => setShowSyncModal(false)}>
                      Close
                    </button>
                    <button
                      style={styles.btnPrimary}
                      onClick={handleOutboundDispatch}
                      disabled={outboundLoading}
                    >
                      {outboundLoading ? 'Dispatching...' : 'Dispatch Outbound Risk Results'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, any> = {
  container: {
    backgroundColor: '#F4F6F8',
    minHeight: '100vh',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
  },
  pageTitle: {
    fontSize: '1.4rem',
    fontWeight: 700,
    color: '#172033',
    margin: 0,
  },
  pageSubtitle: {
    fontSize: '0.85rem',
    color: '#667085',
    marginTop: '0.2rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: '1.25rem',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: '8px',
    border: '1px solid #E4E7EC',
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1rem',
  },
  providerInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  providerBadgeRzp: {
    width: '36px',
    height: '36px',
    borderRadius: '6px',
    backgroundColor: '#0C2340',
    color: '#38BDF8',
    fontWeight: 700,
    fontSize: '0.75rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  providerBadgeShopify: {
    width: '36px',
    height: '36px',
    borderRadius: '6px',
    backgroundColor: '#95BF47',
    color: '#FFFFFF',
    fontWeight: 700,
    fontSize: '0.75rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  providerBadgeWoo: {
    width: '36px',
    height: '36px',
    borderRadius: '6px',
    backgroundColor: '#96588A',
    color: '#FFFFFF',
    fontWeight: 700,
    fontSize: '0.75rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  providerBadgeStripe: {
    width: '36px',
    height: '36px',
    borderRadius: '6px',
    backgroundColor: '#635BFF',
    color: '#FFFFFF',
    fontWeight: 700,
    fontSize: '0.75rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardTitle: {
    fontSize: '0.95rem',
    fontWeight: 600,
    color: '#172033',
    margin: 0,
  },
  envTag: {
    fontSize: '0.72rem',
    color: '#667085',
  },
  statusActive: {
    fontSize: '0.72rem',
    fontWeight: 600,
    color: '#12B76A',
    backgroundColor: '#ECFDF3',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
  },
  statusInactive: {
    fontSize: '0.72rem',
    fontWeight: 600,
    color: '#667085',
    backgroundColor: '#F2F4F7',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
  },
  badgeComingSoon: {
    fontSize: '0.7rem',
    fontWeight: 600,
    color: '#F79009',
    backgroundColor: '#FFFAEB',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
  },
  cardBody: {
    fontSize: '0.82rem',
    color: '#344054',
    marginBottom: '1.25rem',
  },
  cardDesc: {
    margin: 0,
    lineHeight: 1.4,
    color: '#667085',
  },
  metricRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '0.35rem 0',
    borderBottom: '1px solid #F2F4F7',
  },
  metricLabel: {
    color: '#667085',
  },
  metricValue: {
    fontWeight: 600,
    color: '#172033',
  },
  cardFooter: {
    display: 'flex',
    gap: '0.5rem',
  },
  btnPrimary: {
    backgroundColor: '#155EEF',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    padding: '0.45rem 0.9rem',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnSync: {
    backgroundColor: '#12B76A',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    padding: '0.45rem 0.9rem',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
    flex: 1,
  },
  btnSecondary: {
    backgroundColor: '#FFFFFF',
    color: '#344054',
    border: '1px solid #D0D5DD',
    borderRadius: '6px',
    padding: '0.45rem 0.9rem',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnDisabled: {
    backgroundColor: '#F2F4F7',
    color: '#98A2B3',
    border: '1px solid #EAECF0',
    borderRadius: '6px',
    padding: '0.45rem 0.9rem',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'not-allowed',
    width: '100%',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(16, 24, 40, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: '8px',
    width: '460px',
    padding: '1.5rem',
    boxShadow: '0px 8px 24px rgba(0, 0, 0, 0.12)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.25rem',
  },
  modalTitle: {
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#172033',
    margin: 0,
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '1rem',
    cursor: 'pointer',
    color: '#667085',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.3rem',
  },
  label: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#344054',
  },
  input: {
    padding: '0.5rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #D0D5DD',
    fontSize: '0.85rem',
    outline: 'none',
  },
  inputDisabled: {
    padding: '0.5rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #EAECF0',
    backgroundColor: '#F9FAFB',
    color: '#667085',
    fontSize: '0.85rem',
  },
  fieldNote: {
    fontSize: '0.72rem',
    color: '#667085',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '0.5rem',
    marginTop: '1rem',
  },
  errorBanner: {
    backgroundColor: '#FEF3F2',
    color: '#B42318',
    border: '1px solid #FECDCA',
    padding: '0.75rem 1rem',
    borderRadius: '6px',
    marginBottom: '1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '0.85rem',
  },
  successBanner: {
    backgroundColor: '#ECFDF3',
    color: '#027A48',
    border: '1px solid #ABE5C5',
    padding: '0.75rem 1rem',
    borderRadius: '6px',
    marginTop: '0.5rem',
    fontSize: '0.85rem',
  },
  syncProgressBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  pipelineSteps: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.6rem',
    backgroundColor: '#F8FAFC',
    padding: '1rem',
    borderRadius: '6px',
    border: '1px solid #E2E8F0',
  },
  stepItem: (active: boolean) => ({
    fontSize: '0.85rem',
    fontWeight: active ? 600 : 400,
    color: active ? '#155EEF' : '#94A3B8',
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
  }),
  stepBadge: {
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    backgroundColor: '#E2E8F0',
    color: '#475569',
    fontSize: '0.7rem',
    fontWeight: 700,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricsSummaryCard: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E4E7EC',
    borderRadius: '6px',
    padding: '1rem',
  },
  summaryTitle: {
    fontSize: '0.9rem',
    fontWeight: 700,
    color: '#172033',
    margin: '0 0 0.75rem 0',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '0.5rem',
  },
  mTile: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.6rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  mVal: {
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#172033',
  },
  mLbl: {
    fontSize: '0.7rem',
    color: '#667085',
    textTransform: 'uppercase',
  },
};
