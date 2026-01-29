import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { useApp } from '../context/AppContext';
import { metricsApi, insightsApi } from '../api';
import QuickStats from '../components/dashboard/QuickStats';
import DailyInsightCard from '../components/dashboard/DailyInsightCard';
import TopLossPoint from '../components/dashboard/TopLossPoint';
import RecommendedAction from '../components/dashboard/RecommendedAction';
import LossBreakdownChart from '../components/charts/LossBreakdownChart';
import HourlyChart from '../components/charts/HourlyChart';
import Card from '../components/common/Card';
import './Pages.css';

function Dashboard() {
  const { selectedDate, formatDate } = useApp();
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);
  const [insight, setInsight] = useState(null);
  const [hourlyData, setHourlyData] = useState(null);
  const [actions, setActions] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, [selectedDate]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const dateStr = formatDate(selectedDate);
      
      const [metricsRes, insightRes, hourlyRes, actionsRes] = await Promise.all([
        metricsApi.getAnalysis(dateStr).catch(() => null),
        insightsApi.getDaily(dateStr, true).catch(() => null),
        metricsApi.getHourly(dateStr).catch(() => null),
        insightsApi.getActions(dateStr).catch(() => null)
      ]);

      setMetrics(metricsRes);
      setInsight(insightRes);
      setHourlyData(hourlyRes);
      setActions(actionsRes);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleImplementAction = (action) => {
    console.log('Implement action:', action);
    // TODO: Open modal to confirm implementation
  };

  return (
    <div className="page dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p className="page-subtitle">
          {format(selectedDate, 'EEEE, MMMM d, yyyy')}
        </p>
      </div>

      <QuickStats metrics={metrics} />

      <div className="dashboard-grid">
        <div className="dashboard-main">
          <DailyInsightCard insight={insight} loading={loading} />
          
          <div className="grid grid-2">
            <Card title="Loss Breakdown" loading={loading}>
              <LossBreakdownChart data={insight?.loss_by_location ? 
                { ...insight.summary, ...Object.fromEntries(
                  Object.entries(insight.loss_by_location).map(([k,v]) => [`${k}_loss`, v])
                )} : metrics?.financial_loss
              } />
            </Card>
            
            <Card title="Hourly Arrivals" loading={loading}>
              <HourlyChart data={hourlyData} />
            </Card>
          </div>
        </div>
        
        <div className="dashboard-sidebar">
          <RecommendedAction 
            action={actions?.top_action} 
            onImplement={handleImplementAction}
          />
          
          <TopLossPoint lossData={insight} loading={loading} />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;