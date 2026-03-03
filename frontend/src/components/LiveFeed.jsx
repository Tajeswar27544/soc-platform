import React from 'react';

const SEVERITY_BADGE = {
    1: 'bg-red-500/20 text-red-400',
    2: 'bg-amber-500/20 text-amber-400',
    3: 'bg-blue-500/20 text-blue-400',
    4: 'bg-green-500/20 text-green-400',
};

const SEVERITY_LABEL = { 1: 'CRIT', 2: 'HIGH', 3: 'MED', 4: 'LOW' };

/**
 * Live feed panel showing the most recent alerts with auto-scroll feel.
 */
export default function LiveFeed({ alerts = [] }) {
    return (
        <div className="bg-soc-card border border-soc-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
                <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse-dot" />
                <h3 className="text-sm font-semibold text-soc-muted uppercase tracking-wider">
                    Live Feed
                </h3>
                <span className="text-xs text-soc-muted ml-auto">auto-refresh 5s</span>
            </div>

            {alerts.length === 0 ? (
                <p className="text-soc-muted text-center py-6 text-sm">Waiting for alerts…</p>
            ) : (
                <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                    {alerts.map((a, idx) => (
                        <div
                            key={a.id || idx}
                            className="flex items-start gap-3 p-3 rounded-lg bg-soc-bg/60 border border-soc-border/50 hover:border-soc-accent/30 transition-colors"
                        >
                            {/* Severity badge */}
                            <span
                                className={`inline-flex items-center justify-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${SEVERITY_BADGE[a.severity] || SEVERITY_BADGE[4]}`}
                            >
                                {SEVERITY_LABEL[a.severity] || 'UNK'}
                            </span>

                            {/* Alert details */}
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-medium truncate" title={a.signature}>
                                    {a.signature}
                                </p>
                                <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-xs text-soc-muted">
                                    <span>{a.src_ip} → {a.dest_ip}</span>
                                    <span>{a.protocol}</span>
                                    <span>{a.country}</span>
                                </div>
                            </div>

                            {/* Timestamp */}
                            <span className="text-[10px] text-soc-muted whitespace-nowrap flex-shrink-0">
                                {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : '—'}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
