import React from 'react';
import { ImportData } from './ImportData';

export const UnifiedDataInput: React.FC<{ onNavigateTransactions?: () => void }> = ({ onNavigateTransactions }) => {
  return <ImportData onViewTransactions={onNavigateTransactions || (() => {})} onViewRiskResults={() => {}} />;
};
export default UnifiedDataInput;
