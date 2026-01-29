import React from 'react';
import Card from '../common/Card';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import './Dashboard.css';

function DailyInsightCard({ insight, loading }) {
  if (!insight || insight.status === 'no_data') {
    return (
      <Card title="Daily Insight" loading={loading}>
        <div className="insight-empty">
          <p>No data available for this date</p>
          <button className="btn btn-primary">Generate Insight</button>
        </div>
      </Card>
    );
  }

  const { top_loss, recommended_action, summary } = insight;

  return (
    <Card 
      title="Daily Insight" 
      subtitle={insight.date}
      loading={loading}
    >
      <div className="insight-content">
        <div className="insight-section">
          <h4 className="insight-section-title">Top Loss Point</h4>
          <div className="insight-highlight loss">
            <span className="highlight-icon">📍</span>
            <div className="highlight-content">
              <span className="highlight-location">{top_loss?.location}</span>
              <span className="highlight-value">{formatCurrency(top_loss?.amount)}</span>
              <span className="highlight-cause">{top_loss?.cause}</span>
            </div>
          </div>
        </div>

        <div className="insight-section">
          <h4 className="insight-section-title">Recommended Action</h4>
          <div className="insight-highlight action">
            <span className="highlight-icon">💡</span>
            <div className="highlight-content">
              <span className="highlight-description">
                {recommended_action?.description}
              </span>
              <div className="highlight-meta">
                <span className="potential-recovery">
                  Potential: {formatCurrency(recommended_action?.potential_recovery)}
                </span>
                <span className="confidence">
                  Confidence: {formatPercent(recommended_action?.confidence * 100)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="insight-stats">
          <div className="insight-stat">
            <span className="stat-value">{formatCurrency(summary?.total_loss)}</span>
            <span className="stat-label">Total Loss</span>
          </div>
          <div className="insight-stat">
            <span className="stat-value">{summary?.total_observations}</span>
            <span className="stat-label">Observations</span>
          </div>
          <div className="insight-stat">
            <span className="stat-value">{formatPercent(summary?.data_completeness * 100)}</span>
            <span className="stat-label">Data Quality</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default DailyInsightCard;