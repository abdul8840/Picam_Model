import client from './client';

export const insightsApi = {
  // Get daily insight
  getDaily: (date, generate = false) => {
    return client.get(`/insights/daily/${date}`, { 
      params: { generate } 
    });
  },

  // Generate daily insight
  generateDaily: (date, force = false) => {
    return client.post(`/insights/daily/${date}/generate`, null, {
      params: { force }
    });
  },

  // Get weekly summary
  getWeekly: (endDate = null) => {
    const params = endDate ? { end_date: endDate } : {};
    return client.get('/insights/weekly', { params });
  },

  // Get trend analysis
  getTrends: (days = 30) => {
    return client.get('/insights/trends', { params: { days } });
  },

  // Regenerate insights for date range
  regenerate: (startDate, endDate) => {
    return client.post('/insights/regenerate', null, {
      params: { start_date: startDate, end_date: endDate }
    });
  },

  // Get action recommendations
  getActions: (date) => {
    return client.get(`/insights/actions/${date}`);
  },

  // Get pending actions
  getPendingActions: () => {
    return client.get('/insights/actions/pending');
  }
};

export default insightsApi;