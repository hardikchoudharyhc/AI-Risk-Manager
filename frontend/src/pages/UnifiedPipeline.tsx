import React, { useState } from 'react';
import { ingestData } from '../services/api';
import { ProcessResponse, ProcessResultItem } from '../types';

interface UnifiedPipelineProps {
  onSelectTransaction?: (id: string) => void;
}

export const UnifiedPipeline: React.FC<UnifiedPipelineProps> = ({ onSelectTransaction }) => {
  const [sourceType, setSourceType] = useState<'csv' | 'json' | 'manual'>('csv');
  const [sourceId, setSourceId] = useState('uploaded_merchant_a.csv');
  const [rawText, setRawText] = useState(
    `cust_id,order_id,order_total,pay_type,order_dt,currency,transaction_status\n` +
    `C-8001,O-9001,150.00,card,2026-08-28T10:00:00Z,USD,completed\n` +
    `C-8002,O-9002,2400.00,upi,2026-08-28T10:05:00Z,INR,completed`
  );
  const [merchantId, setMerchantId] = useState('merchant_a');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latestResponse, setLatestResponse] = useState<ProcessResponse | null>(null);

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let payloadData: any = rawText;
      if (sourceType === 'json') {
        try {
          payloadData = JSON.parse(rawText);
        } catch {
          payloadData = rawText; // fallback to string for backend JSON parser
        }
      }

      const res = await ingestData({
        data: payloadData,
        source_type: sourceType,
        source_id: sourceId,
        merchant_id: merchantId,
      });

      setLatestResponse(res);
    } catch (err: any) {
      setError(err.message || 'Unified Ingestion failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Title */}
      <div style={styles.header}>
        <h1 style={styles.pageTitle}>Unified Ingestion Pipeline</h1>
        <p style={styles.pageSubtitle}>
          Single architectural pathway for CSV, JSON, manual paste, and provider API adapters converging into canonical schema & Risk Engine.
        </p>
      </div>

      {/* Visual Pipeline Architecture Map */}
      <div style={styles.pipelineBanner}>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>1. SOURCE</span>
          <span style={styles.stageSub}>CSV / JSON / RZP</span>
        </div>
        <span style={styles.stageArrow}>➔</span>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>2. INGEST</span>
          <span style={styles.stageSub}>Format Detection</span>
        </div>
        <span style={styles.stageArrow}>➔</span>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>3. NORMALIZE</span>
          <span style={styles.stageSub}>Merchant Schema</span>
        </div>
        <span style={styles.stageArrow}>➔</span>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>4. VALIDATE</span>
          <span style={styles.stageSub}>Pydantic Security</span>
        </div>
        <span style={styles.stageArrow}>➔</span>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>5. DEDUPLICATE</span>
          <span style={styles.stageSub}>De-dup Check</span>
        </div>
        <span style={styles.stageArrow}>➔</span>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>6. RISK ENGINE</span>
          <span style={styles.stageSub}>AI Risk Evaluation</span>
        </div>
        <span style={styles.stageArrow}>➔</span>
        <div style={styles.stageNode}>
          <span style={styles.stageTitle}>7. DECISION</span>
          <span style={styles.stageSub}>Cost-Aware</span>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <span>{error}</span>
          <button style={styles.closeBtn} onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div style={styles.mainGrid}>
        {/* Input Form */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Submit Input Records</h3>
          <form onSubmit={handleRunPipeline} style={styles.form}>
            <div style={styles.formRow}>
              <div style={styles.field}>
                <label style={styles.label}>Source Type</label>
                <select
                  style={styles.select}
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value as any)}
                >
                  <option value="csv">CSV File / Raw Text</option>
                  <option value="json">JSON Object / Array</option>
                  <option value="manual">Manual Entry</option>
                </select>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Source Identifier</label>
                <input
                  style={styles.input}
                  value={sourceId}
                  onChange={(e) => setSourceId(e.target.value)}
                  placeholder="file.csv or connection_id"
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Merchant Schema</label>
                <select
                  style={styles.select}
                  value={merchantId}
                  onChange={(e) => setMerchantId(e.target.value)}
                >
                  <option value="merchant_a">Merchant A (cust_id, order_total)</option>
                  <option value="merchant_b">Merchant B (customerId, amount)</option>
                  <option value="merchant_c">Merchant C (user_id, transaction_value)</option>
                  <option value="canonical">Canonical (customer_id, amount)</option>
                </select>
              </div>
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Raw Content Payload</label>
              <textarea
                rows={7}
                style={styles.textarea}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste CSV or JSON content here..."
                required
              />
            </div>

            <div style={styles.formFooter}>
              <button type="submit" style={styles.btnSubmit} disabled={loading}>
                {loading ? 'Processing Pipeline...' : 'Run Unified Ingestion Pipeline'}
              </button>
            </div>
          </form>
        </div>

        {/* Latest Ingestion Inspection Panel */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Latest Ingestion Metrics & Output</h3>
          {latestResponse ? (
            <div style={styles.responseContainer}>
              <div style={styles.summaryBar}>
                <div style={styles.sumMetric}>
                  <span style={styles.sumVal}>{latestResponse.summary.total_records}</span>
                  <span style={styles.sumLbl}>Total</span>
                </div>
                <div style={styles.sumMetric}>
                  <span style={{ ...styles.sumVal, color: '#12B76A' }}>{latestResponse.summary.valid_records}</span>
                  <span style={styles.sumLbl}>Valid</span>
                </div>
                <div style={styles.sumMetric}>
                  <span style={{ ...styles.sumVal, color: '#F04438' }}>{latestResponse.summary.rejected_records}</span>
                  <span style={styles.sumLbl}>Rejected</span>
                </div>
                <div style={styles.sumMetric}>
                  <span style={{ ...styles.sumVal, color: '#F79009' }}>{latestResponse.summary.duplicate_records}</span>
                  <span style={styles.sumLbl}>Duplicates</span>
                </div>
              </div>

              <div style={styles.metaDetails}>
                <div><strong>Request ID:</strong> {latestResponse.request_id}</div>
                <div><strong>Merchant Schema:</strong> {latestResponse.summary.merchant_id}</div>
                <div><strong>Format Detected:</strong> {latestResponse.summary.format_detected.toUpperCase()}</div>
              </div>

              <h4 style={styles.tableSubTitle}>Evaluated Canonical Output ({latestResponse.results.length} records)</h4>
              <div style={styles.resultsList}>
                {latestResponse.results.map((item: ProcessResultItem) => (
                  <div
                    key={item.transaction.transaction_id}
                    style={styles.resRow}
                    onClick={() => onSelectTransaction && onSelectTransaction(item.transaction.transaction_id)}
                  >
                    <div style={styles.resLeft}>
                      <span style={styles.txId}>{item.transaction.transaction_id}</span>
                      <span style={styles.custRef}>{item.transaction.customer_id} • {item.transaction.payment_method}</span>
                    </div>
                    <div style={styles.resRight}>
                      <span style={styles.txAmt}>₹{item.transaction.amount.toFixed(2)}</span>
                      <span style={item.decision.final_decision === 'APPROVE' ? styles.badgeApprove : styles.badgeAction}>
                        {item.decision.final_decision}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={styles.emptyState}>
              <span>No ingestion run executed yet. Submit raw payload or sync Razorpay source to inspect live metrics.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, any> = {
  container: {
    backgroundColor: '#F4F6F8',
    minHeight: '100vh',
  },
  header: {
    marginBottom: '1.25rem',
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
  pipelineBanner: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E4E7EC',
    borderRadius: '8px',
    padding: '1rem 1.25rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1.5rem',
    overflowX: 'auto',
  },
  stageNode: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  stageTitle: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#155EEF',
    letterSpacing: '0.04em',
  },
  stageSub: {
    fontSize: '0.68rem',
    color: '#667085',
    marginTop: '0.1rem',
  },
  stageArrow: {
    color: '#D0D5DD',
    fontSize: '0.9rem',
    fontWeight: 700,
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1.25rem',
  },
  panel: {
    backgroundColor: '#FFFFFF',
    borderRadius: '8px',
    border: '1px solid #E4E7EC',
    padding: '1.25rem',
  },
  panelTitle: {
    fontSize: '1rem',
    fontWeight: 700,
    color: '#172033',
    margin: '0 0 1rem 0',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '0.75rem',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.3rem',
  },
  label: {
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#344054',
  },
  input: {
    padding: '0.45rem 0.65rem',
    borderRadius: '6px',
    border: '1px solid #D0D5DD',
    fontSize: '0.82rem',
  },
  select: {
    padding: '0.45rem 0.65rem',
    borderRadius: '6px',
    border: '1px solid #D0D5DD',
    fontSize: '0.82rem',
    backgroundColor: '#FFFFFF',
  },
  textarea: {
    padding: '0.65rem',
    borderRadius: '6px',
    border: '1px solid #D0D5DD',
    fontSize: '0.82rem',
    fontFamily: 'monospace',
  },
  formFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
  },
  btnSubmit: {
    backgroundColor: '#155EEF',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    padding: '0.55rem 1.25rem',
    fontSize: '0.85rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  responseContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  summaryBar: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '0.5rem',
    backgroundColor: '#F8FAFC',
    padding: '0.75rem',
    borderRadius: '6px',
    border: '1px solid #E2E8F0',
  },
  sumMetric: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  sumVal: {
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#172033',
  },
  sumLbl: {
    fontSize: '0.68rem',
    color: '#667085',
    textTransform: 'uppercase',
  },
  metaDetails: {
    fontSize: '0.78rem',
    color: '#475569',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.2rem',
    backgroundColor: '#F1F5F9',
    padding: '0.6rem',
    borderRadius: '6px',
  },
  tableSubTitle: {
    fontSize: '0.85rem',
    fontWeight: 600,
    color: '#172033',
    margin: '0.5rem 0 0 0',
  },
  resultsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
    maxHeight: '260px',
    overflowY: 'auto',
  },
  resRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.5rem 0.75rem',
    border: '1px solid #EAECF0',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: '#FFFFFF',
  },
  resLeft: {
    display: 'flex',
    flexDirection: 'column',
  },
  txId: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#172033',
  },
  custRef: {
    fontSize: '0.72rem',
    color: '#667085',
  },
  resRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  txAmt: {
    fontSize: '0.85rem',
    fontWeight: 600,
    color: '#172033',
  },
  badgeApprove: {
    fontSize: '0.7rem',
    fontWeight: 600,
    color: '#12B76A',
    backgroundColor: '#ECFDF3',
    padding: '0.15rem 0.4rem',
    borderRadius: '4px',
  },
  badgeAction: {
    fontSize: '0.7rem',
    fontWeight: 600,
    color: '#F04438',
    backgroundColor: '#FEF3F2',
    padding: '0.15rem 0.4rem',
    borderRadius: '4px',
  },
  emptyState: {
    padding: '3rem 1.5rem',
    textAlign: 'center',
    color: '#98A2B3',
    fontSize: '0.85rem',
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
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '1rem',
    cursor: 'pointer',
    color: '#667085',
  },
};
