import client from './client';

export const dataApi = {
  // Get available locations
  getLocations: () => {
    return client.get('/data/locations');
  },

  // Get data quality report
  getQuality: (startDate, endDate, locationId = null) => {
    const params = { start_date: startDate, end_date: endDate };
    if (locationId) params.location_id = locationId;
    return client.get('/data/quality', { params });
  },

  // Get available date range
  getDateRange: () => {
    return client.get('/data/date-range');
  },

  // Get video processing stats
  getVideoStats: (locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get('/data/video-stats', { params });
  },

  // Verify privacy compliance
  verifyPrivacy: () => {
    return client.get('/data/privacy-compliance');
  },

  // Generate sample data (admin)
  generateSampleData: (days = 7, seed = 42) => {
    return client.post('/admin/generate-sample-data', null, {
      params: { days, seed }
    });
  },

  // Generate all insights (admin)
  generateAllInsights: (days = 7) => {
    return client.post('/admin/generate-all-insights', null, {
      params: { days }
    });
  }
};

export default dataApi;