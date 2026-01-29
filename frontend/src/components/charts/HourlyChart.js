import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import './Charts.css';

function HourlyChart({ data, dataKey = 'arrivals', title = 'Hourly Pattern' }) {
  if (!data || !data.hourly_metrics) return null;

  const chartData = Object.entries(data.hourly_metrics)
    .map(([hour, metrics]) => ({
      hour: `${hour.padStart(2, '0')}:00`,
      hourNum: parseInt(hour),
      [dataKey]: metrics[dataKey] || 0,
      queue: metrics.avg_queue_length || 0
    }))
    .sort((a, b) => a.hourNum - b.hourNum);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{label}</p>
          {payload.map((item, index) => (
            <p key={index} className="tooltip-value" style={{ color: item.color }}>
              {item.name}: {item.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorArrivals" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
          <XAxis 
            dataKey="hour" 
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
            tickLine={false}
            interval={2}
          />
          <YAxis 
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke="var(--chart-1)"
            strokeWidth={2}
            fill="url(#colorArrivals)"
            name="Arrivals"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default HourlyChart;