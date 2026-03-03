import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const SEVERITY_COLORS = {
  1: '#ef4444', // Critical — red
  2: '#f59e0b', // High — amber
  3: '#3b82f6', // Medium — blue
  4: '#10b981', // Low — green
};

const SEVERITY_LABELS = {
  1: 'Critical',
  2: 'High',
  3: 'Medium',
  4: 'Low',
};

/**
 * Bar chart showing alert counts per severity level.
 */
export default function SeverityChart({ data = [] }) {
  const chartData = data.map((d) => ({
    ...d,
    label: SEVERITY_LABELS[d.severity] || `Sev ${d.severity}`,
  }));

  return (
    <div className="bg-soc-card border border-soc-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-soc-muted uppercase tracking-wider mb-4">
        Severity Distribution
      </h3>
      {chartData.length === 0 ? (
        <p className="text-soc-muted text-center py-10 text-sm">No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 12 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 12 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#1a2035', border: '1px solid #1e293b', borderRadius: 8, color: '#e2e8f0' }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, idx) => (
                <Cell key={idx} fill={SEVERITY_COLORS[entry.severity] || '#3b82f6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
