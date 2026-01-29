import React from 'react';
import { formatCurrency, formatPercent, formatTimestamp } from '../../utils/formatters';
import './ROI.css';

function ROIEntry({ entry, onVerify }) {
  const isPositive = entry.net_benefit > 0;

  return (
    <div className={`roi-entry ${isPositive ? 'positive' : 'negative'}`}>
      <div className="entry-header">
        <div className="entry-meta">
          <span className="entry-date">{formatTimestamp(entry.timestamp)}</span>
          <span className="entry-id">#{entry.entry_id.slice(-8)}</span>
        </div>
        <div className="entry-status">
          {entry.is_verified ? (
            <span className="verified-badge" title="Entry verified">✓</span>
          ) : (
            <button 
              className="verify-btn"
              onClick={() => onVerify && onVerify(entry.entry_id)}
              title="Verify entry"
            >
              Verify
            </button>
          )}
        </div>
      </div>

      <div className="entry-action">
        <span className="action-type">{entry.action_type?.replace(/_/g, ' ')}</span>
        <p className="action-description">{entry.action_description}</p>
      </div>

      <div className="entry-metrics">
        <div className="metric-pair">
          <div className="metric">
            <span className="metric-label">Before</span>
            <span className="metric-value">{formatCurrency(entry.before_loss)}/day</span>
          </div>
          <span className="metric-arrow">→</span>
          <div className="metric">
            <span className="metric-label">After</span>
            <span className="metric-value">{formatCurrency(entry.after_loss)}/day</span>
          </div>
        </div>

        <div className="metric-results">
          <div className="result-item">
            <span className="result-label">Reduction</span>
            <span className="result-value positive">
              {formatCurrency(entry.loss_reduction)}
            </span>
          </div>
          <div className="result-item">
            <span className="result-label">Improvement</span>
            <span className="result-value positive">
              {formatPercent(entry.improvement_percentage)}
            </span>
          </div>
          <div className="result-item">
            <span className="result-label">Action Cost</span>
            <span className="result-value">
              {formatCurrency(entry.action_cost)}
            </span>
          </div>
          <div className="result-item highlight">
            <span className="result-label">Net Benefit</span>
            <span className={`result-value ${isPositive ? 'positive' : 'negative'}`}>
              {formatCurrency(entry.net_benefit)}
            </span>
          </div>
        </div>
      </div>

      <div className="entry-footer">
        <span className="sequence">Seq #{entry.sequence}</span>
        <span className="hash" title={entry.entry_hash}>
          Hash: {entry.entry_hash?.slice(0, 12)}...
        </span>
      </div>
    </div>
  );
}

export default ROIEntry;