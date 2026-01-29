export const LOCATION_TYPES = {
  FRONT_DESK: 'front_desk',
  RESTAURANT: 'restaurant',
  LOBBY: 'lobby',
  HOUSEKEEPING: 'housekeeping',
  CONCIERGE: 'concierge',
  VALET: 'valet',
  SPA: 'spa',
  GYM: 'gym'
};

export const LOCATION_LABELS = {
  front_desk: 'Front Desk',
  restaurant: 'Restaurant',
  lobby: 'Lobby',
  housekeeping: 'Housekeeping',
  concierge: 'Concierge',
  valet: 'Valet',
  spa: 'Spa',
  gym: 'Gym'
};

export const ACTION_TYPES = {
  ADD_STAFF_PEAK: 'add_staff_peak',
  ADD_CAPACITY: 'add_capacity',
  QUEUE_MANAGEMENT: 'queue_management',
  SCHEDULE_OPTIMIZATION: 'schedule_optimization',
  DEMAND_SMOOTHING: 'demand_smoothing'
};

export const ACTION_LABELS = {
  add_staff_peak: 'Add Peak Staff',
  add_capacity: 'Add Capacity',
  queue_management: 'Queue Management',
  schedule_optimization: 'Schedule Optimization',
  demand_smoothing: 'Demand Smoothing'
};

export const LOSS_CATEGORIES = {
  WAIT_TIME: 'wait_time_cost',
  THROUGHPUT: 'lost_throughput_revenue',
  WALKAWAY: 'walkaway_cost',
  IDLE: 'idle_time_cost',
  OVERTIME: 'overtime_cost'
};

export const LOSS_LABELS = {
  wait_time_cost: 'Wait Time',
  lost_throughput_revenue: 'Lost Throughput',
  walkaway_cost: 'Walk-aways',
  idle_time_cost: 'Idle Time',
  overtime_cost: 'Overtime'
};

export const CHART_COLORS = [
  '#6366f1',
  '#8b5cf6',
  '#ec4899',
  '#f59e0b',
  '#10b981',
  '#3b82f6',
  '#ef4444'
];

export const STATUS_COLORS = {
  stable: '#10b981',
  stressed: '#f59e0b',
  unstable: '#ef4444',
  unknown: '#6b7280'
};