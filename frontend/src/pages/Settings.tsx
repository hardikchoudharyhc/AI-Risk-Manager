import React, { useState } from 'react';
import { PageHeader } from '../components/PageHeader';

export const Settings: React.FC = () => {
  const [activeSection, setActiveSection] = useState<'workspace' | 'policy' | 'security' | 'notifications'>('workspace');
  const [savedFeedback, setSavedFeedback] = useState(false);

  // Form states
  const [merchantName, setMerchantName] = useState('Demo Merchant Inc.');
  const [merchantId, setMerchantId] = useState('merchant_a');
  const [criticalThreshold, setCriticalThreshold] = useState('80');
  const [highThreshold, setHighThreshold] = useState('60');
  const [autoBlock, setAutoBlock] = useState(true);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedFeedback(true);
    setTimeout(() => setSavedFeedback(false), 3000);
  };

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Configure workspace options, automated risk policy thresholds, and security controls."
      />

      {savedFeedback && (
        <div style={styles.successBanner}>
          ✓ Settings saved successfully.
        </div>
      )}

      <div style={styles.container}>
        {/* Settings Navigation Tabs */}
        <div style={styles.navCol}>
          <button
            onClick={() => setActiveSection('workspace')}
            style={{
              ...styles.navBtn,
              ...(activeSection === 'workspace' ? styles.navBtnActive : {}),
            }}
          >
            🏢 Workspace Settings
          </button>
          <button
            onClick={() => setActiveSection('policy')}
            style={{
              ...styles.navBtn,
              ...(activeSection === 'policy' ? styles.navBtnActive : {}),
            }}
          >
            🛡️ Risk Policy & Thresholds
          </button>
          <button
            onClick={() => setActiveSection('security')}
            style={{
              ...styles.navBtn,
              ...(activeSection === 'security' ? styles.navBtnActive : {}),
            }}
          >
            🔒 Security & API Access
          </button>
          <button
            onClick={() => setActiveSection('notifications')}
            style={{
              ...styles.navBtn,
              ...(activeSection === 'notifications' ? styles.navBtnActive : {}),
            }}
          >
            🔔 Alert Notifications
          </button>
        </div>

        {/* Settings Content Box */}
        <div style={styles.contentCol}>
          {activeSection === 'workspace' && (
            <form onSubmit={handleSave} style={styles.formCard}>
              <h3 style={styles.sectionTitle}>Workspace Profile</h3>

              <div style={styles.fieldGroup}>
                <label style={styles.label}>Merchant Name</label>
                <input
                  type="text"
                  value={merchantName}
                  onChange={(e) => setMerchantName(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={styles.fieldGroup}>
                <label style={styles.label}>Merchant ID Identifier</label>
                <input
                  type="text"
                  value={merchantId}
                  disabled
                  style={{ ...styles.input, backgroundColor: '#F1F5F9', color: '#64748B' }}
                />
                <span style={styles.hint}>Internal canonical identifier.</span>
              </div>

              <button type="submit" style={styles.saveBtn}>
                Save Workspace Changes
              </button>
            </form>
          )}

          {activeSection === 'policy' && (
            <form onSubmit={handleSave} style={styles.formCard}>
              <h3 style={styles.sectionTitle}>Risk Score Decision Policy</h3>
              <p style={styles.sectionSub}>Configure policy cutoffs for automated risk level mapping.</p>

              <div style={styles.fieldGroup}>
                <label style={styles.label}>Critical Risk Cutoff Score (0–100)</label>
                <input
                  type="number"
                  value={criticalThreshold}
                  onChange={(e) => setCriticalThreshold(e.target.value)}
                  style={styles.input}
                />
                <span style={styles.hint}>Transactions scoring ≥ this value trigger BLOCK / CRITICAL decision.</span>
              </div>

              <div style={styles.fieldGroup}>
                <label style={styles.label}>High Risk Cutoff Score (0–100)</label>
                <input
                  type="number"
                  value={highThreshold}
                  onChange={(e) => setHighThreshold(e.target.value)}
                  style={styles.input}
                />
                <span style={styles.hint}>Transactions scoring ≥ this value trigger MANUAL_REVIEW / HIGH decision.</span>
              </div>

              <div style={styles.checkboxGroup}>
                <input
                  type="checkbox"
                  id="autoblock"
                  checked={autoBlock}
                  onChange={(e) => setAutoBlock(e.target.checked)}
                />
                <label htmlFor="autoblock" style={styles.checkboxLabel}>
                  Enable automated defensive action execution on CRITICAL risk
                </label>
              </div>

              <button type="submit" style={styles.saveBtn}>
                Save Policy Configuration
              </button>
            </form>
          )}

          {activeSection === 'security' && (
            <div style={styles.formCard}>
              <h3 style={styles.sectionTitle}>Security & API Access</h3>
              <p style={styles.sectionSub}>Manage API keys and active session tokens.</p>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Environment API Key</label>
                <input
                  type="text"
                  value="rm_live_998877665544332211"
                  readOnly
                  style={{ ...styles.input, fontFamily: 'monospace' }}
                />
              </div>
            </div>
          )}

          {activeSection === 'notifications' && (
            <div style={styles.formCard}>
              <h3 style={styles.sectionTitle}>Alert Notifications</h3>
              <p style={styles.sectionSub}>Configure real-time alert routing for high risk spikes.</p>
              <div style={styles.checkboxGroup}>
                <input type="checkbox" id="email-alert" defaultChecked />
                <label htmlFor="email-alert" style={styles.checkboxLabel}>
                  Email risk summary digest on Critical events
                </label>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
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
  container: {
    display: 'grid',
    gridTemplateColumns: '220px 1fr',
    gap: '1.5rem',
  },
  navCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
  },
  navBtn: {
    padding: '0.65rem 0.85rem',
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#475569',
    cursor: 'pointer',
    textAlign: 'left',
  },
  navBtnActive: {
    backgroundColor: '#F1F5F9',
    color: '#2563EB',
    borderColor: '#BFDBFE',
  },
  contentCol: {
    flex: 1,
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
    maxWidth: '520px',
  },
  sectionTitle: {
    fontSize: '1rem',
    fontWeight: 700,
    color: '#0F172A',
    margin: 0,
  },
  sectionSub: {
    fontSize: '0.78rem',
    color: '#64748B',
    margin: '-0.75rem 0 0.5rem 0',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
  },
  label: {
    fontSize: '0.8rem',
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
  checkboxGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  checkboxLabel: {
    fontSize: '0.82rem',
    color: '#334155',
    cursor: 'pointer',
  },
  saveBtn: {
    padding: '0.55rem 1.25rem',
    backgroundColor: '#2563EB',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.85rem',
    fontWeight: 600,
    cursor: 'pointer',
    alignSelf: 'flex-start',
    marginTop: '0.5rem',
  },
};
