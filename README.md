# Raspberry Pi Wi-Fi Provisioning

This project contains:

- A **GitHub Pages** web app for Android / Chrome that configures a Raspberry Pi's Wi-Fi via **Web Bluetooth**.
- A **Pi local captive portal** website used when the Pi is in AP mode (`Pi-Setup-XXXX`).
- A simple **Flask backend example** for the Pi that exposes `/api/scan` and `/api/config` for the captive portal.
- A **Pi BLE daemon** example that exposes the same Wi-Fi provisioning API over BLE.
- A small **provisioning window** supervisor that runs BLE + AP for 5 minutes after boot.
- A GitHub Actions workflow to deploy the GitHub Pages app.

Repo is intended for: `https://github.com/koenvanwijk/pi-wifi-setup`
and will publish to: `https://koenvanwijk.github.io/pi-wifi-setup/`.

> ⚠️ The Pi-side code here is a reference implementation. You will likely need
> to tweak paths, users, and some network settings (hostapd/dnsmasq) for your
> specific Raspberry Pi OS image.

Directory layout (Pi side parts):

- `pi-web/` — static HTML/JS served from the Pi in AP mode.
- `pi-backend/`
  - `wifi_helper.py` — wraps `nmcli` to scan/apply Wi-Fi.
  - `flask_app.py` — Flask HTTP API + serves `pi-web`.
  - `ble_daemon.py` — BLE GATT server exposing the same API.
  - `provision_window.py` — runs BLE + AP for 5 minutes after boot (systemd).
- `pi-ap/` — example hostapd/dnsmasq config and start script.

You are expected to:

1. Install dependencies on the Pi (`python3-flask`, `hostapd`, `dnsmasq`, BlueZ, etc.).
2. Copy the repo to the Pi.
3. Adapt `/etc` configs (hostapd/dnsmasq) to match your environment.
4. Install the systemd units (sample units included in the README below or in comments).
