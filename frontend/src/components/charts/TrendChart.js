import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { formatCurrency, formatDisplayDate } from '../../utils/formatters';
import './Charts.css';

function TrendChart({ data, showAverage = true }) {
  if (!data || !data.daily_breakdown) return null;

  const chartData = data.daily_breakdown.map(item => ({
    date: item.date,
    displayDate: formatDisplayDate(item.date),
    loss: item.total_loss
  }));

  const average = data.averages?.overall_avg_daily_loss || 0;

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{payload[0].payload.displayDate}</p>
          <p className="tooltip-value">{formatCurrency(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
          <XAxis 
            dataKey="displayDate"
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
          {showAverage && average > 0 && (
            <ReferenceLine 
              y={average} 
              stroke="var(--accent-warning)" 
              strokeDasharray="5 5"
              label={{ 
                value: 'Avg', 
                fill: 'var(--accent-warning)',
                fontSize: 11
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="loss"
            stroke="var(--accent-danger)"
            strokeWidth={2}
            dot={{ fill: 'var(--accent-danger)', strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6, strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;