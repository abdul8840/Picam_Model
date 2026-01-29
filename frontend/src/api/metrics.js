import client from './client';

export const metricsApi = {
  // Get summary metrics for a date
  getSummary: (date, locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get(`/metrics/summary/${date}`, { params });
  },

  // Get Little's Law calculations
  getLittlesLaw: (date, locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get(`/metrics/littles-law/${date}`, { params });
  },

  // Get entropy/variability metrics
  getEntropy: (date, locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get(`/metrics/entropy/${date}`, { params });
  },

  // Get financial loss calculation
  getLoss: (date, locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get(`/metrics/loss/${date}`, { params });
  },

  // Get complete analysis
  getAnalysis: (date, locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get(`/metrics/analysis/${date}`, { params });
  },

  // Get hourly metrics
  getHourly: (date, locationId = null) => {
    const params = locationId ? { location_id: locationId } : {};
    return client.get(`/metrics/hourly/${date}`, { params });
  }
};

export default metricsApi;