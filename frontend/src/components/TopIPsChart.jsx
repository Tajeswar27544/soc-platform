import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

/**
 * Horizontal bar chart showing top 10 source IPs by alert count.
 */
export default function TopIPsChart({ data = [] }) {
  return (
    <div className="bg-soc-card border border-soc-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-soc-muted uppercase tracking-wider mb-4">
        Top 10 Source IPs
      </h3>
      {data.length === 0 ? (
        <p className="text-soc-muted text-center py-10 text-sm">No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
            <XAxis type="number" tick={{ fill: '#64748b', fontSize: 12 }} allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="src_ip"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              width={120}
            />
            <Tooltip
              contentStyle={{ background: '#1a2035', border: '1px solid #1e293b', borderRadius: 8, color: '#e2e8f0' }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
