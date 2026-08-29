import React from 'react';

interface TopBarProps {
  onSearch?: (query: string) => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onSearch }) => {
  return (
    <header style={styles.header}>
      <div style={styles.searchWrapper}>
        <span style={styles.searchIcon}>🔍</span>
        <input
          type="text"
          placeholder="Search transactions, customers, or risk signals..."
          style={styles.searchInput}
          onChange={(e) => onSearch && onSearch(e.target.value)}
        />
      </div>

      <div style={styles.rightSection}>
        <div style={styles.envBadge}>
          <span style={styles.envDot} />
          DEMO / MOCK ENVIRONMENT
        </div>

        <button style={styles.iconBtn} title="Notifications">
          🔔
        </button>

        <div style={styles.divider} />

        <div style={styles.userMenu}>
          <div style={styles.avatar}>RM</div>
          <span style={styles.userName}>Risk Ops</span>
        </div>
      </div>
    </header>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    height: '56px',
    backgroundColor: '#FFFFFF',
    borderBottom: '1px solid #E2E8F0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 2rem',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  searchWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    backgroundColor: '#F8FAFC',
    border: '1px solid #E2E8F0',
    borderRadius: '6px',
    padding: '0.4rem 0.75rem',
    width: '320px',
  },
  searchIcon: {
    fontSize: '0.85rem',
    color: '#94A3B8',
  },
  searchInput: {
    border: 'none',
    backgroundColor: 'transparent',
    outline: 'none',
    fontSize: '0.82rem',
    color: '#0F172A',
    width: '100%',
  },
  rightSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  envBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    backgroundColor: '#EFF6FF',
    color: '#1E40AF',
    border: '1px solid #BFDBFE',
    borderRadius: '4px',
    padding: '0.2rem 0.6rem',
    fontSize: '0.7rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
  },
  envDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#2563EB',
  },
  iconBtn: {
    background: 'none',
    border: 'none',
    fontSize: '0.95rem',
    cursor: 'pointer',
    padding: '0.35rem',
    borderRadius: '4px',
    color: '#64748B',
  },
  divider: {
    width: '1px',
    height: '20px',
    backgroundColor: '#E2E8F0',
  },
  userMenu: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    cursor: 'pointer',
  },
  avatar: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    backgroundColor: '#0F172A',
    color: '#FFFFFF',
    fontSize: '0.72rem',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userName: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#334155',
  },
};
