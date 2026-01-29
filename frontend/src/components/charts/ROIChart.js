import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';
import { formatCurrency, formatDisplayDate } from '../../utils/formatters';
import './Charts.css';

function ROIChart({ entries }) {
  if (!entries || entries.length === 0) return null;

  const chartData = entries.slice(0, 10).reverse().map(entry => ({
    date: formatDisplayDate(entry.timestamp),
    reduction: entry.loss_reduction,
    cost: entry.action_cost,
    net: entry.net_benefit,
    positive: entry.net_benefit > 0
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{label}</p>
          <p className="tooltip-value" style={{ color: 'var(--accent-success)' }}>
            Savings: {formatCurrency(data.reduction)}
          </p>
          <p className="tooltip-value" style={{ color: 'var(--accent-warning)' }}>
            Cost: {formatCurrency(data.cost)}
          </p>
          <p className="tooltip-value" style={{ color: data.positive ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
            Net: {formatCurrency(data.net)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
          <XAxis 
            dataKey="date"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis 
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `$${value}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="net" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={entry.positive ? 'var(--accent-success)' : 'var(--accent-danger)'} 
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ROIChart;