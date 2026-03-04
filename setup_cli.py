#!/usr/bin/env python3
"""
SOC Platform — Interactive CLI Setup
Run from the project root:  python3 setup_cli.py
"""

import getpass
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── All paths are absolute so subprocess never gets confused ──────────────────
ROOT    = Path(__file__).resolve().parent
BACKEND = ROOT / 'backend'
FRONTEND = ROOT / 'frontend'
PYTHON  = sys.executable           # same interpreter that is running this script

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

# ── Step 1: Python backend ────────────────────────────────────────────────────
def step_backend():
    header('Step 1 / 4 — Python Backend')

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
    header('Step 2 / 4 — React Frontend')

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
    header('Step 3 / 4 — GeoIP Database (optional)')

    mmdb = BACKEND / 'GeoLite2-City.mmdb'
    if mmdb.exists():
        ok(f'GeoLite2-City.mmdb already present')
        set_env_value('GEOIP_DB_PATH', str(mmdb))
        return

    print(dim('  Country lookups require the free MaxMind GeoLite2-City database.'))
    print(dim('  Sign up at https://www.maxmind.com/en/geolite2/signup to get a license key.'))
    print()

    if not ask_yn('Do you have a MaxMind license key?', default=False):
        warn('Skipping GeoIP — country lookups will show "Unknown"')
        warn('You can re-run this script or place GeoLite2-City.mmdb in backend/ later')
        return

    key = ask('MaxMind license key')
    if not key:
        warn('No key entered — skipping GeoIP')
        return

    url = (
        f'https://download.maxmind.com/app/geoip_download'
        f'?edition_id=GeoLite2-City&license_key={key}&suffix=tar.gz'
    )
    tgz = BACKEND / 'GeoLite2-City.tar.gz'

    info('Downloading GeoLite2-City.mmdb …')
    run(['wget', '-q', url, '-O', str(tgz)])

    info('Extracting …')
    run(['tar', '-xzf', str(tgz), '-C', str(BACKEND)])

    # Find and move the .mmdb
    matches = list(BACKEND.glob('GeoLite2-City_*/GeoLite2-City.mmdb'))
    if not matches:
        err('Could not find .mmdb after extraction — check license key and try again')
    matches[0].rename(mmdb)

    # Clean up
    for d in BACKEND.glob('GeoLite2-City_*/'):
        shutil.rmtree(d, ignore_errors=True)
    tgz.unlink(missing_ok=True)

    set_env_value('GEOIP_DB_PATH', str(mmdb))
    ok(f'GeoLite2-City.mmdb installed → {mmdb}')

import re

# ── Step 4: Suricata auto-config (optional) ───────────────────────────────────
def step_suricata():
    header('Step 4 / 5 — Suricata Network Interface (optional)')
    if not shutil.which('suricata'):
        warn('Suricata not found — skipping IDS auto-config. Install with: sudo apt install suricata')
        return
    # List interfaces (skip loopback)
    info('Detecting network interfaces …')
    result = subprocess.run(['ip', 'link'], capture_output=True, text=True)
    if result.returncode != 0:
        warn('Could not list interfaces (ip link failed)')
        return
    # Parse interface names
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
    # Offer to restart service
    if ask_yn('Restart Suricata service now?', default=True):
        run(['sudo', 'systemctl', 'restart', 'suricata'])
        ok('Suricata service restarted')
    else:
        warn('Suricata not restarted; run: sudo systemctl restart suricata')
def step_email():
    header('Step 4 / 4 — Email Alerts (optional)')
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
    print(bold('  Start the backend:'))
    print(cyan(  '    cd backend && source venv/bin/activate && python -m api.main'))
    print()
    print(bold('  Start the frontend (new terminal):'))
    print(cyan(  '    cd frontend && npm run dev'))
    print()
    print(bold('  Open the dashboard:'))
    print(cyan(  '    http://localhost:5173'))
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

    step_backend()
    step_frontend()
    step_suricata()
    step_geoip()
    step_email()
    finish()
