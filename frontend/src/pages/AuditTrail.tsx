import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { fetchAuditTrail } from '../services/api';
import { AuditLogEntry } from '../types';

export const AuditTrail: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState('ALL');

  const loadAudit = () => {
    setLoading(true);
    setError(null);
    fetchAuditTrail()
      .then((res) => {
        setLogs(res.audit_trail);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filteredLogs = logs.filter((log) => {
    if (filterAction !== 'ALL' && log.decision !== filterAction) return false;
    return true;
  });

  return (
    <div>
      <PageHeader
        title="Audit Trail"
        description="Compliance-grade immutable audit logs tracking system evaluations and defensive responses."
        actions={
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">All Event Decisions</option>
            <option value="ALLOW">ALLOW</option>
            <option value="MONITOR">MONITOR</option>
            <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
            <option value="BLOCK">BLOCK</option>
          </select>
        }
      />

      {loading ? (
        <LoadingState message="Fetching audit logs..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadAudit} />
      ) : filteredLogs.length === 0 ? (
        <EmptyState title="No audit entries found" description="Audit log entries will appear automatically as risk decisions occur." />
      ) : (
        <div style={styles.card}>
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th>TIMESTAMP</th>
                  <th>AUDIT ID</th>
                  <th>TRANSACTION</th>
                  <th>MERCHANT</th>
                  <th>DECISION</th>
                  <th>ACTION CODE</th>
                  <th>STATUS</th>
                  <th>MODEL VERSION</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr key={log.audit_id} style={styles.tr}>
                    <td style={styles.timeCell}>{new Date(log.timestamp).toLocaleString()}</td>
                    <td style={styles.monoCell}>{log.audit_id}</td>
                    <td style={styles.txnIdCell}>{log.transaction_id}</td>
                    <td>{log.merchant_id}</td>
                    <td>
                      <span style={styles.decisionBadge}>{log.decision}</span>
                    </td>
                    <td style={styles.monoCell}>{log.action_code}</td>
                    <td>
                      <span style={styles.statusSuccess}>{log.execution_status}</span>
                    </td>
                    <td style={styles.monoCell}>{log.model_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  select: {
    padding: '0.45rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #CBD5E1',
    backgroundColor: '#FFFFFF',
    fontSize: '0.8rem',
    color: '#334155',
    outline: 'none',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.25rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.82rem',
    textAlign: 'left',
  },
  tr: {
    borderBottom: '1px solid #F1F5F9',
  },
  timeCell: {
    color: '#64748B',
    fontSize: '0.78rem',
    padding: '0.75rem 0.5rem',
  },
  monoCell: {
    fontFamily: 'monospace',
    fontSize: '0.76rem',
    color: '#475569',
  },
  txnIdCell: {
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#2563EB',
  },
  decisionBadge: {
    padding: '0.15rem 0.45rem',
    borderRadius: '4px',
    backgroundColor: '#F1F5F9',
    color: '#0F172A',
    fontWeight: 700,
    fontSize: '0.72rem',
  },
  statusSuccess: {
    color: '#166534',
    fontWeight: 600,
    fontSize: '0.75rem',
  },
};
