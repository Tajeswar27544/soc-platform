/**
 * SOC Platform API service.
 *
 * Centralises all backend HTTP calls. Uses axios with a base URL
 * that can be overridden via VITE_API_URL env var for production builds.
 *
 * Every public function accepts an optional AbortSignal so callers can
 * cancel in-flight requests when a newer poll cycle starts — preventing
 * stale responses from overwriting fresh data.
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Alerts ───────────────────────────────────────────────────────────────

export const fetchAlerts = async (limit = 500, offset = 0, signal) => {
  const { data } = await api.get('/alerts', { params: { limit, offset }, signal });
  return data;
};

export const fetchLatestAlerts = async (count = 20, signal) => {
  const { data } = await api.get('/alerts/latest', { params: { count }, signal });
  return data;
};

export const fetchAlertsBySeverity = async (level, limit = 200, signal) => {
  const { data } = await api.get(`/alerts/severity/${level}`, { params: { limit }, signal });
  return data;
};

/**
 * Incremental fetch — returns only alerts with id > lastId.
 * Use this for the live-feed panel to avoid re-fetching everything.
 */
export const fetchAlertsAfter = async (lastId, limit = 200, signal) => {
  const { data } = await api.get(`/alerts/after/${lastId}`, { params: { limit }, signal });
  return data;
};

// ── Analytics ────────────────────────────────────────────────────────────

export const fetchStats = async (signal) => {
  const { data } = await api.get('/alerts/stats', { signal });
  return data;
};

export const fetchTopIPs = async (limit = 10, signal) => {
  const { data } = await api.get('/alerts/top-ips', { params: { limit }, signal });
  return data;
};

export const fetchSeverityDistribution = async (signal) => {
  const { data } = await api.get('/alerts/severity-distribution', { signal });
  return data;
};

export const fetchTimeline = async (hours = 24, signal) => {
  const { data } = await api.get('/alerts/timeline', { params: { hours }, signal });
  return data;
};

export const fetchCountries = async (limit = 20, signal) => {
  const { data } = await api.get('/alerts/countries', { params: { limit }, signal });
  return data;
};

export const fetchTopSignatures = async (limit = 10, signal) => {
  const { data } = await api.get('/alerts/top-signatures', { params: { limit }, signal });
  return data;
};

// ── Health ────────────────────────────────────────────────────────────────

export const fetchHealth = async (signal) => {
  const { data } = await api.get('/health', { signal });
  return data;
};

export default api;
