import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { useApp } from '../context/AppContext';
import { metricsApi } from '../api';
import Card from '../components/common/Card';
import MetricCard from '../components/common/MetricCard';
import UtilizationGauge from '../components/charts/UtilizationGauge';
import HourlyChart from '../components/charts/HourlyChart';
import { formatDuration, formatNumber } from '../utils/formatters';
import './Pages.css';

function Metrics() {
  const { selectedDate, formatDate } = useApp();
  const [loading, setLoading] = useState(true);
  const [littlesLaw, setLittlesLaw] = useState(null);
  const [entropy, setEntropy] = useState(null);
  const [summary, setSummary] = useState(null);
  const [hourly, setHourly] = useState(null);

  useEffect(() => {
    loadMetrics();
  }, [selectedDate]);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const dateStr = formatDate(selectedDate);
      
      const [littlesRes, entropyRes, summaryRes, hourlyRes] = await Promise.all([
        metricsApi.getLittlesLaw(dateStr).catch(() => null),
        metricsApi.getEntropy(dateStr).catch(() => null),
        metricsApi.getSummary(dateStr).catch(() => null),
        metricsApi.getHourly(dateStr).catch(() => null)
      ]);

      setLittlesLaw(littlesRes);
      setEntropy(entropyRes);
      setSummary(summaryRes);
      setHourly(hourlyRes);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page metrics-page">
      <div className="page-header">
        <h1>Physics Metrics</h1>
        <p className="page-subtitle">
          Little's Law & Queueing Theory Analysis for {format(selectedDate, 'MMM d, yyyy')}
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-4">
        <MetricCard
          title="Total Arrivals"
          value={summary?.flow_metrics?.total_arrivals || 0}
          icon="👥"
        />
        <MetricCard
          title="Avg Queue Length"
          value={summary?.queue_metrics?.avg_queue_length || 0}
          format="number"
          icon="📊"
        />
        <MetricCard
          title="Avg Wait Time"
          value={summary?.time_metrics?.avg_wait_time_seconds || 0}
          format="number"
          subtitle="seconds"
          icon="⏱️"
        />
        <MetricCard
          title="Peak Utilization"
          value={(summary?.utilization_metrics?.peak_utilization || 0) * 100}
          format="percent"
          icon="📈"
          status={summary?.utilization_metrics?.is_overloaded ? 'danger' : 'success'}
        />
      </div>

      <div className="grid grid-2" style={{ marginTop: '24px' }}>
        {/* Little's Law Card */}
        <Card title="Little's Law Analysis" subtitle="L = λW" loading={loading}>
          {littlesLaw?.status === 'calculated' ? (
            <div className="littles-law-content">
              <div className="formula-display">
                <div className="formula-box">
                  <span className="formula-var">L</span>
                  <span className="formula-value">{formatNumber(littlesLaw.littles_law.L, 2)}</span>
                  <span className="formula-label">Avg in System</span>
                </div>
                <span className="formula-equals">=</span>
                <div className="formula-box">
                  <span className="formula-var">λ</span>
                  <span className="formula-value">
                    {formatNumber(littlesLaw.littles_law.lambda_rate * 3600, 2)}
                  </span>
                  <span className="formula-label">Arrivals/hr</span>
                </div>
                <span className="formula-times">×</span>
                <div className="formula-box">
                  <span className="formula-var">W</span>
                  <span className="formula-value">
                    {formatDuration(littlesLaw.littles_law.W_seconds)}
                  </span>
                  <span className="formula-label">Time in System</span>
                </div>
              </div>

              <div className="queue-metrics">
                <h4>Queue Metrics</h4>
                <div className="metrics-row">
                  <div className="metric-item">
                    <span className="metric-label">Queue Length (Lq)</span>
                    <span className="metric-value">{formatNumber(littlesLaw.queue_metrics.L_q, 2)}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Wait Time (Wq)</span>
                    <span className="metric-value">{formatDuration(littlesLaw.queue_metrics.W_q_seconds)}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Utilization (ρ)</span>
                    <span className="metric-value">{formatNumber(littlesLaw.queue_metrics.utilization_rho * 100, 1)}%</span>
                  </div>
                </div>
              </div>

              <div className="verification-status">
                {littlesLaw.verification?.verified ? (
                  <span className="badge badge-success">✓ Little's Law Verified</span>
                ) : (
                  <span className="badge badge-warning">⚠ Verification Pending</span>
                )}
                {littlesLaw.system_state?.is_unstable && (
                  <span className="badge badge-danger">System Unstable</span>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Insufficient data for Little's Law calculation</p>
              <p className="text-muted">Need at least 10 data points</p>
            </div>
          )}
        </Card>

        {/* Utilization Gauge */}
        <Card title="System Utilization" loading={loading}>
          <div className="utilization-content">
            <UtilizationGauge 
              value={littlesLaw?.queue_metrics?.utilization_rho || 0}
              label="ρ"
            />
            <div className="utilization-info">
              <p>
                <strong>ρ = λ / (c × μ)</strong>
              </p>
              <p className="text-muted">
                Utilization above 85% causes exponential wait time growth.
                Above 100% indicates queue growth faster than service.
              </p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-2" style={{ marginTop: '24px' }}>
        {/* Entropy Card */}
        <Card title="Operational Entropy" subtitle="Variability Analysis" loading={loading}>
          {entropy?.status === 'calculated' ? (
            <div className="entropy-content">
              <div className="entropy-metrics">
                <div className="entropy-item">
                  <span className="entropy-label">Arrival CV</span>
                  <span className="entropy-value">{formatNumber(entropy.entropy.arrival_cv, 3)}</span>
                  <span className={`entropy-status ${entropy.interpretation.arrival_variability}`}>
                    {entropy.interpretation.arrival_variability}
                  </span>
                </div>
                <div className="entropy-item">
                  <span className="entropy-label">Service CV</span>
                  <span className="entropy-value">{formatNumber(entropy.entropy.service_cv, 3)}</span>
                  <span className={`entropy-status ${entropy.interpretation.service_variability}`}>
                    {entropy.interpretation.service_variability}
                  </span>
                </div>
                <div className="entropy-item">
                  <span className="entropy-label">Variance Impact</span>
                  <span className="entropy-value">{formatNumber(entropy.entropy.variance_impact_multiplier, 2)}x</span>
                </div>
              </div>

              {entropy.kingman_impact && (
                <div className="kingman-box">
                  <h5>Kingman's Formula Impact</h5>
                  <p>{entropy.kingman_impact.interpretation}</p>
                  <code>Wq ≈ (ρ/(1-ρ)) × ((Ca² + Cs²)/2) × (1/μ)</code>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <p>Insufficient data for entropy calculation</p>
            </div>
          )}
        </Card>

        {/* Hourly Pattern */}
        <Card title="Hourly Arrival Pattern" loading={loading}>
          <HourlyChart data={hourly} />
          {hourly?.peak_hour !== undefined && (
            <div className="peak-info">
              Peak hour: <strong>{hourly.peak_hour}:00</strong> with {hourly.peak_arrivals} arrivals
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

export default Metrics;