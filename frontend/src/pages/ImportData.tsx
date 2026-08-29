import React, { useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { ErrorState } from '../components/ErrorState';
import { ingestData } from '../services/api';
import { ProcessResponse } from '../types';

interface ImportDataProps {
  onViewTransactions: () => void;
  onViewRiskResults: () => void;
}

const SAMPLE_CSV = `cust_id,order_id,order_total,pay_type,order_dt,currency,transaction_status
C-101,ORD-101,150.00,credit_card,2026-08-28T10:00:00Z,USD,completed
C-102,ORD-102,450.00,upi,2026-08-28T10:15:00Z,USD,completed
C-103,ORD-103,1200.00,debit_card,2026-08-28T10:30:00Z,USD,completed
C-104,ORD-104,89.90,credit_card,2026-08-28T10:45:00Z,USD,completed
C-105,ORD-105,3200.00,net_banking,2026-08-28T11:00:00Z,USD,completed`;

export const ImportData: React.FC<ImportDataProps> = ({
  onViewTransactions,
  onViewRiskResults,
}) => {
  const [fileContent, setFileContent] = useState<string>(SAMPLE_CSV);
  const [fileName, setFileName] = useState<string>('merchant_a.csv');
  const [fileSize, setFileSize] = useState<string>('1.2 KB');
  const [detectedFormat, setDetectedFormat] = useState<string>('CSV');

  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ProcessResponse | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setFileSize(`${(file.size / 1024).toFixed(1)} KB`);
    const isJson = file.name.endsWith('.json');
    setDetectedFormat(isJson ? 'JSON' : 'CSV');

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setFileContent(text);
      setResponse(null);
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    setProcessing(true);
    setError(null);
    try {
      let payloadData: any = fileContent;
      if (detectedFormat === 'JSON') {
        try {
          payloadData = JSON.parse(fileContent);
        } catch {
          // Keep as string if parsing fails
        }
      }

      const res = await ingestData({
        data: payloadData,
        merchant_id: 'merchant_a',
        source_type: detectedFormat === 'JSON' ? 'json' : 'csv',
        source_id: fileName,
      });

      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'Failed to process import data.');
    } finally {
      setProcessing(false);
    }
  };

  const recordCount = fileContent.split('\n').filter((l) => l.trim().length > 0).length - (detectedFormat === 'CSV' ? 1 : 0);

  return (
    <div>
      <PageHeader
        title="Import Transaction Data"
        description="Upload batch transaction data from CSV or JSON files for real-time risk assessment."
      />

      {error && <ErrorState message={error} onRetry={handleImport} />}

      {/* Main Import Card */}
      <div style={styles.card}>
        <div style={styles.supportedFormatsRow}>
          <span style={styles.formatLabel}>SUPPORTED FILE FORMATS:</span>
          <span style={styles.formatTag}>CSV (.csv)</span>
          <span style={styles.formatTag}>JSON (.json)</span>
        </div>

        {/* Dropzone */}
        <div style={styles.dropzone}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📄</div>
          <h3 style={styles.dropTitle}>Drag and drop your transaction file here</h3>
          <p style={styles.dropDesc}>or browse from your local device</p>
          <input
            type="file"
            accept=".csv,.json"
            onChange={handleFileUpload}
            style={styles.fileInput}
            id="file-upload-input"
          />
          <label htmlFor="file-upload-input" style={styles.browseBtn}>
            Choose File
          </label>
        </div>

        {/* Detected Pre-Import Info */}
        <div style={styles.preImportCard}>
          <div style={styles.preImportGrid}>
            <div>
              <div style={styles.infoLabel}>Selected File</div>
              <div style={styles.infoVal}>{fileName}</div>
            </div>
            <div>
              <div style={styles.infoLabel}>File Size</div>
              <div style={styles.infoVal}>{fileSize}</div>
            </div>
            <div>
              <div style={styles.infoLabel}>Detected Format</div>
              <div style={styles.infoVal}>{detectedFormat}</div>
            </div>
            <div>
              <div style={styles.infoLabel}>Estimated Records</div>
              <div style={styles.infoVal}>{recordCount > 0 ? recordCount : 'Unknown'}</div>
            </div>
          </div>
        </div>

        {/* Content Preview */}
        <div style={{ marginTop: '1.25rem' }}>
          <label style={styles.infoLabel}>FILE PAYLOAD PREVIEW</label>
          <textarea
            value={fileContent}
            onChange={(e) => setFileContent(e.target.value)}
            rows={5}
            style={styles.previewArea}
          />
        </div>

        {/* Trigger Button */}
        <div style={{ marginTop: '1.25rem', textAlign: 'right' }}>
          <button
            onClick={handleImport}
            disabled={processing || !fileContent.trim()}
            style={styles.importBtn}
          >
            {processing ? 'Processing & Assessing Risk...' : 'Import & Analyze Transactions'}
          </button>
        </div>
      </div>

      {/* Processing Summary Output */}
      {response && (
        <div style={styles.summaryCard}>
          <div style={styles.summaryHeader}>
            <span style={{ fontSize: '1.2rem' }}>✅</span>
            <div>
              <h3 style={styles.summaryTitle}>Import & Risk Assessment Complete</h3>
              <p style={styles.summarySub}>
                Processed {response.summary.total_records} records in request {response.request_id}
              </p>
            </div>
          </div>

          <div style={styles.statsGrid}>
            <div style={styles.statBox}>
              <div style={styles.statNum}>{response.summary.total_records}</div>
              <div style={styles.statLbl}>Records Received</div>
            </div>
            <div style={styles.statBox}>
              <div style={{ ...styles.statNum, color: '#166534' }}>{response.summary.valid_records}</div>
              <div style={styles.statLbl}>Valid Records</div>
            </div>
            <div style={styles.statBox}>
              <div style={{ ...styles.statNum, color: response.summary.rejected_records > 0 ? '#991B1B' : '#64748B' }}>
                {response.summary.rejected_records}
              </div>
              <div style={styles.statLbl}>Rejected Records</div>
            </div>
            <div style={styles.statBox}>
              <div style={styles.statNum}>{response.summary.duplicate_records}</div>
              <div style={styles.statLbl}>Duplicates</div>
            </div>
          </div>

          <div style={styles.summaryActions}>
            <button onClick={onViewTransactions} style={styles.primaryBtn}>
              View Transactions
            </button>
            <button onClick={onViewRiskResults} style={styles.secondaryBtn}>
              View Risk Results
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
    marginBottom: '1.5rem',
  },
  supportedFormatsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
    marginBottom: '1rem',
  },
  formatLabel: {
    fontSize: '0.7rem',
    fontWeight: 700,
    color: '#64748B',
    letterSpacing: '0.05em',
  },
  formatTag: {
    padding: '0.2rem 0.5rem',
    backgroundColor: '#F1F5F9',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#334155',
  },
  dropzone: {
    border: '2px dashed #CBD5E1',
    borderRadius: '8px',
    padding: '2.5rem 1.5rem',
    textAlign: 'center',
    backgroundColor: '#F8FAFC',
    marginBottom: '1.25rem',
  },
  dropTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: '#0F172A',
    margin: 0,
  },
  dropDesc: {
    fontSize: '0.8rem',
    color: '#64748B',
    margin: '0.25rem 0 1rem 0',
  },
  fileInput: {
    display: 'none',
  },
  browseBtn: {
    display: 'inline-block',
    padding: '0.5rem 1.25rem',
    backgroundColor: '#FFFFFF',
    color: '#334155',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  preImportCard: {
    backgroundColor: '#F1F5F9',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '1rem',
  },
  preImportGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: '1rem',
  },
  infoLabel: {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#64748B',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    marginBottom: '0.25rem',
  },
  infoVal: {
    fontSize: '0.9rem',
    fontWeight: 700,
    color: '#0F172A',
  },
  previewArea: {
    width: '100%',
    fontFamily: 'monospace',
    fontSize: '0.78rem',
    padding: '0.6rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #CBD5E1',
    outline: 'none',
    boxSizing: 'border-box',
    backgroundColor: '#F8FAFC',
    color: '#0F172A',
  },
  importBtn: {
    padding: '0.6rem 1.5rem',
    backgroundColor: '#2563EB',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.85rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  summaryCard: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  summaryHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '1.25rem',
  },
  summaryTitle: {
    fontSize: '1.05rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  summarySub: {
    fontSize: '0.8rem',
    color: '#64748B',
    margin: '0.15rem 0 0 0',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
    gap: '1rem',
    marginBottom: '1.25rem',
  },
  statBox: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.85rem 1rem',
    textAlign: 'center',
  },
  statNum: {
    fontSize: '1.4rem',
    fontWeight: 700,
    color: '#0F172A',
  },
  statLbl: {
    fontSize: '0.72rem',
    fontWeight: 600,
    color: '#64748B',
    marginTop: '0.2rem',
  },
  summaryActions: {
    display: 'flex',
    gap: '0.75rem',
  },
  primaryBtn: {
    padding: '0.5rem 1.25rem',
    backgroundColor: '#2563EB',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryBtn: {
    padding: '0.5rem 1.25rem',
    backgroundColor: '#EFF6FF',
    color: '#2563EB',
    border: '1px solid #BFDBFE',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
};
