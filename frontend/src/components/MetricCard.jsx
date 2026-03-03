import React from 'react';

/**
 * Metric card for the dashboard header row.
 * Displays a single KPI with icon, value, and label.
 */
export default function MetricCard({ title, value, icon, color = 'text-soc-accent', subtitle }) {
  return (
    <div className="bg-soc-card border border-soc-border rounded-xl p-5 flex items-center gap-4 hover:border-soc-accent/30 transition-colors">
      <div className={`text-3xl ${color} flex-shrink-0`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-soc-muted text-xs font-medium uppercase tracking-wider truncate">
          {title}
        </p>
        <p className={`text-2xl font-bold ${color} tabular-nums`}>
          {value !== null && value !== undefined ? value.toLocaleString() : '—'}
        </p>
        {subtitle && (
          <p className="text-soc-muted text-xs mt-0.5">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
