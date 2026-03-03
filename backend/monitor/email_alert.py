"""
Email alerting module for high-severity Suricata alerts.

Sends HTML-formatted email via Gmail SMTP (SSL on port 465).
Credentials are sourced exclusively from environment variables —
SMTP_EMAIL and SMTP_PASSWORD must be set before running.

Security note:
    Gmail "App Passwords" or OAuth2 tokens should be used.
    Never commit credentials to version control.
"""

import smtplib
import logging
import time as _time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from monitor.config import (
    SMTP_EMAIL,
    SMTP_PASSWORD,
    SMTP_HOST,
    SMTP_PORT,
    ALERT_RECIPIENT,
    EMAIL_SEVERITY_THRESHOLD,
)

logger: logging.Logger = logging.getLogger("soc.email_alert")


def _build_email_body(alert: dict) -> str:
    """Construct an HTML email body from an alert dict."""
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #16213e; border-radius: 8px; padding: 24px; border-left: 4px solid #e94560;">
            <h2 style="color: #e94560; margin-top: 0;">⚠️ HIGH SEVERITY ALERT</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px; color: #a0a0a0;">Timestamp</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('timestamp', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Signature</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('signature', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Severity</td>
                    <td style="padding: 8px; color: #e94560; font-weight: bold;">{alert.get('severity', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Category</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('category', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Source IP</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('src_ip', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Destination IP</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('dest_ip', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Country</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('country', 'Unknown')}</td></tr>
                <tr><td style="padding: 8px; color: #a0a0a0;">Protocol</td>
                    <td style="padding: 8px; color: #ffffff;">{alert.get('protocol', 'N/A')}</td></tr>
            </table>
            <hr style="border-color: #2a2a4a; margin: 16px 0;">
            <p style="font-size: 12px; color: #666;">SOC Platform — Automated Alert Notification</p>
        </div>
    </body>
    </html>
    """


def should_send_email(severity: int) -> bool:
    """Determine whether an alert warrants an email notification.

    Suricata severity scale:
        1 = Critical / High — active exploitation, malware C2, etc.
        2 = Medium-High   — suspicious activity, policy violations.
        3 = Informational — low-confidence or benign matches.
        4 = Not suspicious.

    We email on severity <= threshold (default 2) because these
    represent real threats that need immediate analyst attention.
    """
    return severity <= EMAIL_SEVERITY_THRESHOLD


def send_alert_email(alert: dict, retries: int = 2) -> bool:
    """Send an email alert for a high-severity event.

    Retries up to *retries* times with exponential backoff on transient
    SMTP failures.  Returns True on success, False on final failure.
    Never raises — email delivery failures must not crash the pipeline.
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning(
            "SMTP credentials not configured — skipping email for alert: %s",
            alert.get("signature", "?"),
        )
        return False

    last_exc: Exception | None = None
    for attempt in range(1, retries + 2):  # 1 initial + retries
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"[SOC ALERT] Severity {alert.get('severity', '?')} — "
                f"{alert.get('signature', 'Unknown Signature')}"
            )
            msg["From"] = SMTP_EMAIL
            msg["To"] = ALERT_RECIPIENT

            html_body: str = _build_email_body(alert)
            msg.attach(MIMEText(html_body, "html"))

            # Gmail SSL connection on port 465
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.sendmail(SMTP_EMAIL, ALERT_RECIPIENT, msg.as_string())

            logger.info(
                "Email alert sent for severity-%s event: %s",
                alert.get("severity"),
                alert.get("signature"),
            )
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP authentication failed — check SMTP_EMAIL and SMTP_PASSWORD env vars"
            )
            return False  # don't retry auth failures
        except (smtplib.SMTPException, OSError) as exc:
            last_exc = exc
            if attempt <= retries:
                backoff = 2 ** (attempt - 1)  # 1s, 2s
                logger.warning(
                    "SMTP attempt %d/%d failed (%s) — retrying in %ds",
                    attempt, retries + 1, exc, backoff,
                )
                _time.sleep(backoff)
            else:
                logger.error("SMTP error sending alert email after %d attempts: %s", attempt, exc)
        except Exception as exc:
            logger.error("Unexpected error sending alert email: %s", exc)
            return False

    return False


def is_email_configured() -> bool:
    """Return True if SMTP credentials are set."""
    return bool(SMTP_EMAIL and SMTP_PASSWORD)
