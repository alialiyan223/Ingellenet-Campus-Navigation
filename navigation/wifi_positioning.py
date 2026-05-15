"""
Wi-Fi Positioning Module
──────────────────────────────────────────────────────────────────────────────
Uses Wi-Fi RSSI fingerprinting (simulated) to estimate the user's current
location within the campus without GPS.

Real deployment would use platform-specific Wi-Fi scanning APIs
(e.g., netsh on Windows, iwlist on Linux, CoreWLAN on macOS).
"""

import math
import random
import logging
import platform
import subprocess
import re
import time
import threading
from typing import Optional
from database.db_manager import get_all_fingerprints

logger = logging.getLogger(__name__)


# ── RSSI Scanner ───────────────────────────────────────────────────────────────

class WifiScanner:
    """Platform-aware Wi-Fi scanner. Falls back to simulation on failure."""

    def __init__(self):
        self._system = platform.system()
        self._last_scan: list[dict] = []
        self._lock = threading.Lock()

    def scan(self) -> list[dict]:
        """Return a list of {bssid, ssid, rssi, frequency} dicts."""
        try:
            if self._system == "Windows":
                return self._scan_windows()
            elif self._system == "Linux":
                return self._scan_linux()
            else:
                return self._simulate_scan()
        except Exception as exc:
            logger.debug("Real Wi-Fi scan failed (%s) – using simulation.", exc)
            return self._simulate_scan()

    # ── Windows ────────────────────────────────────────────────────────────────
    def _scan_windows(self) -> list[dict]:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            encoding="utf-8", errors="ignore", timeout=10
        )
        networks = []
        current: dict = {}
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                if current:
                    networks.append(current)
                current = {"ssid": line.split(":", 1)[-1].strip()}
            elif "BSSID" in line:
                current["bssid"] = line.split(":", 1)[-1].strip()
            elif "Signal" in line:
                pct = int(re.search(r"\d+", line).group())
                current["rssi"] = self._pct_to_dbm(pct)
            elif "Channel" in line:
                ch = int(re.search(r"\d+", line).group())
                current["frequency"] = 5000 if ch > 14 else 2400
        if current:
            networks.append(current)
        return networks

    # ── Linux ──────────────────────────────────────────────────────────────────
    def _scan_linux(self) -> list[dict]:
        output = subprocess.check_output(
            ["iwlist", "scanning"], encoding="utf-8", errors="ignore", timeout=10
        )
        networks = []
        current: dict = {}
        for line in output.splitlines():
            line = line.strip()
            if "Cell" in line and "Address" in line:
                if current:
                    networks.append(current)
                bssid = line.split("Address:")[-1].strip()
                current = {"bssid": bssid}
            elif "ESSID:" in line:
                current["ssid"] = line.split('"')[1]
            elif "Signal level" in line:
                m = re.search(r"-\d+", line)
                if m:
                    current["rssi"] = float(m.group())
            elif "Frequency:" in line:
                m = re.search(r"[\d.]+", line)
                current["frequency"] = float(m.group()) * 1000 if m else 2400
        if current:
            networks.append(current)
        return networks

    # ── Simulation ─────────────────────────────────────────────────────────────
    def _simulate_scan(self) -> list[dict]:
        """Return deterministic pseudo-random RSSI values for demo purposes."""
        bssids = [
            ("AA:BB:CC:DD:EE:01", "CampusNet-A", 2412),
            ("AA:BB:CC:DD:EE:02", "CampusNet-B", 2437),
            ("AA:BB:CC:DD:EE:03", "CampusNet-C", 5180),
            ("AA:BB:CC:DD:EE:04", "CampusNet-D", 5200),
        ]
        return [
            {
                "bssid": bssid,
                "ssid": ssid,
                "rssi": random.uniform(-75, -45),
                "frequency": freq,
            }
            for bssid, ssid, freq in bssids
        ]

    @staticmethod
    def _pct_to_dbm(pct: int) -> float:
        """Convert Windows signal % to approximate dBm."""
        return (pct / 2) - 100


# ── Fingerprint Localiser ──────────────────────────────────────────────────────

class WifiLocaliser:
    """
    Matches a live Wi-Fi scan against stored fingerprints to estimate location.
    Uses Euclidean distance in RSSI-space (nearest-neighbour).
    """

    def __init__(self):
        self._scanner = WifiScanner()
        self._fingerprints: dict[str, dict[str, float]] = {}  # room → {bssid: rssi_avg}
        self._confidence: float = 0.0
        self._current_room: Optional[str] = None
        self._lock = threading.Lock()
        self._refresh_thread: Optional[threading.Thread] = None
        self._running = False
        self._load_fingerprints()

    def _load_fingerprints(self):
        """Load reference fingerprints from DB into memory."""
        data = get_all_fingerprints()
        fp: dict[str, dict[str, float]] = {}
        for row in data:
            room = row["room_code"]
            if room not in fp:
                fp[room] = {}
            fp[room][row["bssid"]] = row["rssi_avg"]
        with self._lock:
            self._fingerprints = fp
        logger.info("Loaded %d room fingerprints from DB", len(fp))

    def locate(self) -> dict:
        """Perform a scan and return estimated location."""
        scan = self._scanner.scan()
        if not scan:
            return {"room": None, "confidence": 0.0, "method": "wifi-fingerprint"}

        # Build observed RSSI vector
        observed: dict[str, float] = {ap["bssid"]: ap["rssi"] for ap in scan}

        best_room: Optional[str] = None
        best_dist = float("inf")

        for room, ref_vec in self._fingerprints.items():
            common = set(observed) & set(ref_vec)
            if not common:
                continue
            dist = math.sqrt(sum((observed[b] - ref_vec[b]) ** 2 for b in common))
            if dist < best_dist:
                best_dist = dist
                best_room = room

        # Confidence: inverse of distance, clamped 0-1
        confidence = max(0.0, min(1.0, 1.0 - best_dist / 50.0)) if best_dist < 50 else 0.0

        with self._lock:
            self._current_room = best_room
            self._confidence = round(confidence, 2)

        return {
            "room": best_room,
            "confidence": self._confidence,
            "method": "wifi-fingerprint",
            "scan_count": len(scan),
        }

    @property
    def current_room(self) -> Optional[str]:
        with self._lock:
            return self._current_room

    @property
    def confidence(self) -> float:
        with self._lock:
            return self._confidence

    def start_background_scan(self, interval: int = 15):
        """Continuously scan in a background thread."""
        self._running = True

        def _loop():
            while self._running:
                self.locate()
                time.sleep(interval)

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("Background Wi-Fi scan started (interval=%ds)", interval)

    def stop_background_scan(self):
        self._running = False
