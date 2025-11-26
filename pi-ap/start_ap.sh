#!/bin/bash
# start_ap.sh - bring up AP with SSID Pi-Setup-XXXX and run Flask captive portal.
#
# This is a reference script. You still need:
#   - hostapd
#   - dnsmasq
#   - static IP on wlan0 (e.g. 192.168.4.1)
#
# Adjust paths/usernames as needed.

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="${SCRIPT_DIR}/.."

# Derive last 4 hex digits of wlan0 MAC
MAC=$(cat /sys/class/net/wlan0/address | tr 'a-f' 'A-F')
LAST4=$(echo "$MAC" | awk -F: '{print $(NF-1)$(NF)}')
SSID="Pi-Setup-${LAST4}"

echo "Using SSID: ${SSID}"

# Generate hostapd config from template
HOSTAPD_CONF=/tmp/hostapd-pi-setup.conf
sed "s/__SSID__/${SSID}/" "${SCRIPT_DIR}/hostapd.conf.template" > "${HOSTAPD_CONF}"

# Use a dedicated dnsmasq config
DNSMASQ_CONF="${SCRIPT_DIR}/dnsmasq-pi-setup.conf"

# Stop any running services that conflict
systemctl stop hostapd || true
systemctl stop dnsmasq || true

# Bring wlan0 up with static IP (adjust to your network setup)
ip link set wlan0 down || true
ip addr flush dev wlan0 || true
ip link set wlan0 up
ip addr add 192.168.4.1/24 dev wlan0

# Start dnsmasq and hostapd manually pointing at our configs
dnsmasq --no-daemon --conf-file="${DNSMASQ_CONF}" &
DNSMASQ_PID=$!

hostapd "${HOSTAPD_CONF}" &
HOSTAPD_PID=$!

# Start Flask app (captive portal)
cd "${PROJECT_ROOT}/pi-backend"
# Use python directly for demo; in production use gunicorn/uwsgi.
python3 flask_app.py &
FLASK_PID=$!

# Wait until killed by systemd (pi-ap.service)
wait
