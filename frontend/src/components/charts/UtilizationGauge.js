import React from 'react';
import './Charts.css';

function UtilizationGauge({ value, label = 'Utilization' }) {
  const percentage = Math.min(value * 100, 100);
  const displayValue = (value * 100).toFixed(1);
  
  const getColor = () => {
    if (value < 0.7) return 'var(--accent-success)';
    if (value < 0.9) return 'var(--accent-warning)';
    return 'var(--accent-danger)';
  };

  const getStatus = () => {
    if (value < 0.7) return 'Healthy';
    if (value < 0.9) return 'Busy';
    if (value < 1.0) return 'Near Capacity';
    return 'Overloaded';
  };

  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="gauge-container">
      <svg className="gauge" viewBox="0 0 100 100">
        {/* Background circle */}
        <circle
          className="gauge-bg"
          cx="50"
          cy="50"
          r="45"
          fill="none"
          strokeWidth="8"
        />
        {/* Progress circle */}
        <circle
          className="gauge-progress"
          cx="50"
          cy="50"
          r="45"
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          style={{
            stroke: getColor(),
            strokeDasharray: circumference,
            strokeDashoffset: strokeDashoffset,
            transform: 'rotate(-90deg)',
            transformOrigin: '50% 50%'
          }}
        />
        {/* Center text */}
        <text
          x="50"
          y="45"
          textAnchor="middle"
          className="gauge-value"
          style={{ fill: 'var(--text-primary)' }}
        >
          {displayValue}%
        </text>
        <text
          x="50"
          y="60"
          textAnchor="middle"
          className="gauge-label"
          style={{ fill: 'var(--text-muted)' }}
        >
          {label}
        </text>
      </svg>
      <div className="gauge-status" style={{ color: getColor() }}>
        {getStatus()}
      </div>
    </div>
  );
}

export default UtilizationGauge;