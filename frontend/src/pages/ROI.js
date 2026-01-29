import React, { useEffect, useState } from 'react';
import { roiApi } from '../api';
import Card from '../components/common/Card';
import ROIChart from '../components/charts/ROIChart';
import { formatCurrency, formatPercent, formatTimestamp } from '../utils/formatters';
import './Pages.css';

function ROI() {
  const [loading, setLoading] = useState(true);
  const [roiLog, setRoiLog] = useState(null);
  const [summary, setSummary] = useState(null);
  const [chainStatus, setChainStatus] = useState(null);

  useEffect(() => {
    loadROIData();
  }, []);

  const loadROIData = async () => {
    setLoading(true);
    try {
      const [logRes, summaryRes, chainRes] = await Promise.all([
        roiApi.getLog(20).catch(() => null),
        roiApi.getSummary().catch(() => null),
        roiApi.verifyChain().catch(() => null)
      ]);

      setRoiLog(logRes);
      setSummary(summaryRes);
      setChainStatus(chainRes);
    } catch (error) {
      console.error('Failed to load ROI data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyEntry = async (entryId) => {
    try {
      const result = await roiApi.verifyEntry(entryId);
      alert(result.valid ? 'Entry verified successfully!' : 'Entry verification failed!');
    } catch (error) {
      alert('Verification failed: ' + error.message);
    }
  };

  return (
    <div className="page roi-page">
      <div className="page-header">
        <h1>ROI Tracking</h1>
        <p className="page-subtitle">
          Verified improvements with immutable audit trail
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-4">
        <Card loading={loading}>
          <div className="roi-stat">
            <span className="roi-stat-value positive">
              {formatCurrency(summary?.cumulative?.total_savings || 0)}
            </span>
            <span className="roi-stat-label">Total Verified Savings</span>
          </div>
        </Card>
        <Card loading={loading}>
          <div className="roi-stat">
            <span className="roi-stat-value">
              {formatCurrency(summary?.cumulative?.total_cost || 0)}
            </span>
            <span className="roi-stat-label">Total Action Cost</span>
          </div>
        </Card>
        <Card loading={loading}>
          <div className="roi-stat">
            <span className={`roi-stat-value ${(summary?.cumulative?.total_net_benefit || 0) > 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(summary?.cumulative?.total_net_benefit || 0)}
            </span>
            <span className="roi-stat-label">Net Benefit</span>
          </div>
        </Card>
        <Card loading={loading}>
          <div className="roi-stat">
            <span className="roi-stat-value">
              {summary?.cumulative?.overall_roi ? `${summary.cumulative.overall_roi}%` : 'N/A'}
            </span>
            <span className="roi-stat-label">Overall ROI</span>
          </div>
        </Card>
      </div>

      {/* Chain Integrity */}
      <Card 
        title="Audit Chain Integrity"
        headerAction={
          <span className={`badge ${chainStatus?.chain_status === 'valid' ? 'badge-success' : 'badge-danger'}`}>
            {chainStatus?.chain_status === 'valid' ? '✓ Chain Valid' : '⚠ Chain Issue'}
          </span>
        }
        style={{ marginTop: '24px' }}
      >
        <p className="chain-message">{chainStatus?.message}</p>
        <p className="text-muted">
          Each ROI entry is cryptographically linked to the previous entry,
          ensuring the log cannot be tampered with.
        </p>
      </Card>

      <div className="grid grid-2" style={{ marginTop: '24px' }}>
        {/* ROI Chart */}
        <Card title="Net Benefit by Action" loading={loading}>
          <ROIChart entries={roiLog?.entries} />
        </Card>

        {/* By Action Type */}
        <Card title="Performance by Action Type" loading={loading}>
          {summary?.by_action_type && Object.keys(summary.by_action_type).length > 0 ? (
            <div className="action-type-breakdown">
              {Object.entries(summary.by_action_type).map(([type, data]) => (
                <div key={type} className="action-type-item">
                  <div className="type-header">
                    <span className="type-name">{type.replace(/_/g, ' ')}</span>
                    <span className="type-count">{data.count} actions</span>
                  </div>
                  <div className="type-metrics">
                    <span className="type-savings positive">
                      {formatCurrency(data.total_savings)} saved
                    </span>
                    <span className="type-roi">
                      {data.roi !== null ? `${data.roi}% ROI` : 'N/A'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No action data yet</div>
          )}
        </Card>
      </div>

      {/* ROI Log */}
      <Card 
        title="ROI Log" 
        subtitle={`${roiLog?.pagination?.total || 0} verified entries`}
        style={{ marginTop: '24px' }}
        loading={loading}
      >
        {roiLog?.entries?.length > 0 ? (
          <div className="roi-log">
            <table className="roi-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Action</th>
                  <th>Before</th>
                  <th>After</th>
                  <th>Reduction</th>
                  <th>Improvement</th>
                  <th>Net Benefit</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {roiLog.entries.map(entry => (
                  <tr key={entry.entry_id}>
                    <td>{formatTimestamp(entry.timestamp)}</td>
                    <td className="action-cell">
                      <span className="action-desc">{entry.action_description}</span>
                    </td>
                    <td>{formatCurrency(entry.before_loss)}</td>
                    <td>{formatCurrency(entry.after_loss)}</td>
                    <td className="positive">{formatCurrency(entry.loss_reduction)}</td>
                    <td>{formatPercent(entry.improvement_percentage)}</td>
                    <td className={entry.net_benefit > 0 ? 'positive' : 'negative'}>
                      {formatCurrency(entry.net_benefit)}
                    </td>
                    <td>
                      <button 
                        className="btn-verify"
                        onClick={() => handleVerifyEntry(entry.entry_id)}
                        title="Verify entry integrity"
                      >
                        {entry.is_verified ? '✓' : '?'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <p>No verified improvements yet</p>
            <p className="text-muted">
              Implement recommended actions and verify results to build your ROI log
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}

export default ROI;