/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        soc: {
          bg:       '#0a0e1a',
          surface:  '#111827',
          card:     '#1a2035',
          border:   '#1e293b',
          accent:   '#3b82f6',
          danger:   '#ef4444',
          warning:  '#f59e0b',
          success:  '#10b981',
          text:     '#e2e8f0',
          muted:    '#64748b',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
    },
  },
  plugins: [],
};
