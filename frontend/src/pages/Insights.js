import React, { useEffect, useState } from 'react';
import { insightsApi } from '../api';
import Card from '../components/common/Card';
import TrendChart from '../components/charts/TrendChart';
import { formatCurrency, formatPercent, formatDisplayDate } from '../utils/formatters';
import './Pages.css';

function Insights() {
  const [loading, setLoading] = useState(true);
  const [weekly, setWeekly] = useState(null);
  const [trends, setTrends] = useState(null);
  const [pendingActions, setPendingActions] = useState(null);

  useEffect(() => {
    loadInsights();
  }, []);

  const loadInsights = async () => {
    setLoading(true);
    try {
      const [weeklyRes, trendsRes, actionsRes] = await Promise.all([
        insightsApi.getWeekly().catch(() => null),
        insightsApi.getTrends(30).catch(() => null),
        insightsApi.getPendingActions().catch(() => null)
      ]);

      setWeekly(weeklyRes);
      setTrends(trendsRes);
      setPendingActions(actionsRes);
    } catch (error) {
      console.error('Failed to load insights:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page insights-page">
      <div className="page-header">
        <h1>Insights & Trends</h1>
        <p className="page-subtitle">
          Long-term patterns and actionable recommendations
        </p>
      </div>

      {/* Weekly Summary */}
      <Card title="Weekly Summary" subtitle={weekly?.period} loading={loading}>
        {weekly?.status !== 'no_data' ? (
          <div className="weekly-content">
            <div className="weekly-stats">
              <div className="weekly-stat">
                <span className="stat-value">{formatCurrency(weekly?.summary?.total_loss)}</span>
                <span className="stat-label">Total Loss</span>
              </div>
              <div className="weekly-stat">
                <span className="stat-value">{formatCurrency(weekly?.summary?.avg_daily_loss)}</span>
                <span className="stat-label">Avg Daily Loss</span>
              </div>
              <div className="weekly-stat">
                <span className="stat-value">{weekly?.days_with_data}</span>
                <span className="stat-label">Days Analyzed</span>
              </div>
            </div>

            {weekly?.daily_breakdown && (
              <div className="daily-breakdown">
                <h4>Daily Breakdown</h4>
                <div className="breakdown-list">
                  {weekly.daily_breakdown.map(day => (
                    <div key={day.date} className="breakdown-item">
                      <span className="breakdown-date">{formatDisplayDate(day.date)}</span>
                      <span className="breakdown-location">{day.top_location}</span>
                      <span className="breakdown-loss">{formatCurrency(day.total_loss)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="empty-state">No weekly data available</div>
        )}
      </Card>

      <div className="grid grid-2" style={{ marginTop: '24px' }}>
        {/* Trend Analysis */}
        <Card title="30-Day Loss Trend" loading={loading}>
          {trends?.status !== 'insufficient_data' ? (
            <div className="trend-content">
              <TrendChart data={trends} />
              
              <div className="trend-summary">
                <div className={`trend-direction ${trends?.trend?.direction}`}>
                  {trends?.trend?.direction === 'improving' && '📉 Improving'}
                  {trends?.trend?.direction === 'worsening' && '📈 Worsening'}
                  {trends?.trend?.direction === 'stable' && '➡️ Stable'}
                </div>
                <p className="trend-interpretation">
                  {trends?.trend?.interpretation}
                </p>
                
                {trends?.week_over_week?.change_percentage !== null && (
                  <div className="wow-change">
                    <span>Week over Week: </span>
                    <span className={trends.week_over_week.change_percentage < 0 ? 'positive' : 'negative'}>
                      {trends.week_over_week.change_percentage > 0 ? '+' : ''}
                      {formatPercent(trends.week_over_week.change_percentage)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Need at least 7 days of data for trend analysis</p>
            </div>
          )}
        </Card>

        {/* Pending Actions */}
        <Card 
          title="Pending Actions" 
          subtitle={`${pendingActions?.count || 0} actions awaiting implementation`}
          loading={loading}
        >
          {pendingActions?.actions?.length > 0 ? (
            <div className="pending-actions">
              {pendingActions.actions.slice(0, 5).map(action => (
                <div key={action.id} className="pending-action">
                  <div className="action-header">
                    <span className="action-date">{formatDisplayDate(action.date)}</span>
                    <span className="action-location">{action.location}</span>
                  </div>
                  <p className="action-description">{action.description}</p>
                  <div className="action-footer">
                    <span className="potential">
                      {formatCurrency(action.potential_recovery)} potential
                    </span>
                    <span className="confidence">
                      {formatPercent(action.confidence * 100)} confidence
                    </span>
                  </div>
                </div>
              ))}
              
              <div className="total-potential">
                Total Potential Recovery: {formatCurrency(pendingActions.total_potential_recovery)}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>No pending actions</p>
              <p className="text-muted">All recommendations have been addressed</p>
            </div>
          )}
        </Card>
      </div>

      {/* Top Loss Locations */}
      {weekly?.top_loss_locations && (
        <Card title="Top Loss Locations (7 Days)" style={{ marginTop: '24px' }}>
          <div className="top-locations">
            {weekly.top_loss_locations.map((loc, index) => (
              <div key={loc.location} className="top-location">
                <span className="location-rank">#{index + 1}</span>
                <span className="location-name">{loc.location}</span>
                <span className="location-loss">{formatCurrency(loc.total_loss)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export default Insights;