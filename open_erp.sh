#!/bin/sh
# Launcher for macOS and Linux. On macOS you can also double-click
# open_erp.command in Finder.
set -u
cd -- "$(dirname "$0")"

PYTHON="./venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "ERP launcher error: virtualenv Python not found at $PWD/venv" >&2
  echo "Follow the setup steps in README.md first." >&2
  exit 1
fi

exec "$PYTHON" open_erp.py
