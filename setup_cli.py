#!/usr/bin/env python3
"""Compatibility entrypoint for legacy command: python3 setup_cli.py."""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    runpy.run_path(str(ROOT / 'setup.py'), run_name='__main__')
