#!/usr/bin/env python3
"""
SOC Platform — Interactive CLI Setup
Run from the project root:  python3 setup.py
"""

import getpass
import glob
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── All paths are absolute so subprocess never gets confused ──────────────────
ROOT    = Path(__file__).resolve().parent
BACKEND = ROOT / 'backend'
FRONTEND = ROOT / 'frontend'
PYTHON  = sys.executable           # same interpreter that is running this script

# Ensure backend package is importable for helpers (e.g., monitor.geoip)
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

IS_WIN = os.name == 'nt'
PIP    = BACKEND / 'venv' / ('Scripts/pip.exe' if IS_WIN else 'bin/pip')
VENV_PYTHON = BACKEND / 'venv' / ('Scripts/python.exe' if IS_WIN else 'bin/python')

# ── ANSI colour helpers ───────────────────────────────────────────────────────
def _c(code, text): return f"\033[{code}m{text}\033[0m"
def cyan(t):   return _c(96, t)
def green(t):  return _c(92, t)
def yellow(t): return _c(93, t)
def red(t):    return _c(91, t)
def bold(t):   return _c(1,  t)
def dim(t):    return _c(2,  t)

def header(title):
    w = 60
    print()
    print(cyan('─' * w))
    print(cyan('  ') + bold(title))
    print(cyan('─' * w))

def ok(msg):   print(green('  ✓ ') + msg)
def warn(msg): print(yellow('  ⚠ ') + msg)
def info(msg): print(dim  ('  · ') + msg)
def err(msg):  print(red  ('  ✗ ') + msg); sys.exit(1)

def run(cmd, cwd=None, capture=False):
    """Run a command, printing it first.  Exits on failure."""
    pretty = ' '.join(str(c) for c in cmd)
    print(cyan(f'    $ {pretty}'))
    result = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=capture,
    )
    if result.returncode != 0:
        err(f'Command failed (exit {result.returncode}): {pretty}')
    return result

def ask(question, default='', secret=False):
    suffix = f' [{default}]' if default else ''
    prompt = bold(f'  ? {question}') + dim(suffix) + ': '
    try:
        answer = (getpass.getpass(prompt) if secret else input(prompt)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return answer or default

def ask_yn(question, default=True):
    hint = '[Y/n]' if default else '[y/N]'
    answer = ask(f'{question} {hint}').lower()
    if answer in ('y', 'yes'): return True
    if answer in ('n', 'no'):  return False
    return default


def _is_port_open(port, host='127.0.0.1', timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_http(url, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                if 200 <= r.status < 500:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def _start_backend_api():
    health_url = 'http://127.0.0.1:8000/health'
    if _wait_for_http(health_url, timeout=2.0):
        ok('Backend API already running on port 8000 — reusing existing process')
        return None

    proc = subprocess.Popen(
        [str(VENV_PYTHON), '-m', 'api.main'],
        cwd=str(BACKEND),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_for_http(health_url, timeout=25.0):
        err('Backend API failed to become healthy on http://localhost:8000/health')
    ok(f'Backend API running (PID: {proc.pid})')
    return proc


def _start_frontend_dev():
    # Prefer stable URL if already occupied by a running dev server.
    if _wait_for_http('http://127.0.0.1:5173', timeout=2.0):
        ok('Frontend already running on port 5173 — reusing existing process')
        return None, 5173

    for port in range(5173, 5183):
        if _is_port_open(port):
            continue
        proc = subprocess.Popen(
            ['npm', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
            cwd=str(FRONTEND),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if _wait_for_http(f'http://127.0.0.1:{port}', timeout=25.0):
            ok(f'Frontend dev server running (PID: {proc.pid}) on port {port}')
            return proc, port
        if proc.poll() is None:
            proc.terminate()
    err('Frontend dev server failed to start on ports 5173-5182')


def _install_apt_packages(packages, reason):
    """Install missing Debian/Ubuntu packages via apt."""
    if not packages:
        return
    if not shutil.which('apt'):
        err(f'Missing packages for {reason}: {", ".join(packages)} (apt not available)')
    info(f'Missing system packages for {reason}: {", ".join(packages)}')
    if ask_yn(f'Install missing packages for {reason} via apt (requires sudo)?', default=True):
        run(['sudo', 'apt', 'update'])
        run(['sudo', 'apt', 'install', '-y', *packages])
    else:
        err(f'Cannot continue without required packages for {reason}')


def step_system_tools():
    header('Step 1 / 6 — System Tools')

    if IS_WIN:
        warn('Automatic Linux package setup skipped on Windows')
        return

    required_tools = {
        'ip': 'iproute2',
        'wget': 'wget',
        'tar': 'tar',
        'curl': 'curl',
        'sqlite3': 'sqlite3',
    }
    missing_pkgs = []
    for binary, pkg in required_tools.items():
        if not shutil.which(binary):
            missing_pkgs.append(pkg)

    # Deduplicate while preserving order.
    missing_pkgs = list(dict.fromkeys(missing_pkgs))
    _install_apt_packages(missing_pkgs, 'SOC setup and diagnostics')

    # Optional but strongly recommended for attack simulation testing.
    if not shutil.which('nmap'):
        if ask_yn('nmap not found. Install nmap for IDS testing?', default=True):
            _install_apt_packages(['nmap'], 'IDS test traffic generation')
        else:
            warn('nmap not installed — you can still run the platform, but attack simulation is limited')

    ok('System tool checks complete')

# ── Step 1: Python backend ────────────────────────────────────────────────────
def step_backend():
    header('Step 2 / 6 — Python Backend')

    # Create venv
    if (BACKEND / 'venv').exists():
        ok('Virtual environment already exists — skipping creation')
    else:
        info('Creating virtual environment …')
        run([PYTHON, '-m', 'venv', 'venv'], cwd=BACKEND)
        ok('Virtual environment created')

    if not PIP.exists():
        err(f'pip not found at {PIP} — venv creation may have failed')

    # Install deps
    info('Upgrading pip …')
    run([PIP, 'install', '--upgrade', 'pip', '-q'])

    info('Installing Python dependencies …')
    run([PIP, 'install', '-r', BACKEND / 'requirements.txt', '-q'])
    ok('Python dependencies installed')

    # .env
    env_path    = BACKEND / '.env'
    env_example = BACKEND / '.env.example'
    if not env_path.exists():
        shutil.copy(env_example, env_path)
        ok('.env created from .env.example')
    else:
        ok('.env already exists')

# ── Step 2: Node / React frontend ────────────────────────────────────────────
def step_frontend():
    header('Step 3 / 6 — React Frontend')

    if not shutil.which('npm'):
        info('npm not found on PATH')
        # On Windows we can't auto-install; guide the user.
        if IS_WIN:
            err('npm not found — please install Node.js 18+ (https://nodejs.org)')

        # Try Debian/Ubuntu automatic install if `apt` is available.
        if shutil.which('apt'):
            if ask_yn('npm not found. Attempt to install Node.js/npm via apt (requires sudo)?', default=True):
                info('Installing Node.js and npm via apt (requires sudo)...')
                run(['sudo', 'apt', 'update'])
                run(['sudo', 'apt', 'install', '-y', 'nodejs', 'npm'])
                if not shutil.which('npm'):
                    warn('Installation finished but npm still not found.')
                    err('npm not found — please install Node.js 18+ manually (https://nodejs.org)')
                else:
                    ok('npm installed')
            else:
                err('npm not found — please install Node.js 18+ (https://nodejs.org)')
        else:
            err('npm not found — please install Node.js 18+ (https://nodejs.org)')

    info('Running npm install …')
    run(['npm', 'install', '--silent'], cwd=FRONTEND)
    ok('Frontend dependencies installed')

# ── Step 3: GeoIP database ───────────────────────────────────────────────────
def step_geoip():
    header('Step 5 / 6 — GeoIP Database (optional)')

    mmdb = BACKEND / 'GeoLite2-City.mmdb'
    if mmdb.exists():
        ok(f'GeoLite2-City.mmdb already present')
        set_env_value('GEOIP_DB_PATH', str(mmdb))
        return

    import sys
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    try:
        from monitor.geoip import download_geoip_db
    except Exception as exc:
        download_geoip_db = None
        warn(f'GeoIP helper unavailable ({exc}) — skipping auto-download')
        warn('You can place GeoLite2-City.mmdb in backend/ later and re-run setup')
        return

    print(dim('  Country lookups require the free MaxMind GeoLite2-City database.'))
    print(dim('  Sign up at https://www.maxmind.com/en/geolite2/signup to get a license key.'))
    print()

    license_key = (os.getenv('MAXMIND_LICENSE_KEY') or '').strip()
    if license_key:
        info('Using MAXMIND_LICENSE_KEY from environment for GeoIP download')
    else:
        if not ask_yn('Do you have a MaxMind license key?', default=False):
            warn('Skipping GeoIP — country lookups will show "Unknown"')
            warn('You can re-run this script or place GeoLite2-City.mmdb in backend/ later')
            return

        license_key = ask('MaxMind license key')
        if not license_key:
            warn('No key entered — skipping GeoIP')
            return

    info('Downloading GeoLite2-City.mmdb …')
    success = download_geoip_db(mmdb, license_key=license_key)
    if not success:
        warn('GeoIP download failed — country lookups will show "Unknown"')
        warn('You can retry later by re-running setup or python -m monitor.geoip --output backend/GeoLite2-City.mmdb')
        return

    set_env_value('GEOIP_DB_PATH', str(mmdb))
    ok(f'GeoLite2-City.mmdb installed → {mmdb}')

import re

# ── Step 4: Suricata auto-config (optional) ───────────────────────────────────
def step_suricata():
    header('Step 4 / 6 — Suricata Network Interface')
    if not shutil.which('suricata'):
        info('Suricata not found. Attempting to install via apt (requires sudo)...')
        if shutil.which('apt'):
            run(['sudo', 'apt', 'update'])
            run(['sudo', 'apt', 'install', '-y', 'suricata', 'suricata-update'])
            if not shutil.which('suricata'):
                err('Suricata installation failed. Please install manually.')
            else:
                ok('Suricata installed')
        else:
            err('Suricata not found and apt not available. Please install Suricata manually.')

    if not shutil.which('suricata-update'):
        warn('suricata-update not found; attempting install (requires sudo)...')
        if shutil.which('apt'):
            run(['sudo', 'apt', 'install', '-y', 'suricata-update'])
        else:
            err('suricata-update missing and apt not available. Install it manually.')

    # List interfaces (skip loopback)
    info('Detecting network interfaces …')
    result = subprocess.run(['ip', 'link'], capture_output=True, text=True)
    if result.returncode != 0:
        warn('Could not list interfaces (ip link failed)')
        return
    # Parse interface names
    import re
    ifaces = re.findall(r'\d+: ([^:]+):', result.stdout)
    ifaces = [i for i in ifaces if i != 'lo']
    if not ifaces:
        warn('No non-loopback interfaces found')
        return
    print('  Available interfaces:')
    for idx, iface in enumerate(ifaces):
        print(f'    {idx+1}. {iface}')
    choice = ask('Select interface to monitor (number)', default='1')
    try:
        iface = ifaces[int(choice)-1]
    except Exception:
        warn('Invalid selection, skipping Suricata config')
        return
    # Patch suricata.yaml
    yaml_path = '/etc/suricata/suricata.yaml'
    if not os.path.exists(yaml_path):
        warn(f'Suricata config not found at {yaml_path}')
        return
    # Read and patch config
    with open(yaml_path, 'r') as f:
        lines = f.readlines()
    new_lines = []
    in_af_packet = False
    replaced = False
    for line in lines:
        if line.strip().startswith('af-packet:'):
            in_af_packet = True
            new_lines.append(line)
            continue
        if in_af_packet and re.match(r'\s*- interface:', line):
            # Replace interface line
            indent = re.match(r'(\s*)- interface:', line).group(1)
            new_lines.append(f'{indent}- interface: {iface}\n')
            replaced = True
            in_af_packet = False  # only replace first occurrence
            continue
        new_lines.append(line)
    if not replaced:
        warn('Could not find af-packet interface line to replace; skipping patch')
        return
    # Write patched config (with sudo)
    import tempfile
    with tempfile.NamedTemporaryFile('w', delete=False) as tf:
        tf.writelines(new_lines)
        temp_path = tf.name
    print(cyan(f'    $ sudo cp {temp_path} {yaml_path}'))
    run(['sudo', 'cp', temp_path, yaml_path])
    os.unlink(temp_path)
    ok(f'Suricata config updated to use interface: {iface}')

    info('Updating Suricata detection rules …')
    run(['sudo', 'suricata-update'])

    rules_file = '/var/lib/suricata/rules/suricata.rules'
    if not os.path.exists(rules_file) or os.path.getsize(rules_file) == 0:
        err(f'Suricata rules file missing or empty: {rules_file}')
    ok(f'Suricata rules ready: {rules_file}')

    run(['sudo', 'systemctl', 'restart', 'suricata'])
    ok('Suricata service restarted')

    # Ensure backend ingests real Suricata log, not test sample file.
    set_env_value('EVE_JSON_PATH', '/var/log/suricata/eve.json')
    ok('Backend EVE_JSON_PATH set to /var/log/suricata/eve.json')

def step_email():
    header('Step 6 / 6 — Email Alerts (optional)')
    print(dim('  High-severity alerts can be emailed via Gmail SMTP.'))
    print(dim('  Requires a Gmail App Password: https://myaccount.google.com/apppasswords'))
    print()

    if not ask_yn('Configure email alerts?', default=False):
        warn('Skipping email — alerts will be visible on the dashboard only')
        return

    email = ask('Gmail address (SMTP_EMAIL)')
    if not email:
        warn('No address entered — skipping email')
        return

    pw   = ask('Gmail App Password (16 chars)', secret=True)
    rcpt = ask('Alert recipient email', default=email)

    set_env_value('SMTP_EMAIL',       email)
    set_env_value('SMTP_PASSWORD',    pw)
    set_env_value('ALERT_RECIPIENT',  rcpt)
    ok('Email config saved to backend/.env')

# ── .env helper ───────────────────────────────────────────────────────────────
def set_env_value(key, value):
    env_path = BACKEND / '.env'
    lines = env_path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith(key + '=') or line.startswith(f'# {key}='):
            lines[i] = f'{key}={value}'
            env_path.write_text('\n'.join(lines) + '\n')
            return
    lines.append(f'{key}={value}')
    env_path.write_text('\n'.join(lines) + '\n')

# ── Summary ───────────────────────────────────────────────────────────────────
def finish():
    w = 60
    print()
    print(green('═' * w))
    print(green('  ✓ Setup complete!'))
    print(green('═' * w))
    print()
    print(bold('  Starting backend API...'))
    _start_backend_api()
    print()
    print(bold('  Starting frontend dev server...'))
    _, frontend_port = _start_frontend_dev()
    print()
    print(bold('  Open the dashboard:'))
    print(cyan(f'    http://localhost:{frontend_port}'))
    print()
    print(bold('  API docs:'))
    print(cyan(  '    http://localhost:8000/docs'))
    print()

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    w = 60
    print()
    print(bold(cyan('╔' + '═' * (w - 2) + '╗')))
    print(bold(cyan('║')) + bold(' SOC Monitoring Platform — Automated Setup'.center(w - 2)) + bold(cyan('║')))
    print(bold(cyan('╚' + '═' * (w - 2) + '╝')))
    print(dim(f'  Project root: {ROOT}'))

    if not (BACKEND / 'requirements.txt').exists():
        err(f'requirements.txt not found in {BACKEND} — are you in the project root?')
    if not (FRONTEND / 'package.json').exists():
        err(f'package.json not found in {FRONTEND} — are you in the project root?')

    step_system_tools()
    step_backend()
    step_frontend()
    step_suricata()
    step_geoip()
    step_email()
    finish()
