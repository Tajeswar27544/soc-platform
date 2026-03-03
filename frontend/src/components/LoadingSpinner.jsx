import React from 'react';

/**
 * Reusable loading spinner.
 */
export default function LoadingSpinner({ message = 'Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <div className="w-8 h-8 border-2 border-soc-accent border-t-transparent rounded-full animate-spin" />
      <p className="text-soc-muted text-sm">{message}</p>
    </div>
  );
}
