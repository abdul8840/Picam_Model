import React from 'react';
import Card from '../common/Card';
import ROIEntry from './ROIEntry';
import { formatCurrency } from '../../utils/formatters';
import './ROI.css';

function ROILog({ entries, onVerify, loading }) {
  if (!entries || entries.length === 0) {
    return (
      <Card title="ROI Log" loading={loading}>
        <div className="empty-state">
          <p>No verified improvements yet</p>
          <p className="text-muted">
            Implement recommended actions and verify results to build your ROI log
          </p>
        </div>
      </Card>
    );
  }

  const totalSavings = entries.reduce((sum, e) => sum + (e.loss_reduction || 0), 0);
  const totalNetBenefit = entries.reduce((sum, e) => sum + (e.net_benefit || 0), 0);

  return (
    <Card 
      title="ROI Log" 
      subtitle={`${entries.length} verified improvements`}
      headerAction={
        <div className="roi-log-summary">
          <span className="summary-item">
            Total Savings: <strong className="positive">{formatCurrency(totalSavings)}</strong>
          </span>
          <span className="summary-item">
            Net Benefit: <strong className={totalNetBenefit >= 0 ? 'positive' : 'negative'}>
              {formatCurrency(totalNetBenefit)}
            </strong>
          </span>
        </div>
      }
      loading={loading}
    >
      <div className="roi-entries">
        {entries.map(entry => (
          <ROIEntry 
            key={entry.entry_id} 
            entry={entry} 
            onVerify={onVerify}
          />
        ))}
      </div>
    </Card>
  );
}

export default ROILog;