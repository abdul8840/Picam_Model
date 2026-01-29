import React from 'react';
import Card from '../common/Card';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import { ACTION_LABELS } from '../../utils/constants';
import './Dashboard.css';

function RecommendedAction({ action, onImplement }) {
  if (!action) {
    return (
      <Card title="Recommended Action">
        <div className="empty-state">No recommendations available</div>
      </Card>
    );
  }

  const roiRatio = action.roi_ratio === 'infinite' ? '∞' : `${action.roi_ratio}x`;

  return (
    <Card 
      title="Today's Top Action"
      headerAction={
        <span className={`badge badge-${action.confidence > 0.7 ? 'success' : 'warning'}`}>
          {formatPercent(action.confidence * 100)} confidence
        </span>
      }
    >
      <div className="action-content">
        <div className="action-type">
          {ACTION_LABELS[action.type] || action.type}
        </div>
        
        <p className="action-description">{action.description}</p>
        
        <div className="action-metrics">
          <div className="action-metric">
            <span className="metric-label">Potential Recovery</span>
            <span className="metric-value positive">
              {formatCurrency(action.min_recovery)} - {formatCurrency(action.max_recovery)}
            </span>
          </div>
          
          <div className="action-metric">
            <span className="metric-label">Action Cost</span>
            <span className="metric-value">{formatCurrency(action.cost)}</span>
          </div>
          
          <div className="action-metric">
            <span className="metric-label">Net Benefit</span>
            <span className={`metric-value ${action.net_benefit > 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(action.net_benefit)}
            </span>
          </div>
          
          <div className="action-metric">
            <span className="metric-label">ROI Ratio</span>
            <span className="metric-value">{roiRatio}</span>
          </div>
        </div>
        
        <div className="action-physics">
          <h5>Physics Justification</h5>
          <p>{action.justification}</p>
        </div>
        
        {onImplement && (
          <button 
            className="btn btn-primary action-implement-btn"
            onClick={() => onImplement(action)}
          >
            Mark as Implemented
          </button>
        )}
      </div>
    </Card>
  );
}

export default RecommendedAction;