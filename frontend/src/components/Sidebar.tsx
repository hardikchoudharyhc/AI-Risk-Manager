import React from 'react';

interface NavItem {
  id: string;
  label: string;
  icon: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: 'OVERVIEW',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    ],
  },
  {
    title: 'RISK OPERATIONS',
    items: [
      { id: 'transactions', label: 'Transactions', icon: '💳' },
      { id: 'risk-queue', label: 'Risk Queue', icon: '⚡' },
      { id: 'customers', label: 'Customers', icon: '👥' },
    ],
  },
  {
    title: 'DATA SOURCES',
    items: [
      { id: 'sources', label: 'Connected Sources', icon: '🔌' },
      { id: 'import', label: 'Import Data', icon: '📥' },
    ],
  },
  {
    title: 'INSIGHTS',
    items: [
      { id: 'analytics', label: 'Analytics', icon: '📈' },
    ],
  },
  {
    title: 'SYSTEM',
    items: [
      { id: 'audit', label: 'Audit Trail', icon: '🛡️' },
      { id: 'settings', label: 'Settings', icon: '⚙️' },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange }) => {
  return (
    <aside style={styles.sidebar}>
      {/* Product Identity */}
      <div style={styles.header}>
        <div style={styles.logoIcon}>🛡️</div>
        <div>
          <div style={styles.brandTitle}>AI Risk Manager</div>
          <div style={styles.brandSubtitle}>Defensive Risk Intelligence</div>
        </div>
      </div>

      {/* Navigation Groups */}
      <nav style={styles.navContainer}>
        {NAV_GROUPS.map((group) => (
          <div key={group.title} style={styles.group}>
            <div style={styles.groupTitle}>{group.title}</div>
            {group.items.map((item) => {
              const isActive = currentTab === item.id || (currentTab === 'sources/razorpay' && item.id === 'sources');
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  style={{
                    ...styles.navButton,
                    ...(isActive ? styles.navButtonActive : {}),
                  }}
                >
                  <span style={styles.navIcon}>{item.icon}</span>
                  <span style={styles.navLabel}>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer / Workspace */}
      <div style={styles.footer}>
        <div style={styles.workspaceCard}>
          <div style={styles.workspaceLabel}>WORKSPACE</div>
          <div style={styles.workspaceName}>Demo Merchant</div>
        </div>
      </div>
    </aside>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: '240px',
    backgroundColor: '#FFFFFF',
    borderRight: '1px solid #E2E8F0',
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    position: 'fixed',
    left: 0,
    top: 0,
    zIndex: 20,
  },
  header: {
    padding: '1.25rem 1.25rem 1rem 1.25rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    borderBottom: '1px solid #F1F5F9',
  },
  logoIcon: {
    fontSize: '1.4rem',
  },
  brandTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#0F172A',
    lineHeight: 1.2,
  },
  brandSubtitle: {
    fontSize: '0.68rem',
    color: '#64748B',
    fontWeight: 500,
  },
  navContainer: {
    flex: 1,
    padding: '1rem 0.75rem',
    overflowY: 'auto',
  },
  group: {
    marginBottom: '1.25rem',
  },
  groupTitle: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#94A3B8',
    letterSpacing: '0.08em',
    padding: '0 0.5rem',
    marginBottom: '0.35rem',
  },
  navButton: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
    padding: '0.45rem 0.6rem',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '6px',
    color: '#475569',
    fontSize: '0.82rem',
    fontWeight: 500,
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'background-color 0.15s, color 0.15s',
  },
  navButtonActive: {
    backgroundColor: '#F1F5F9',
    color: '#0F172A',
    fontWeight: 600,
  },
  navIcon: {
    fontSize: '0.85rem',
  },
  navLabel: {
    flex: 1,
  },
  footer: {
    padding: '0.75rem 0.75rem 1rem 0.75rem',
    borderTop: '1px solid #F1F5F9',
  },
  workspaceCard: {
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.6rem 0.75rem',
  },
  workspaceLabel: {
    fontSize: '0.62rem',
    fontWeight: 700,
    color: '#94A3B8',
    letterSpacing: '0.06em',
  },
  workspaceName: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#0F172A',
  },
};
