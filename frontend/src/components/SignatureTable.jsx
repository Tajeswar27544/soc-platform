import React from 'react';

const SEVERITY_BADGE = {
  1: 'bg-red-500/20 text-red-400 border-red-500/30',
  2: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  3: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  4: 'bg-green-500/20 text-green-400 border-green-500/30',
};

/**
 * Scrollable table of the most recently triggered signatures.
 */
export default function SignatureTable({ data = [] }) {
  return (
    <div className="bg-soc-card border border-soc-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-soc-muted uppercase tracking-wider mb-4">
        Most Triggered Signatures
      </h3>
      {data.length === 0 ? (
        <p className="text-soc-muted text-center py-6 text-sm">No data available</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-soc-muted text-xs uppercase border-b border-soc-border">
                <th className="text-left py-2 pr-4">#</th>
                <th className="text-left py-2 pr-4">Signature</th>
                <th className="text-right py-2">Count</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={idx} className="border-b border-soc-border/50 hover:bg-soc-bg/40 transition-colors">
                  <td className="py-2 pr-4 text-soc-muted">{idx + 1}</td>
                  <td className="py-2 pr-4 font-mono text-xs truncate max-w-xs" title={row.signature}>
                    {row.signature}
                  </td>
                  <td className="py-2 text-right tabular-nums font-semibold text-soc-accent">
                    {row.count.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
