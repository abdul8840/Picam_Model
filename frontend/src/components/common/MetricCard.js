import React from 'react';
import { formatCurrency, formatNumber, formatPercent } from '../../utils/formatters';
import './MetricCard.css';

function MetricCard({ 
  title, 
  value, 
  format = 'number',
  change = null,
  changeLabel = 'vs yesterday',
  icon,
  status = null,
  subtitle = null
}) {
  const formatValue = () => {
    switch (format) {
      case 'currency':
        return formatCurrency(value);
      case 'percent':
        return formatPercent(value);
      case 'number':
      default:
        return formatNumber(value);
    }
  };

  const getChangeClass = () => {
    if (change === null) return '';
    // For losses, negative change is good
    if (format === 'currency' && title.toLowerCase().includes('loss')) {
      return change < 0 ? 'positive' : 'negative';
    }
    return change >= 0 ? 'positive' : 'negative';
  };

  return (
    <div className={`metric-card ${status ? `status-${status}` : ''}`}>
      <div className="metric-card-header">
        {icon && <span className="metric-icon">{icon}</span>}
        <span className="metric-title">{title}</span>
      </div>
      
      <div className="metric-card-body">
        <div className="metric-value-container">
          <span className="metric-value">{formatValue()}</span>
          {change !== null && (
            <span className={`metric-change ${getChangeClass()}`}>
              {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
            </span>
          )}
        </div>
        
        {subtitle && (
          <span className="metric-subtitle">{subtitle}</span>
        )}
        
        {change !== null && (
          <span className="metric-change-label">{changeLabel}</span>
        )}
      </div>
      
      {status && (
        <div className="metric-status-bar"></div>
      )}
    </div>
  );
}

export default MetricCard;