import React from 'react';
import Card from '../common/Card';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import './ROI.css';

function ROISummary({ summary, chainStatus, loading }) {
  if (!summary || summary.status === 'no_data') {
    return (
      <Card title="ROI Summary" loading={loading}>
        <div className="empty-state">
          <p>No ROI data available yet</p>
        </div>
      </Card>
    );
  }

  const { cumulative, by_action_type } = summary;

  return (
    <Card 
      title="Cumulative ROI" 
      headerAction={
        <span className={`badge ${chainStatus?.chain_status === 'valid' ? 'badge-success' : 'badge-danger'}`}>
          {chainStatus?.chain_status === 'valid' ? '✓ Chain Valid' : '⚠ Check Chain'}
        </span>
      }
      loading={loading}
    >
      <div className="roi-summary-content">
        {/* Main Stats */}
        <div className="summary-stats">
          <div className="summary-stat primary">
            <span className="stat-value positive">
              {formatCurrency(cumulative?.total_savings || 0)}
            </span>
            <span className="stat-label">Total Verified Savings</span>
          </div>
          
          <div className="summary-stat">
            <span className="stat-value">
              {formatCurrency(cumulative?.total_cost || 0)}
            </span>
            <span className="stat-label">Total Action Cost</span>
          </div>
          
          <div className="summary-stat">
            <span className={`stat-value ${(cumulative?.total_net_benefit || 0) >= 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(cumulative?.total_net_benefit || 0)}
            </span>
            <span className="stat-label">Net Benefit</span>
          </div>
          
          <div className="summary-stat">
            <span className="stat-value">
              {cumulative?.overall_roi != null 
                ? `${cumulative.overall_roi}%` 
                : 'N/A'}
            </span>
            <span className="stat-label">Overall ROI</span>
          </div>
        </div>

        {/* By Action Type */}
        {by_action_type && Object.keys(by_action_type).length > 0 && (
          <div className="action-type-breakdown">
            <h4>By Action Type</h4>
            <div className="type-list">
              {Object.entries(by_action_type).map(([type, data]) => (
                <div key={type} className="type-item">
                  <div className="type-header">
                    <span className="type-name">{type.replace(/_/g, ' ')}</span>
                    <span className="type-count">{data.count} actions</span>
                  </div>
                  <div className="type-stats">
                    <span className="type-stat">
                      <span className="label">Savings:</span>
                      <span className="value positive">{formatCurrency(data.total_savings)}</span>
                    </span>
                    <span className="type-stat">
                      <span className="label">Cost:</span>
                      <span className="value">{formatCurrency(data.total_cost)}</span>
                    </span>
                    <span className="type-stat">
                      <span className="label">ROI:</span>
                      <span className="value">{data.roi != null ? `${data.roi}%` : 'N/A'}</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chain Integrity Note */}
        <div className="chain-note">
          <p>
            <strong>Immutable Audit Trail:</strong> Each entry is cryptographically 
            linked to the previous entry, ensuring the log cannot be tampered with.
          </p>
        </div>
      </div>
    </Card>
  );
}

export default ROISummary;