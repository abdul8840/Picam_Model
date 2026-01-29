/**
 * Format currency value
 */
export function formatCurrency(value, decimals = 0) {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
}

/**
 * Format number with commas
 */
export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
}

/**
 * Format percentage
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined) return '-';
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format duration in seconds to human readable
 */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '-';
  
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else if (seconds < 3600) {
    const mins = Math.round(seconds / 60);
    return `${mins}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.round((seconds % 3600) / 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
}

/**
 * Format date to display string
 */
export function formatDisplayDate(dateString) {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format timestamp to display string
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Get status color based on value
 */
export function getStatusColor(value, thresholds = { good: 0.7, warning: 0.9 }) {
  if (value < thresholds.good) return 'success';
  if (value < thresholds.warning) return 'warning';
  return 'danger';
}

/**
 * Get trend indicator
 */
export function getTrendIndicator(current, previous) {
  if (!current || !previous) return { direction: 'neutral', change: 0 };
  
  const change = ((current - previous) / previous) * 100;
  
  return {
    direction: change > 0 ? 'up' : change < 0 ? 'down' : 'neutral',
    change: Math.abs(change)
  };
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text, length = 50) {
  if (!text) return '';
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
}