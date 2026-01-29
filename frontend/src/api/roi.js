import client from './client';

export const roiApi = {
  // Get ROI log
  getLog: (limit = 50, skip = 0) => {
    return client.get('/roi/log', { params: { limit, skip } });
  },

  // Get ROI summary
  getSummary: () => {
    return client.get('/roi/summary');
  },

  // Record action implementation
  recordImplementation: (actionId, implementationDate, actualCost = null, notes = null) => {
    return client.post('/roi/implement', {
      action_id: actionId,
      implementation_date: implementationDate,
      actual_cost: actualCost,
      notes: notes
    });
  },

  // Verify improvement and create ROI entry
  verifyImprovement: (data) => {
    return client.post('/roi/verify', data);
  },

  // Verify single entry
  verifyEntry: (entryId) => {
    return client.get(`/roi/verify/${entryId}`);
  },

  // Verify chain integrity
  verifyChain: () => {
    return client.get('/roi/chain-integrity');
  }
};

export default roiApi;