"""Shared Wi-Fi helper used by both BLE and HTTP provisioning on the Pi.

This file is an example; you may need to adjust paths / permissions
for your Raspberry Pi OS (NetworkManager vs wpa_supplicant).

Designed for NetworkManager (`nmcli`) which is the default on
Raspberry Pi OS Bookworm with desktop.
"""

import subprocess
from typing import List, Dict, Tuple


def scan_wifi() -> List[Dict[str, str]]:
    """Return a list of available Wi-Fi networks.

    Each entry is:
      { "s": ssid, "p": signal(0-100), "sec": "WPA2" / "OPEN" / ... }
    """
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
            text=True,
        )
    except Exception:
        return []

    networks = []
    seen = set()
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split(":")
        if len(parts) < 3:
            continue
        ssid, signal, security = parts[0], parts[1], parts[2]
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        try:
            p = int(signal)
        except ValueError:
            p = 0
        networks.append({"s": ssid, "p": p, "sec": security or "UNKNOWN"})
    return networks


def apply_wifi(ssid: str, password: str) -> Tuple[bool, str]:
    """Apply Wi-Fi credentials using nmcli.

    Returns (success, message).
    """
    if not ssid:
        return False, "SSID is empty"

    cmd = ["nmcli", "dev", "wifi", "connect", ssid]
    if password:
        cmd += ["password", password]

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return True, out.strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.strip() or str(e)
