#!/usr/bin/env python3
"""
SOC Platform Interactive CLI Setup Script
- Automates backend/frontend install
- Guides user for GeoIP and email config
- Downloads GeoLite2 if license key provided
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path('backend')
FRONTEND = Path('frontend')
PYTHON = sys.executable or 'python3'

# --- Helpers ---
def run(cmd, cwd=None, check=True):
    print(f"\033[96m$ {' '.join(cmd)}\033[0m")
    subprocess.run(cmd, cwd=cwd, check=check)

def prompt(msg, default=None, secret=False):
    import getpass
    if secret:
        return getpass.getpass(msg + (f' [{default}]' if default else '') + ': ') or default
    return input(msg + (f' [{default}]' if default else '') + ': ') or default

# --- Backend Setup ---
def setup_backend():
    print("\n[1/4] Python backend setup...")
    venv_dir = BACKEND / 'venv'
    if not venv_dir.exists():
        run([PYTHON, '-m', 'venv', 'venv'], cwd=BACKEND)
    # Detect pip path for Unix/Windows
    if os.name == 'nt':
        pip = venv_dir / 'Scripts' / 'pip.exe'
    else:
        pip = venv_dir / 'bin' / 'pip'
    if not pip.exists():
        print(f"[ERROR] pip not found at {pip}. Virtualenv creation may have failed.")
        sys.exit(1)
    run([str(pip), 'install', '--upgrade', 'pip'], cwd=BACKEND)
    run([str(pip), 'install', '-r', 'requirements.txt'], cwd=BACKEND)
    # .env
    env_path = BACKEND / '.env'
    if not env_path.exists():
        (BACKEND / '.env.example').replace(env_path)
        print("[INFO] .env created from .env.example")
    else:
        print("[INFO] .env already exists")

# --- Frontend Setup ---
def setup_frontend():
    print("\n[2/4] React frontend setup...")
    if not shutil.which('npm'):
        print("[ERROR] npm not found. Please install Node.js 18+ and npm.")
        sys.exit(1)
    run(['npm', 'install'], cwd=FRONTEND)

# --- GeoIP Download ---
def setup_geoip():
    print("\n[3/4] GeoIP setup...")
    geoip_path = BACKEND / 'GeoLite2-City.mmdb'
    if geoip_path.exists():
        print(f"[INFO] GeoLite2-City.mmdb already exists at {geoip_path}")
        return
    print("To enable country lookups, you need a MaxMind license key.")
    key = prompt("Enter your MaxMind GeoLite2 license key (or leave blank to skip)")
    if not key:
        print("[WARN] Skipping GeoIP download. You can add the .mmdb later.")
        return
    url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={key}&suffix=tar.gz"
    tgz = BACKEND / 'GeoLite2-City.tar.gz'
    run(['wget', url, '-O', str(tgz)])
    run(['tar', '-xzf', str(tgz)], cwd=BACKEND)
    for f in (BACKEND).glob('GeoLite2-City_*/GeoLite2-City.mmdb'):
        f.replace(geoip_path)
    run(['rm', '-rf', 'GeoLite2-City_*', 'GeoLite2-City.tar.gz'], cwd=BACKEND)
    print(f"[INFO] GeoLite2-City.mmdb downloaded to {geoip_path}")

# --- Email Config ---
def setup_email():
    print("\n[4/4] Email alert setup...")
    env_path = BACKEND / '.env'
    lines = env_path.read_text().splitlines()
    def set_env(key, value):
        for i, line in enumerate(lines):
            if line.startswith(key + '='):
                lines[i] = f"{key}={value}"
                return
        lines.append(f"{key}={value}")
    email = prompt("Enter SMTP_EMAIL for alerts (Gmail recommended)")
    if email:
        set_env('SMTP_EMAIL', email)
        pw = prompt("Enter SMTP_PASSWORD (Gmail App Password)", secret=True)
        set_env('SMTP_PASSWORD', pw)
        rcpt = prompt("Enter ALERT_RECIPIENT (alert destination email)", default=email)
        set_env('ALERT_RECIPIENT', rcpt)
        env_path.write_text('\n'.join(lines) + '\n')
        print("[INFO] Email config written to backend/.env")
    else:
        print("[WARN] Email alerts will be disabled (no SMTP_EMAIL set)")

# --- Main CLI ---
if __name__ == '__main__':
    import shutil
    print("\n=== SOC Platform Automated Setup ===\n")
    setup_backend()
    setup_frontend()
    setup_geoip()
    setup_email()
    print("\n[Done] Setup complete!\n")
    print("To start backend:  cd backend && source venv/bin/activate && python -m api.main")
    print("To start frontend: cd frontend && npm run dev\n")
