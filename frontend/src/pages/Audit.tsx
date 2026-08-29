import React, { useEffect, useState } from 'react';
import { Header } from '../components/Header';
import { fetchAuditTrail } from '../services/api';
import { AuditLogEntry } from '../types';

export const Audit: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditTrail()
      .then((res) => {
        setLogs(res.audit_trail);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <Header
        title="Immutable Audit & Compliance Trail"
        subtitle="Cryptographically verified logs of all automated risk decisions and defensive responses."
      />

      <div style={styles.card}>
        {loading ? (
          <div style={styles.loading}>Loading audit trail...</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th>AUDIT ID</th>
                <th>TRANSACTION ID</th>
                <th>MERCHANT</th>
                <th>DECISION</th>
                <th>ACTION CODE</th>
                <th>EXECUTION STATUS</th>
                <th>MODEL VERSION</th>
                <th>TIMESTAMP</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.audit_id} style={styles.tr}>
                  <td style={styles.idCell}>{log.audit_id}</td>
                  <td style={styles.monoCell}>{log.transaction_id}</td>
                  <td>{log.merchant_id}</td>
                  <td>
                    <span
                      style={{
                        ...styles.badge,
                        backgroundColor:
                          log.decision === 'DEFENSIVE_ACTION' ? '#FEE2E2' : log.decision === 'MANUAL_REVIEW' ? '#FEF3C7' : '#DCFCE7',
                        color:
                          log.decision === 'DEFENSIVE_ACTION' ? '#991B1B' : log.decision === 'MANUAL_REVIEW' ? '#92400E' : '#166534',
                      }}
                    >
                      {log.decision}
                    </span>
                  </td>
                  <td style={styles.monoCell}>{log.action_code}</td>
                  <td style={styles.greenText}>{log.execution_status}</td>
                  <td style={styles.subText}>{log.model_version}</td>
                  <td style={styles.subText}>{new Date(log.timestamp).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: { backgroundColor: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '1rem' },
  loading: { padding: '2rem', textAlign: 'center', color: '#64748B' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' },
  tr: { borderBottom: '1px solid #F1F5F9' },
  idCell: { fontFamily: 'monospace', fontWeight: 600, color: '#2563EB' },
  monoCell: { fontFamily: 'monospace', fontSize: '0.78rem' },
  badge: { padding: '0.15rem 0.45rem', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700 },
  greenText: { color: '#166534', fontWeight: 600 },
  subText: { color: '#64748B', fontSize: '0.78rem' },
};
