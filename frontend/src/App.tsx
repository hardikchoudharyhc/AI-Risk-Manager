import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { Dashboard } from './pages/Dashboard';
import { Transactions } from './pages/Transactions';
import { TransactionDetail } from './pages/TransactionDetail';
import { RiskQueue } from './pages/RiskQueue';
import { Customers } from './pages/Customers';
import { ConnectedSources } from './pages/ConnectedSources';
import { RazorpayConnection } from './pages/RazorpayConnection';
import { ImportData } from './pages/ImportData';
import { Analytics } from './pages/Analytics';
import { AuditTrail } from './pages/AuditTrail';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);

  const handleSelectTransaction = (id: string) => {
    setSelectedTxnId(id);
    setCurrentTab('transaction-detail');
  };

  const handleBackToTransactions = () => {
    setSelectedTxnId(null);
    setCurrentTab('transactions');
  };

  const renderContent = () => {
    if (currentTab === 'transaction-detail' && selectedTxnId) {
      return (
        <TransactionDetail
          transactionId={selectedTxnId}
          onBack={handleBackToTransactions}
        />
      );
    }

    switch (currentTab) {
      case 'dashboard':
        return <Dashboard onSelectTransaction={handleSelectTransaction} />;
      case 'transactions':
        return (
          <Transactions
            onSelectTransaction={handleSelectTransaction}
            onImportClick={() => setCurrentTab('import')}
          />
        );
      case 'risk-queue':
        return <RiskQueue onSelectTransaction={handleSelectTransaction} />;
      case 'customers':
        return <Customers onSelectTransaction={handleSelectTransaction} />;
      case 'sources':
        return (
          <ConnectedSources
            onNavigateRazorpay={() => setCurrentTab('sources/razorpay')}
            onViewTransactions={() => setCurrentTab('transactions')}
          />
        );
      case 'sources/razorpay':
        return (
          <RazorpayConnection
            onBack={() => setCurrentTab('sources')}
            onViewTransactions={() => setCurrentTab('transactions')}
          />
        );
      case 'import':
        return (
          <ImportData
            onViewTransactions={() => setCurrentTab('transactions')}
            onViewRiskResults={() => setCurrentTab('risk-queue')}
          />
        );
      case 'analytics':
        return <Analytics />;
      case 'audit':
        return <AuditTrail />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard onSelectTransaction={handleSelectTransaction} />;
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => {
          setSelectedTxnId(null);
          setCurrentTab(tab);
        }}
      />
      <div style={styles.mainWrapper}>
        <TopBar />
        <main style={styles.mainContent}>{renderContent()}</main>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  layout: {
    display: 'flex',
    minHeight: '100vh',
    backgroundColor: '#F8FAFC',
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  mainWrapper: {
    marginLeft: '240px',
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  mainContent: {
    padding: '1.75rem 2.25rem',
    flex: 1,
  },
};

export default App;
