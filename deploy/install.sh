#!/usr/bin/env bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: deploy/install.sh must be run as root." >&2
    echo "Run: sudo bash deploy/install.sh" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SOURCE="${SCRIPT_DIR}/configguardian.service"
SERVICE_TARGET="/etc/systemd/system/configguardian.service"

if [ ! -f "${SERVICE_SOURCE}" ]; then
    echo "Error: service file not found: ${SERVICE_SOURCE}" >&2
    exit 1
fi

cp "${SERVICE_SOURCE}" "${SERVICE_TARGET}"
systemctl daemon-reload
systemctl enable configguardian
systemctl start configguardian
systemctl status configguardian

echo
echo "ConfigGuardian systemd service installed and started successfully."
echo "View live logs with:"
echo "  journalctl -u configguardian -f"
