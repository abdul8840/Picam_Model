import React from 'react';
import Card from '../common/Card';
import { formatNumber } from '../../utils/formatters';
import './Metrics.css';

function EntropyCard({ data, loading }) {
  if (!data || data.status !== 'calculated') {
    return (
      <Card title="Entropy Analysis" subtitle="Operational Variability" loading={loading}>
        <div className="empty-state">
          <p>Insufficient data for entropy calculation</p>
        </div>
      </Card>
    );
  }

  const { entropy, interpretation, kingman_impact } = data;

  const getVariabilityClass = (level) => {
    switch (level) {
      case 'low': return 'success';
      case 'moderate': return 'warning';
      case 'high': return 'danger';
      default: return '';
    }
  };

  return (
    <Card title="Entropy Analysis" subtitle="Operational Variability" loading={loading}>
      <div className="entropy-card-content">
        {/* CV Metrics */}
        <div className="cv-grid">
          <div className="cv-item">
            <div className="cv-header">
              <span className="cv-label">Arrival CV</span>
              <span className={`cv-status ${getVariabilityClass(interpretation.arrival_variability)}`}>
                {interpretation.arrival_variability}
              </span>
            </div>
            <div className="cv-value">{formatNumber(entropy.arrival_cv, 3)}</div>
            <div className="cv-bar">
              <div 
                className="cv-bar-fill"
                style={{ 
                  width: `${Math.min(entropy.arrival_cv * 50, 100)}%`,
                  background: interpretation.arrival_variability === 'high' 
                    ? 'var(--accent-danger)' 
                    : 'var(--accent-primary)'
                }}
              />
            </div>
          </div>

          <div className="cv-item">
            <div className="cv-header">
              <span className="cv-label">Service CV</span>
              <span className={`cv-status ${getVariabilityClass(interpretation.service_variability)}`}>
                {interpretation.service_variability}
              </span>
            </div>
            <div className="cv-value">{formatNumber(entropy.service_cv, 3)}</div>
            <div className="cv-bar">
              <div 
                className="cv-bar-fill"
                style={{ 
                  width: `${Math.min(entropy.service_cv * 50, 100)}%`,
                  background: interpretation.service_variability === 'high' 
                    ? 'var(--accent-danger)' 
                    : 'var(--accent-primary)'
                }}
              />
            </div>
          </div>
        </div>

        {/* Variance Impact */}
        <div className="variance-impact">
          <span className="impact-label">Variance Impact Multiplier</span>
          <span className="impact-value">
            {formatNumber(entropy.variance_impact_multiplier, 2)}x
          </span>
          <p className="impact-desc">
            Wait times are multiplied by this factor due to variability
          </p>
        </div>

        {/* Kingman's Formula */}
        {kingman_impact && (
          <div className="kingman-info">
            <h5>Kingman's Formula</h5>
            <p className="kingman-interpretation">{kingman_impact.interpretation}</p>
            <code className="kingman-formula">{kingman_impact.formula}</code>
          </div>
        )}
      </div>
    </Card>
  );
}

export default EntropyCard;