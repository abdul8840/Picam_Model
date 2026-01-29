import React from 'react';
import Card from '../common/Card';
import { formatCurrency } from '../../utils/formatters';
import { LOCATION_LABELS } from '../../utils/constants';
import './Dashboard.css';

function TopLossPoint({ lossData, loading }) {
  if (!lossData || !lossData.loss_by_location) {
    return (
      <Card title="Loss by Location" loading={loading}>
        <div className="empty-state">No loss data available</div>
      </Card>
    );
  }

  const locations = Object.entries(lossData.loss_by_location)
    .map(([location, loss]) => ({ location, loss }))
    .sort((a, b) => b.loss - a.loss);

  const maxLoss = Math.max(...locations.map(l => l.loss));

  return (
    <Card title="Loss by Location" loading={loading}>
      <div className="loss-locations">
        {locations.map(({ location, loss }) => (
          <div key={location} className="loss-location-item">
            <div className="location-info">
              <span className="location-name">
                {LOCATION_LABELS[location] || location}
              </span>
              <span className="location-loss">{formatCurrency(loss)}</span>
            </div>
            <div className="location-bar">
              <div 
                className="location-bar-fill"
                style={{ width: `${(loss / maxLoss) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default TopLossPoint;