"""Example Flask app for the Pi captive portal.

Serves the local setup UI (pi-web/index.html) and exposes:

- GET  /api/scan   -> { "networks": [...] }
- POST /api/config -> { "status": "SUCCESS" } or { "status": "FAIL", "reason": "..." }

This is a minimal example; in production you would:

- Run this as root or via sudo wrapper so nmcli has permission.
- Integrate with your hostapd/dnsmasq setup.
- Possibly add a setup PIN or authentication.
"""

from flask import Flask, send_from_directory, jsonify, request
from wifi_helper import scan_wifi, apply_wifi

app = Flask(__name__, static_folder="../pi-web", static_url_path="")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/scan")
def api_scan():
    nets = scan_wifi()
    return jsonify({"networks": nets})


@app.route("/api/config", methods=["POST"])
def api_config():
    data = request.get_json(force=True, silent=True) or {}
    ssid = data.get("ssid", "")
    password = data.get("password", "")
    ok, msg = apply_wifi(ssid, password)
    if ok:
        return jsonify({"status": "SUCCESS", "message": msg})
    return jsonify({"status": "FAIL", "reason": msg})


if __name__ == "__main__":
    # For debugging only. In production, run under gunicorn/uwsgi, etc.
    app.run(host="0.0.0.0", port=80)
