import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { RiskBadge } from '../components/RiskBadge';
import { SourceBadge } from '../components/SourceBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { fetchTransactions } from '../services/api';
import { ProcessResultItem, getEffectiveRiskScore, formatRiskScore } from '../types';

interface TransactionsProps {
  onSelectTransaction: (id: string) => void;
  onImportClick?: () => void;
}

export const Transactions: React.FC<TransactionsProps> = ({ onSelectTransaction, onImportClick }) => {
  const [items, setItems] = useState<ProcessResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [decisionFilter, setDecisionFilter] = useState('ALL');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [paymentMethodFilter, setPaymentMethodFilter] = useState('ALL');
  const [page, setPage] = useState(1);
  const limit = 15;

  const loadData = () => {
    setLoading(true);
    setError(null);
    fetchTransactions({
      search,
      risk_level: riskFilter,
      decision: decisionFilter,
      source_type: sourceFilter,
      page,
      limit,
    })
      .then((res) => {
        setItems(res.transactions);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [search, riskFilter, decisionFilter, sourceFilter, page]);

  // Client-side filtering for source and payment method if returned items exist
  const filteredItems = items.filter((item) => {
    if (sourceFilter !== 'ALL' && item.source_type && !item.source_type.toLowerCase().includes(sourceFilter.toLowerCase())) {
      return false;
    }
    if (paymentMethodFilter !== 'ALL' && item.transaction.payment_method.toUpperCase() !== paymentMethodFilter.toUpperCase()) {
      return false;
    }
    return true;
  });

  return (
    <div>
      <PageHeader
        title="Transactions"
        description="Review, search, and investigate all processed merchant transactions."
      />

      {/* Toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.searchGroup}>
          <span style={styles.searchIcon}>🔍</span>
          <input
            type="text"
            placeholder="Search by Transaction ID or Customer ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={styles.searchInput}
          />
        </div>

        <div style={styles.filtersGroup}>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">All Risk Levels</option>
            <option value="LOW">Low Risk (0–29)</option>
            <option value="MEDIUM">Medium Risk (30–59)</option>
            <option value="HIGH">High Risk (60–79)</option>
            <option value="CRITICAL">Critical Risk (80–100)</option>
          </select>

          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">All Decisions</option>
            <option value="ALLOW">ALLOW</option>
            <option value="MONITOR">MONITOR</option>
            <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
            <option value="BLOCK">BLOCK</option>
          </select>

          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">All Data Sources</option>
            <option value="csv">CSV Ingestion</option>
            <option value="json">JSON Ingestion</option>
            <option value="razorpay">Razorpay API</option>
          </select>

          <select
            value={paymentMethodFilter}
            onChange={(e) => setPaymentMethodFilter(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">All Payment Methods</option>
            <option value="CREDIT_CARD">Credit Card</option>
            <option value="UPI">UPI</option>
            <option value="DEBIT_CARD">Debit Card</option>
            <option value="NET_BANKING">Net Banking</option>
          </select>
        </div>
      </div>

      {/* Main Table Content */}
      {loading ? (
        <LoadingState message="Fetching transactions..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="No transactions found"
          description="Connect a payment source or import transaction data to start risk analysis."
          actionLabel="Import Data"
          onAction={onImportClick}
        />
      ) : (
        <div style={styles.card}>
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th>TRANSACTION ID</th>
                  <th>CUSTOMER</th>
                  <th>AMOUNT</th>
                  <th>PAYMENT METHOD</th>
                  <th>SOURCE</th>
                  <th>RISK SCORE</th>
                  <th>RISK LEVEL</th>
                  <th>DECISION</th>
                  <th>TIMESTAMP</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const score = getEffectiveRiskScore(item.risk_assessment);
                  return (
                    <tr
                      key={item.transaction.transaction_id}
                      onClick={() => onSelectTransaction(item.transaction.transaction_id)}
                      style={styles.tr}
                    >
                      <td style={styles.txnIdCell}>{item.transaction.transaction_id}</td>
                      <td style={styles.customerCell}>{item.transaction.customer_id}</td>
                      <td style={styles.boldCell}>
                        {item.transaction.currency} {item.transaction.amount.toFixed(2)}
                      </td>
                      <td style={styles.methodCell}>{item.transaction.payment_method}</td>
                      <td>
                        <SourceBadge source={item.source_type} />
                      </td>
                      <td style={styles.scoreCell}>{formatRiskScore(score)} / 100</td>
                      <td>
                        <RiskBadge score={score} />
                      </td>
                      <td>
                        <RiskBadge decision={item.decision.final_decision} />
                      </td>
                      <td style={styles.timeCell}>
                        {new Date(item.transaction.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div style={styles.pagination}>
            <span style={styles.pageInfo}>
              Page {page} ({filteredItems.length} transactions shown)
            </span>
            <div style={styles.pageControls}>
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{
                  ...styles.pageBtn,
                  ...(page === 1 ? styles.pageBtnDisabled : {}),
                }}
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                style={styles.pageBtn}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  toolbar: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    padding: '1rem 1.25rem',
    marginBottom: '1.25rem',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '1rem',
    justifyContent: 'space-between',
    alignItems: 'center',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  },
  searchGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    backgroundColor: '#F8FAFC',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    padding: '0.45rem 0.75rem',
    flex: '1 1 280px',
  },
  searchIcon: {
    fontSize: '0.85rem',
    color: '#64748B',
  },
  searchInput: {
    border: 'none',
    backgroundColor: 'transparent',
    outline: 'none',
    fontSize: '0.82rem',
    width: '100%',
    color: '#0F172A',
  },
  filtersGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.6rem',
  },
  select: {
    padding: '0.45rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #CBD5E1',
    backgroundColor: '#FFFFFF',
    fontSize: '0.8rem',
    color: '#334155',
    outline: 'none',
    cursor: 'pointer',
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
    cursor: 'pointer',
    transition: 'background-color 0.15s',
  },
  txnIdCell: {
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#2563EB',
    padding: '0.75rem 0.5rem',
  },
  customerCell: {
    color: '#334155',
  },
  boldCell: {
    fontWeight: 700,
    color: '#0F172A',
  },
  methodCell: {
    textTransform: 'uppercase',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#475569',
  },
  scoreCell: {
    fontWeight: 600,
    color: '#334155',
  },
  timeCell: {
    color: '#64748B',
    fontSize: '0.78rem',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '1.25rem',
    paddingTop: '0.75rem',
    borderTop: '1px solid #F1F5F9',
  },
  pageInfo: {
    fontSize: '0.8rem',
    color: '#64748B',
  },
  pageControls: {
    display: 'flex',
    gap: '0.5rem',
  },
  pageBtn: {
    padding: '0.35rem 0.85rem',
    backgroundColor: '#FFFFFF',
    border: '1px solid #CBD5E1',
    borderRadius: '4px',
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#334155',
    cursor: 'pointer',
  },
  pageBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
};
