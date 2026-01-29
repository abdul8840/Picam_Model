import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { formatCurrency } from '../../utils/formatters';
import { LOSS_LABELS, CHART_COLORS } from '../../utils/constants';
import './Charts.css';

function LossBreakdownChart({ data }) {
  if (!data) return null;

  const chartData = Object.entries(data)
    .filter(([key, value]) => value > 0 && key !== 'total_loss')
    .map(([key, value], index) => ({
      name: LOSS_LABELS[key] || key,
      value: value,
      color: CHART_COLORS[index % CHART_COLORS.length]
    }));

  if (chartData.length === 0) {
    return (
      <div className="chart-empty">
        <p>No loss data to display</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{payload[0].name}</p>
          <p className="tooltip-value">{formatCurrency(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            verticalAlign="bottom"
            height={36}
            formatter={(value) => <span style={{ color: 'var(--text-secondary)' }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default LossBreakdownChart;