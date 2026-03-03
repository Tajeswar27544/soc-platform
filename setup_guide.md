# SOC Monitoring Platform — Complete Setup Guide

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Install Suricata on Ubuntu](#2-install-suricata-on-ubuntu)
3. [Configure Suricata for eve.json Output](#3-configure-suricata-for-evejson-output)
4. [Download GeoLite2 Database](#4-download-geolite2-database)
5. [Set Up the Backend](#5-set-up-the-backend)
6. [Configure Environment Variables](#6-configure-environment-variables)
7. [Run the Backend](#7-run-the-backend)
8. [Set Up the Frontend](#8-set-up-the-frontend)
9. [Run the React Dashboard](#9-run-the-react-dashboard)
10. [Simulate Attacks with Nmap](#10-simulate-attacks-with-nmap)
11. [Test Email Alerts](#11-test-email-alerts)
12. [Production Deployment Tips](#12-production-deployment-tips)

---

## 1. System Requirements

| Component | Minimum |
|---|---|
| OS | Ubuntu 20.04+ (tested on 22.04 LTS) |
| CPU | Intel i5 11th gen or equivalent |
| RAM | 8 GB |
| Disk | 10 GB free |
| Python | 3.10+ |
| Node.js | 18+ (LTS) |
| Network | Interface in promiscuous mode for Suricata |

---

## 2. Install Suricata on Ubuntu

```bash
# Add Suricata PPA for latest stable release
sudo add-apt-repository ppa:oisf/suricata-stable -y
sudo apt update

# Install Suricata
sudo apt install suricata suricata-update -y

# Verify installation
suricata --build-info | head -5

# Update rulesets (ET Open rules)
sudo suricata-update

# Enable and start Suricata service
sudo systemctl enable suricata
sudo systemctl start suricata

# Check status
sudo systemctl status suricata
```

### Find your network interface

```bash
ip -br link show
# Example output: enp0s3  UP  aa:bb:cc:dd:ee:ff
# Use the active interface name in the next step
```

---

## 3. Configure Suricata for eve.json Output

Edit the Suricata configuration:

```bash
sudo nano /etc/suricata/suricata.yaml
```

### Ensure eve-log is enabled (it is by default):

```yaml
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - alert:
            payload: yes
            payload-printable: yes
            packet: yes
            metadata: yes
            http-body: yes
            http-body-printable: yes
        - dns
        - http
        - tls
        - files
        - stats:
            totals: yes
            threads: no
```

### Set the correct network interface:

```yaml
af-packet:
  - interface: enp0s3    # <-- Replace with your interface
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
```

### Set HOME_NET to your LAN:

```yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"
```

### Restart Suricata:

```bash
sudo systemctl restart suricata

# Verify eve.json is being written
ls -la /var/log/suricata/eve.json
tail -f /var/log/suricata/eve.json | head -5
```

---

## 4. Download GeoLite2 Database

MaxMind requires a free account to download GeoLite2 databases.

### Step 1: Register at MaxMind

1. Go to https://www.maxmind.com/en/geolite2/signup
2. Create a free account
3. Generate a license key at: Account → Manage License Keys → Generate New License Key

### Step 2: Download the database

```bash
cd soc-platform/backend/

# Option A: Direct download (replace YOUR_LICENSE_KEY)
wget "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=YOUR_LICENSE_KEY&suffix=tar.gz" -O GeoLite2-City.tar.gz

# Extract
tar -xzf GeoLite2-City.tar.gz
cp GeoLite2-City_*/GeoLite2-City.mmdb .
rm -rf GeoLite2-City_* GeoLite2-City.tar.gz

# Option B: Using geoipupdate (recommended for auto-updates)
sudo apt install geoipupdate -y

# Edit /etc/GeoIP.conf with your account ID and license key:
# AccountID YOUR_ACCOUNT_ID
# LicenseKey YOUR_LICENSE_KEY
# EditionIDs GeoLite2-City

sudo geoipupdate
# Default download location: /usr/share/GeoIP/GeoLite2-City.mmdb
```

### Verify the database:

```bash
ls -la GeoLite2-City.mmdb
# Should be ~60-70 MB
```

---

## 5. Set Up the Backend

```bash
cd soc-platform/backend/

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify imports work
python -c "import fastapi, geoip2, uvicorn; print('All dependencies OK')"
```

---

## 6. Configure Environment Variables

Create a `.env` file or export variables in your shell:

```bash
# Required paths
export EVE_JSON_PATH="/var/log/suricata/eve.json"
export GEOIP_DB_PATH="/path/to/soc-platform/backend/GeoLite2-City.mmdb"

# Email alerts (optional — works without, just won't send emails)
export SMTP_EMAIL="your-soc-email@gmail.com"
export SMTP_PASSWORD="your-gmail-app-password"
export ALERT_RECIPIENT="analyst@example.com"

# Optional tuning
export LOG_LEVEL="INFO"
export API_PORT="8000"
export MONITOR_POLL_INTERVAL="1.0"
```

### Gmail App Password Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Generate an app password for "Mail" → "Other (Custom name)" → "SOC Platform"
4. Use the 16-character password as `SMTP_PASSWORD`

> **Never use your actual Gmail password.** Always use App Passwords.

---

## 7. Run the Backend

### Option A: Unified mode (recommended — single process)

```bash
cd soc-platform/backend/
source venv/bin/activate

# The API server starts the log monitor in a background thread
python -m api.main
```

The server starts at `http://0.0.0.0:8000`. Visit `http://localhost:8000/docs` for interactive API documentation.

### Option B: Split mode (separate processes)

```bash
# Terminal 1 — Log monitor only
cd soc-platform/backend/
source venv/bin/activate
python -m monitor.log_monitor

# Terminal 2 — API only
cd soc-platform/backend/
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Verify the backend:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}

curl http://localhost:8000/alerts/stats
# {"total_alerts":0,"high_severity_alerts":0,"alerts_last_hour":0}
```

---

## 8. Set Up the Frontend

```bash
cd soc-platform/frontend/

# Install Node.js dependencies
npm install
```

---

## 9. Run the React Dashboard

```bash
cd soc-platform/frontend/

# Start Vite development server
npm run dev
```

Open `http://localhost:5173` in your browser.

The dashboard will immediately start polling `http://localhost:8000` every 5 seconds.

### Production build:

```bash
npm run build
# Static files output to dist/
# Serve with: npx serve dist/ or any static file server
```

---

## 10. Simulate Attacks with Nmap

Generate real Suricata alerts to test the pipeline end-to-end.

> **⚠ Only scan systems you own or have explicit permission to test!**

### Basic scans from another machine (or same machine targeting your IP):

```bash
# SYN scan — triggers "ET SCAN" rules
sudo nmap -sS -T4 192.168.1.100

# Aggressive scan — triggers multiple rule categories
sudo nmap -A -T4 192.168.1.100

# OS detection + service scan
sudo nmap -O -sV 192.168.1.100

# Full port scan — generates many alerts
sudo nmap -p- -T4 192.168.1.100

# UDP scan
sudo nmap -sU --top-ports 100 192.168.1.100

# Script-based vulnerability scan
sudo nmap --script vuln 192.168.1.100

# Generate lots of alerts quickly
sudo nmap -sS -sV -O -A --script vuln -p 1-10000 192.168.1.100
```

### Verify alerts appear:

```bash
# Check eve.json for new alert entries
sudo tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"'

# Check the API
curl http://localhost:8000/alerts/latest | python3 -m json.tool

# Check the dashboard — alerts should appear within 5 seconds
```

### Using hping3 for targeted testing:

```bash
sudo apt install hping3 -y

# SYN flood (low rate for testing)
sudo hping3 -S -p 80 --flood --rand-source 192.168.1.100

# Christmas tree scan
sudo hping3 -F -S -R -P -A -U -p 80 192.168.1.100
```

---

## 11. Test Email Alerts

### 1. Ensure SMTP is configured:

```bash
echo $SMTP_EMAIL    # Should show your Gmail address
echo $SMTP_PASSWORD # Should show your app password
```

### 2. Generate a high-severity alert:

Most nmap scans generate severity 1-2 alerts. Run:

```bash
# From another machine
sudo nmap -A --script vuln 192.168.1.100
```

### 3. Check the backend logs:

```bash
# Look for email-related log lines
# "Email alert sent for severity-1 event: ..."
```

### 4. Quick manual test (Python REPL):

```bash
cd soc-platform/backend/
source venv/bin/activate
python3 -c "
from monitor.email_alert import send_alert_email
test_alert = {
    'timestamp': '2026-01-01T00:00:00',
    'src_ip': '10.0.0.1',
    'dest_ip': '192.168.1.100',
    'signature': 'TEST: Manual email test',
    'severity': 1,
    'category': 'Test',
    'country': 'Testing',
    'protocol': 'TCP',
}
result = send_alert_email(test_alert)
print('Email sent!' if result else 'Email failed — check logs')
"
```

---

## 12. Production Deployment Tips

### Systemd service for the backend:

```bash
sudo nano /etc/systemd/system/soc-backend.service
```

```ini
[Unit]
Description=SOC Monitoring Platform Backend
After=network.target suricata.service

[Service]
Type=simple
User=soc
WorkingDirectory=/opt/soc-platform/backend
Environment=EVE_JSON_PATH=/var/log/suricata/eve.json
Environment=GEOIP_DB_PATH=/opt/soc-platform/backend/GeoLite2-City.mmdb
Environment=SMTP_EMAIL=your-email@gmail.com
Environment=SMTP_PASSWORD=your-app-password
ExecStart=/opt/soc-platform/backend/venv/bin/python -m api.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable soc-backend
sudo systemctl start soc-backend
```

### Serve frontend with Nginx:

```bash
sudo apt install nginx -y

# Build frontend
cd soc-platform/frontend && npm run build

# Copy to Nginx
sudo cp -r dist/* /var/www/html/

# Add API proxy to nginx config
sudo nano /etc/nginx/sites-available/default
```

```nginx
server {
    listen 80;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /alerts {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

```bash
sudo systemctl restart nginx
```
