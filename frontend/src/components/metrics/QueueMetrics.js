import React from 'react';
import Card from '../common/Card';
import { formatNumber, formatDuration } from '../../utils/formatters';
import './Metrics.css';

function QueueMetrics({ summary, loading }) {
  if (!summary || summary.status === 'no_data') {
    return (
      <Card title="Queue Metrics" loading={loading}>
        <div className="empty-state">No queue data available</div>
      </Card>
    );
  }

  const { flow_metrics, queue_metrics, time_metrics, utilization_metrics } = summary;

  return (
    <Card title="Queue Metrics Summary" loading={loading}>
      <div className="queue-metrics-grid">
        {/* Flow */}
        <div className="metrics-section">
          <h4>Flow</h4>
          <div className="metrics-list">
            <div className="metric-row">
              <span>Total Arrivals</span>
              <span className="value">{formatNumber(flow_metrics?.total_arrivals)}</span>
            </div>
            <div className="metric-row">
              <span>Total Departures</span>
              <span className="value">{formatNumber(flow_metrics?.total_departures)}</span>
            </div>
            <div className="metric-row">
              <span>Net Flow</span>
              <span className={`value ${flow_metrics?.net_flow > 0 ? 'warning' : ''}`}>
                {flow_metrics?.net_flow > 0 ? '+' : ''}{formatNumber(flow_metrics?.net_flow)}
              </span>
            </div>
          </div>
        </div>

        {/* Queue */}
        <div className="metrics-section">
          <h4>Queue</h4>
          <div className="metrics-list">
            <div className="metric-row">
              <span>Avg Queue Length</span>
              <span className="value">{formatNumber(queue_metrics?.avg_queue_length, 1)}</span>
            </div>
            <div className="metric-row">
              <span>Max Queue Length</span>
              <span className="value">{formatNumber(queue_metrics?.max_queue_length)}</span>
            </div>
          </div>
        </div>

        {/* Time */}
        <div className="metrics-section">
          <h4>Time</h4>
          <div className="metrics-list">
            <div className="metric-row">
              <span>Avg Wait Time</span>
              <span className="value">{formatDuration(time_metrics?.avg_wait_time_seconds)}</span>
            </div>
            <div className="metric-row">
              <span>Max Wait Time</span>
              <span className="value">{formatDuration(time_metrics?.max_wait_time_seconds)}</span>
            </div>
            <div className="metric-row">
              <span>Avg Service Time</span>
              <span className="value">{formatDuration(time_metrics?.avg_service_time_seconds)}</span>
            </div>
          </div>
        </div>

        {/* Utilization */}
        <div className="metrics-section">
          <h4>Utilization</h4>
          <div className="metrics-list">
            <div className="metric-row">
              <span>Avg Utilization</span>
              <span className="value">
                {formatNumber(utilization_metrics?.avg_utilization * 100, 1)}%
              </span>
            </div>
            <div className="metric-row">
              <span>Peak Utilization</span>
              <span className={`value ${utilization_metrics?.peak_utilization >= 1 ? 'danger' : ''}`}>
                {formatNumber(utilization_metrics?.peak_utilization * 100, 1)}%
              </span>
            </div>
            <div className="metric-row">
              <span>Status</span>
              <span className={`value ${utilization_metrics?.is_overloaded ? 'danger' : 'success'}`}>
                {utilization_metrics?.is_overloaded ? 'Overloaded' : 'Normal'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default QueueMetrics;