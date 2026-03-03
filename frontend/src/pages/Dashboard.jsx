import React, { useState, useEffect, useCallback, useRef } from 'react';
import MetricCard from '../components/MetricCard';
import SeverityChart from '../components/SeverityChart';
import TimelineChart from '../components/TimelineChart';
import TopIPsChart from '../components/TopIPsChart';
import SignatureTable from '../components/SignatureTable';
import CountryTable from '../components/CountryTable';
import LiveFeed from '../components/LiveFeed';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import {
  fetchStats,
  fetchAlerts,
  fetchLatestAlerts,
  fetchAlertsAfter,
  fetchSeverityDistribution,
  fetchTimeline,
  fetchTopIPs,
  fetchCountries,
  fetchTopSignatures,
  fetchHealth,
} from '../services/api';

const POLL_INTERVAL = 5000; // 5 seconds
const MAX_BACKOFF   = 30000; // cap error-backoff at 30s

/**
 * Main dashboard page — assembles all widgets into a responsive grid
 * and handles auto-refresh polling with:
 *   - AbortController to cancel stale in-flight requests
 *   - Exponential backoff on consecutive errors
 *   - Incremental live-feed via /alerts/after/:id
 */
export default function Dashboard() {
  // ── State ──────────────────────────────────────────────────────────────
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [severityDist, setSeverityDist] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [topIPs, setTopIPs] = useState([]);
  const [countries, setCountries] = useState([]);
  const [signatures, setSignatures] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Refs survive re-renders — used for incremental tracking & backoff
  const lastAlertIdRef = useRef(0);
  const abortRef = useRef(null);
  const errorCountRef = useRef(0);

  // ── Data fetcher ───────────────────────────────────────────────────────
  const loadDashboard = useCallback(async (isInitial = false) => {
    // Cancel any previous in-flight request to avoid stale overwrites
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;

    try {
      if (isInitial) setLoading(true);

      // Use allSettled so one failing endpoint never wipes the whole dashboard.
      // Individual failures are logged; the panel simply shows its last value.
      const [
        statsRes,
        alertsRes,
        sevRes,
        timeRes,
        ipsRes,
        countryRes,
        sigRes,
        healthRes,
      ] = await Promise.allSettled([
        fetchStats(signal),
        fetchAlerts(50, 0, signal),
        fetchSeverityDistribution(signal),
        fetchTimeline(24, signal),
        fetchTopIPs(10, signal),
        fetchCountries(20, signal),
        fetchTopSignatures(10, signal),
        fetchHealth(signal),
      ]);

      // Helper: return value or undefined on rejection
      const ok = (r) => (r.status === 'fulfilled' ? r.value : undefined);

      // Abort cancellations should silently exit, not count as errors
      const allAborted = [statsRes, alertsRes, sevRes, timeRes, ipsRes, countryRes, sigRes, healthRes]
        .every((r) => r.status === 'rejected' &&
          (r.reason?.name === 'CanceledError' || r.reason?.code === 'ERR_CANCELED'));
      if (allAborted || signal.aborted) return;

      // ── Update stats & charts (always full refresh from backend) ──
      if (ok(statsRes))   setStats(ok(statsRes));
      if (ok(sevRes))     setSeverityDist(ok(sevRes).distribution || []);
      if (ok(timeRes))    setTimeline(ok(timeRes).timeline || []);
      if (ok(ipsRes))     setTopIPs(ok(ipsRes).top_ips || []);
      if (ok(countryRes)) setCountries(ok(countryRes).countries || []);
      if (ok(sigRes))     setSignatures(ok(sigRes).signatures || []);
      if (ok(healthRes))  setHealth(ok(healthRes));

      // ── Set alerts for live feed ───────────────────────────────────
      if (ok(alertsRes)) {
        const incoming = ok(alertsRes).alerts || [];
        setAlerts(incoming);
      }

      // Collect any non-abort errors for the banner
      const failures = [statsRes, alertsRes, sevRes, timeRes, ipsRes, countryRes, sigRes, healthRes]
        .filter((r) => r.status === 'rejected' &&
          r.reason?.name !== 'CanceledError' && r.reason?.code !== 'ERR_CANCELED');

      if (failures.length > 0) {
        const msg = failures[0].reason?.message || 'One or more backend endpoints failed';
        console.warn('Partial dashboard failure:', failures.map((f) => f.reason?.message));
        setError(msg);
        errorCountRef.current += 1;
      } else {
        setError(null);
        errorCountRef.current = 0;
      }

      setLastUpdate(new Date());
    } catch (err) {
      // Don't treat aborted requests as errors
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED' || signal.aborted) {
        return;
      }
      console.error('Dashboard fetch error:', err);
      errorCountRef.current += 1;
      setError(err.message || 'Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Initial load + polling with error backoff ──────────────────────────
  useEffect(() => {
    loadDashboard(true);

    let timer;
    const scheduleNext = () => {
      const backoff = errorCountRef.current > 0
        ? Math.min(POLL_INTERVAL * 2 ** errorCountRef.current, MAX_BACKOFF)
        : POLL_INTERVAL;
      timer = setTimeout(() => {
        loadDashboard(false).finally(scheduleNext);
      }, backoff);
    };
    scheduleNext();

    return () => {
      clearTimeout(timer);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [loadDashboard]);

  // ── Render ─────────────────────────────────────────────────────────────
  if (loading && !stats) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner message="Connecting to SOC backend…" />
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 max-w-[1600px] mx-auto">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            <span className="text-soc-accent">◆</span> SOC Monitoring Platform
          </h1>
          <p className="text-soc-muted text-sm mt-0.5">
            Network Intrusion Detection Dashboard
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Live indicator — turns red when monitor is down */}
          <span className="flex items-center gap-1.5 text-xs text-soc-muted">
            <span className={`h-2 w-2 rounded-full ${health?.monitor_alive !== false ? 'bg-green-400 animate-pulse-dot' : 'bg-red-400'}`} />
            {health?.monitor_alive !== false ? 'Live' : 'Monitor Down'}
          </span>
          {health && !health.geoip_loaded && (
            <span className="text-[10px] text-amber-400" title="GeoIP DB not loaded — country data unavailable">
              ⚠ GeoIP
            </span>
          )}
          {health && !health.email_configured && (
            <span className="text-[10px] text-amber-400" title="SMTP not configured — email alerts disabled">
              ⚠ Email
            </span>
          )}
          {lastUpdate && (
            <span className="text-xs text-soc-muted">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      {/* ── Error banner ───────────────────────────────────────────────── */}
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => loadDashboard(true)} />
        </div>
      )}

      {/* ── Metric cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <MetricCard
          title="Total Alerts"
          value={stats?.total_alerts}
          icon="🛡"
          color="text-soc-accent"
        />
        <MetricCard
          title="High Severity"
          value={stats?.high_severity_alerts}
          icon="🔴"
          color="text-red-400"
          subtitle="Severity ≤ 2"
        />
        <MetricCard
          title="Last 1 Hour"
          value={stats?.alerts_last_hour}
          icon="⏱"
          color="text-amber-400"
        />
      </div>

      {/* ── Charts row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <SeverityChart data={severityDist} />
        <TimelineChart data={timeline} />
      </div>

      {/* ── Top IPs + Live Feed ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <TopIPsChart data={topIPs} />
        <LiveFeed alerts={alerts} />
      </div>

      {/* ── Tables row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <SignatureTable data={signatures} />
        <CountryTable data={countries} />
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="text-center text-soc-muted text-xs py-4 border-t border-soc-border mt-4">
        SOC Monitoring Platform v1.0 · Suricata IDS · Polling every {POLL_INTERVAL / 1000}s
        {health?.uptime_seconds > 0 && (
          <span> · Backend uptime: {Math.floor(health.uptime_seconds / 60)}m</span>
        )}
      </footer>
    </div>
  );
}
