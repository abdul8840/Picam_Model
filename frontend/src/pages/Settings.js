import React, { useEffect, useState } from 'react';
import { dataApi } from '../api';
import Card from '../components/common/Card';
import './Pages.css';

function Settings() {
  const [loading, setLoading] = useState(false);
  const [locations, setLocations] = useState([]);
  const [dateRange, setDateRange] = useState(null);
  const [privacy, setPrivacy] = useState(null);
  const [generateStatus, setGenerateStatus] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [locationsRes, dateRangeRes, privacyRes] = await Promise.all([
        dataApi.getLocations().catch(() => []),
        dataApi.getDateRange().catch(() => null),
        dataApi.verifyPrivacy().catch(() => null)
      ]);

      setLocations(locationsRes);
      setDateRange(dateRangeRes);
      setPrivacy(privacyRes);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const handleGenerateSampleData = async () => {
    setLoading(true);
    setGenerateStatus(null);
    try {
      const result = await dataApi.generateSampleData(7, 42);
      setGenerateStatus({
        type: 'success',
        message: `Generated ${result.total_records} records from ${result.start_date} to ${result.end_date}`
      });
      loadSettings();
    } catch (error) {
      setGenerateStatus({
        type: 'error',
        message: 'Failed to generate sample data: ' + error.message
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInsights = async () => {
    setLoading(true);
    setGenerateStatus(null);
    try {
      const result = await dataApi.generateAllInsights(7);
      setGenerateStatus({
        type: 'success',
        message: `Generated ${result.generated} insights`
      });
    } catch (error) {
      setGenerateStatus({
        type: 'error',
        message: 'Failed to generate insights: ' + error.message
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page settings-page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">System configuration and data management</p>
      </div>

      <div className="grid grid-2">
        {/* System Info */}
        <Card title="System Information">
          <div className="settings-section">
            <div className="setting-row">
              <span className="setting-label">System</span>
              <span className="setting-value">PICAM v1.0.0</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">Engine</span>
              <span className="setting-value">Physics-Based (Deterministic)</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">Calculation Mode</span>
              <span className="setting-value">Conservative Lower-Bound</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">Confidence Level</span>
              <span className="setting-value">95%</span>
            </div>
          </div>
        </Card>

        {/* Privacy Status */}
        <Card title="Privacy Compliance">
          {privacy ? (
            <div className="settings-section">
              <div className="privacy-status">
                <span className={`privacy-badge ${privacy.compliant ? 'compliant' : 'non-compliant'}`}>
                  {privacy.compliant ? '✓ Fully Compliant' : '⚠ Check Required'}
                </span>
              </div>
              <div className="setting-row">
                <span className="setting-label">Frames Stored</span>
                <span className="setting-value">{privacy.details.frames_stored ? 'Yes' : 'No'}</span>
              </div>
              <div className="setting-row">
                <span className="setting-label">Personal Data Extracted</span>
                <span className="setting-value">{privacy.details.personal_data_extracted ? 'Yes' : 'No'}</span>
              </div>
              <div className="setting-row">
                <span className="setting-label">Only Counts Saved</span>
                <span className="setting-value">{privacy.details.only_counts_saved ? 'Yes' : 'No'}</span>
              </div>
            </div>
          ) : (
            <div className="empty-state">Loading privacy status...</div>
          )}
        </Card>
      </div>

      <div className="grid grid-2" style={{ marginTop: '24px' }}>
        {/* Data Status */}
        <Card title="Data Status">
          <div className="settings-section">
            <div className="setting-row">
              <span className="setting-label">Locations</span>
              <span className="setting-value">{locations.length}</span>
            </div>
            {locations.length > 0 && (
              <div className="locations-list">
                {locations.map(loc => (
                  <span key={loc} className="location-tag">{loc}</span>
                ))}
              </div>
            )}
            <div className="setting-row">
              <span className="setting-label">Data Range</span>
              <span className="setting-value">
                {dateRange?.status === 'available' 
                  ? `${dateRange.start_date} to ${dateRange.end_date} (${dateRange.days} days)`
                  : 'No data'
                }
              </span>
            </div>
          </div>
        </Card>

        {/* Data Generation (Dev) */}
        <Card title="Development Tools">
          <div className="settings-section">
            <p className="text-muted" style={{ marginBottom: '16px' }}>
              Generate sample data for testing the system.
            </p>
            
            <div className="button-group">
              <button 
                className="btn btn-secondary"
                onClick={handleGenerateSampleData}
                disabled={loading}
              >
                {loading ? 'Generating...' : 'Generate Sample Data (7 days)'}
              </button>
              
              <button 
                className="btn btn-secondary"
                onClick={handleGenerateInsights}
                disabled={loading}
              >
                {loading ? 'Generating...' : 'Generate All Insights'}
              </button>
            </div>

            {generateStatus && (
              <div className={`generate-status ${generateStatus.type}`}>
                {generateStatus.message}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Physics Formulas Reference */}
      <Card title="Physics Reference" style={{ marginTop: '24px' }}>
        <div className="formulas-grid">
          <div className="formula-item">
            <h4>Little's Law</h4>
            <code>L = λW</code>
            <p>Customers in system = Arrival rate × Time in system</p>
          </div>
          <div className="formula-item">
            <h4>Utilization</h4>
            <code>ρ = λ / (c × μ)</code>
            <p>System load = Arrivals / (Servers × Service rate)</p>
          </div>
          <div className="formula-item">
            <h4>Kingman's Formula</h4>
            <code>Wq ≈ (ρ/(1-ρ)) × ((Ca² + Cs²)/2) × (1/μ)</code>
            <p>Wait time depends on utilization and variability</p>
          </div>
          <div className="formula-item">
            <h4>Queue Length</h4>
            <code>Lq = λ × Wq</code>
            <p>Queue length = Arrival rate × Wait time</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default Settings;