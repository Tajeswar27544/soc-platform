import React from 'react';

/**
 * Table showing alert counts grouped by country.
 */
export default function CountryTable({ data = [] }) {
  const maxCount = data.length > 0 ? data[0].count : 1;

  return (
    <div className="bg-soc-card border border-soc-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-soc-muted uppercase tracking-wider mb-4">
        Country Distribution
      </h3>
      {data.length === 0 ? (
        <p className="text-soc-muted text-center py-6 text-sm">No data available</p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {data.map((row, idx) => {
            const pct = Math.round((row.count / maxCount) * 100);
            return (
              <div key={idx} className="flex items-center gap-3">
                <span className="text-xs text-soc-muted w-5 text-right">{idx + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm truncate">{row.country || 'Unknown'}</span>
                    <span className="text-xs font-semibold text-soc-accent tabular-nums ml-2">
                      {row.count.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-1.5 bg-soc-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
