"""
Pydantic response models for the SOC Platform REST API.

These models enforce a strict, documented JSON schema on every endpoint
response, ensuring the React frontend always receives predictable data.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AlertModel(BaseModel):
    """Single alert record as stored in SQLite."""
    id: int
    timestamp: str
    src_ip: str
    dest_ip: str
    signature: str
    severity: int
    category: str
    country: str
    protocol: str


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""
    count: int = Field(description="Number of alerts in this response")
    alerts: list[AlertModel]


class StatsResponse(BaseModel):
    """Dashboard summary statistics."""
    total_alerts: int
    high_severity_alerts: int
    alerts_last_hour: int


class IPCount(BaseModel):
    """Source IP with its alert count."""
    src_ip: str
    count: int


class TopIPsResponse(BaseModel):
    """Top N source IPs by frequency."""
    top_ips: list[IPCount]


class SeverityCount(BaseModel):
    """Alert count for a single severity level."""
    severity: int
    count: int


class SeverityDistributionResponse(BaseModel):
    """Severity breakdown."""
    distribution: list[SeverityCount]


class TimelineEntry(BaseModel):
    """Alert count in a one-hour bucket."""
    hour: str
    count: int


class TimelineResponse(BaseModel):
    """Hourly alert timeline."""
    timeline: list[TimelineEntry]


class CountryCount(BaseModel):
    """Alert count for a country."""
    country: str
    count: int


class CountryDistributionResponse(BaseModel):
    """Alerts grouped by country."""
    countries: list[CountryCount]


class SignatureCount(BaseModel):
    """Alert count for a signature."""
    signature: str
    count: int


class TopSignaturesResponse(BaseModel):
    """Most triggered signatures."""
    signatures: list[SignatureCount]


class HealthResponse(BaseModel):
    """Health-check response — includes subsystem liveness."""
    status: str = "ok"
    version: str = "1.0.0"
    monitor_alive: bool = True
    geoip_loaded: bool = False
    email_configured: bool = False
    alert_count: int = 0
    uptime_seconds: float = 0.0
