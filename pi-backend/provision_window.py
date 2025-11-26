"""Provisioning window supervisor.

Starts BLE and AP services on boot, keeps them alive for 5 minutes,
then stops them. You can configure systemd units like:

  /etc/systemd/system/pi-ble.service
  /etc/systemd/system/pi-ap.service

to be started/stopped by this script.

Example systemd unit for this script:

  [Unit]
  Description=Pi WiFi provisioning window
  After=network-pre.target
  Wants=network-pre.target

  [Service]
  Type=simple
  ExecStart=/usr/bin/python3 /home/pi/pi-wifi-setup/pi-backend/provision_window.py
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target
"""

import subprocess
import time

WINDOW_SECONDS = 300  # 5 minutes
BLE_SERVICE = "pi-ble.service"
AP_SERVICE = "pi-ap.service"


def main():
    subprocess.run(["systemctl", "start", BLE_SERVICE])
    subprocess.run(["systemctl", "start", AP_SERVICE])

    start = time.time()
    while time.time() - start < WINDOW_SECONDS:
        time.sleep(5)

    subprocess.run(["systemctl", "stop", BLE_SERVICE])
    subprocess.run(["systemctl", "stop", AP_SERVICE])


if __name__ == "__main__":
    main()
