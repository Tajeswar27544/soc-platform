# SOC Dashboard — Frontend

## Overview
React-based SOC monitoring dashboard built with Vite, Tailwind CSS, and Recharts. Consumes the FastAPI backend via REST API with 5-second auto-refresh polling.

## Quick Start

```bash
cd frontend/

# Install dependencies
npm install

# Start development server
npm run dev
```

Opens at `http://localhost:5173`. The Vite dev server proxies `/alerts` and `/health` requests to `http://localhost:8000` (the FastAPI backend).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

For production builds:
```bash
VITE_API_URL=https://your-api-server.com npm run build
```

## Build for Production

```bash
npm run build    # Output in dist/
npm run preview  # Preview production build locally
```

## Components

| Component | Description |
|---|---|
| `MetricCard` | KPI cards (total alerts, high severity, last hour) |
| `SeverityChart` | Bar chart of severity distribution |
| `TimelineChart` | Line chart of hourly alert counts |
| `TopIPsChart` | Horizontal bar chart of top source IPs |
| `SignatureTable` | Table of most triggered signatures |
| `CountryTable` | Country distribution with progress bars |
| `LiveFeed` | Real-time alert feed panel |
| `LoadingSpinner` | Loading state indicator |
| `ErrorBanner` | API error display with retry button |
