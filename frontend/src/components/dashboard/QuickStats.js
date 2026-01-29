import React from 'react';
import MetricCard from '../common/MetricCard';
import './Dashboard.css';

function QuickStats({ metrics, previousMetrics }) {
  const calculateChange = (current, previous, key) => {
    if (!previous || !previous[key] || !current || !current[key]) return null;
    const curr = current[key];
    const prev = previous[key];
    if (prev === 0) return null;
    return ((curr - prev) / prev) * 100;
  };

  const totalLoss = metrics?.financial_loss?.total_loss || metrics?.total_loss || 0;
  const avgWait = metrics?.time_metrics?.avg_wait_time_seconds || 0;
  const utilization = metrics?.utilization_metrics?.avg_utilization || 0;
  const arrivals = metrics?.flow_metrics?.total_arrivals || 0;

  return (
    <div className="quick-stats grid grid-4">
      <MetricCard
        title="Total Loss"
        value={totalLoss}
        format="currency"
        icon="💸"
        change={calculateChange(
          { total_loss: totalLoss },
          previousMetrics,
          'total_loss'
        )}
        status={totalLoss > 500 ? 'danger' : totalLoss > 200 ? 'warning' : 'success'}
      />
      
      <MetricCard
        title="Avg Wait Time"
        value={avgWait}
        format="number"
        subtitle="seconds"
        icon="⏱️"
        status={avgWait > 300 ? 'danger' : avgWait > 120 ? 'warning' : 'success'}
      />
      
      <MetricCard
        title="Utilization"
        value={utilization * 100}
        format="percent"
        icon="📊"
        status={utilization > 0.9 ? 'danger' : utilization > 0.7 ? 'warning' : 'success'}
      />
      
      <MetricCard
        title="Total Arrivals"
        value={arrivals}
        format="number"
        icon="👥"
      />
    </div>
  );
}

export default QuickStats;