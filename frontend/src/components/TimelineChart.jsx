import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

/**
 * Line chart showing alert counts over time (hourly buckets).
 */
export default function TimelineChart({ data = [] }) {
  const chartData = data.map((d) => ({
    ...d,
    // Show only HH:00 for readability
    label: d.hour ? d.hour.split(' ')[1] || d.hour : '',
  }));

  return (
    <div className="bg-soc-card border border-soc-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-soc-muted uppercase tracking-wider mb-4">
        Alerts Timeline (24h)
      </h3>
      {chartData.length === 0 ? (
        <p className="text-soc-muted text-center py-10 text-sm">No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="label"
              tick={{ fill: '#64748b', fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis tick={{ fill: '#64748b', fontSize: 12 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#1a2035', border: '1px solid #1e293b', borderRadius: 8, color: '#e2e8f0' }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3, fill: '#3b82f6' }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
