import React from 'react';

/**
 * Error banner displayed when API calls fail.
 */
export default function ErrorBanner({ message, onRetry }) {
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
      <span className="text-red-400 text-xl flex-shrink-0">⚠</span>
      <div className="flex-1 min-w-0">
        <p className="text-red-400 text-sm font-medium">Connection Error</p>
        <p className="text-red-400/70 text-xs mt-0.5 truncate">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-xs bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
