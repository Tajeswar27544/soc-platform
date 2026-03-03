#!/usr/bin/env bash
# SOC Platform Automated Setup Script
# Usage: bash setup.sh
set -e

# --- Config ---
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
PYTHON_VERSION="3.10"

# --- Check Python ---
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 not found. Please install Python $PYTHON_VERSION+ first." >&2
  exit 1
fi

# --- Backend Setup ---
echo "[1/4] Setting up Python backend..."
cd "$BACKEND_DIR"

# Create venv if not exists
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env.example if .env does not exist
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[INFO] Copied .env.example to .env. Please edit backend/.env for GeoIP and email settings."
fi
cd ..

# --- Frontend Setup ---
echo "[2/4] Setting up React frontend..."
cd "$FRONTEND_DIR"
if ! command -v npm &>/dev/null; then
  echo "[ERROR] npm not found. Please install Node.js 18+ and npm." >&2
  exit 1
fi
npm install
cd ..

# --- GeoIP Reminder ---
echo "[3/4] GeoIP setup reminder:"
echo "  - Download GeoLite2-City.mmdb from https://www.maxmind.com/en/geolite2/signup"
echo "  - Place it in backend/ and set GEOIP_DB_PATH in backend/.env"

# --- Email Reminder ---
echo "[4/4] Email alerts:"
echo "  - Set SMTP_EMAIL, SMTP_PASSWORD, ALERT_RECIPIENT in backend/.env for email alerts (see README)"

echo "[DONE] Setup complete."
echo "To start backend:"
echo "  cd backend && source venv/bin/activate && python -m api.main"
echo "To start frontend:"
echo "  cd frontend && npm run dev"
