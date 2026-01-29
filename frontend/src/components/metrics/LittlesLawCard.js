import React from 'react';
import Card from '../common/Card';
import { formatNumber, formatDuration } from '../../utils/formatters';
import './Metrics.css';

function LittlesLawCard({ data, loading }) {
  if (!data || data.status !== 'calculated') {
    return (
      <Card title="Little's Law" subtitle="L = λW" loading={loading}>
        <div className="empty-state">
          <p>Insufficient data for calculation</p>
          <p className="text-muted">Need at least 10 data points</p>
        </div>
      </Card>
    );
  }

  const { littles_law, queue_metrics, system_state, verification } = data;

  return (
    <Card title="Little's Law" subtitle="L = λW" loading={loading}>
      <div className="littles-card-content">
        {/* Main Formula Display */}
        <div className="formula-visual">
          <div className="formula-component">
            <span className="component-symbol">L</span>
            <span className="component-value">{formatNumber(littles_law.L, 2)}</span>
            <span className="component-desc">In System</span>
          </div>
          <span className="formula-operator">=</span>
          <div className="formula-component">
            <span className="component-symbol">λ</span>
            <span className="component-value">
              {formatNumber(littles_law.lambda_rate * 3600, 1)}/hr
            </span>
            <span className="component-desc">Arrival Rate</span>
          </div>
          <span className="formula-operator">×</span>
          <div className="formula-component">
            <span className="component-symbol">W</span>
            <span className="component-value">
              {formatDuration(littles_law.W_seconds)}
            </span>
            <span className="component-desc">Time in System</span>
          </div>
        </div>

        {/* Queue Specific Metrics */}
        <div className="queue-details">
          <div className="queue-metric">
            <span className="queue-label">Queue Length (Lq)</span>
            <span className="queue-value">{formatNumber(queue_metrics.L_q, 2)}</span>
          </div>
          <div className="queue-metric">
            <span className="queue-label">Wait Time (Wq)</span>
            <span className="queue-value">{formatDuration(queue_metrics.W_q_seconds)}</span>
          </div>
          <div className="queue-metric">
            <span className="queue-label">Utilization (ρ)</span>
            <span className={`queue-value ${queue_metrics.utilization_rho > 0.9 ? 'critical' : ''}`}>
              {formatNumber(queue_metrics.utilization_rho * 100, 1)}%
            </span>
          </div>
        </div>

        {/* Status Badges */}
        <div className="status-badges">
          {verification?.verified && (
            <span className="badge badge-success">✓ Verified</span>
          )}
          {system_state?.is_stable ? (
            <span className="badge badge-success">Stable System</span>
          ) : (
            <span className="badge badge-danger">Unstable System</span>
          )}
          <span className="badge badge-info">
            {data.data_points_used} data points
          </span>
        </div>
      </div>
    </Card>
  );
}

export default LittlesLawCard;