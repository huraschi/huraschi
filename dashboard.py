"""Aktivitaetslog und lokales Web-Dashboard fuer den Angelbot (nur Standardbibliothek)."""
import csv
import json
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = Path(__file__).with_name("dashboard.html")


class Activity:
    """Sammelt Ereignisse und Kennzahlen; threadsicher, schreibt optional eine CSV-Datei."""

    def __init__(self, log_file=None, keep=300, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self.started = clock()
        self.status = "Startet"
        self.counts = {"cast": 0, "catch": 0, "timeout": 0, "missing": 0}
        self.bite_waits = []
        self.events = deque(maxlen=keep)
        self.motion_values = deque(maxlen=240)
        self.limit = 0.0
        self.stop_requested = False
        self.log_file = log_file
        if log_file and not Path(log_file).exists():
            with open(log_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["zeit", "ereignis", "nachricht"])

    def log(self, kind, message, status=None, wait=None):
        """kind: start | cast | found | missing | catch | timeout | stop | info"""
        now = self.clock()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        with self.lock:
            if kind in self.counts:
                self.counts[kind] += 1
            if kind == "cast":
                self.motion_values.clear()
            if wait is not None:
                self.bite_waits.append(wait)
            if status:
                self.status = status
            self.events.append({"time": stamp, "kind": kind, "message": message})
        print(f"{stamp[11:]}  {message}")
        if self.log_file:
            with open(self.log_file, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([stamp, kind, message])

    def motion(self, value, limit):
        with self.lock:
            self.motion_values.append(round(value, 2))
            self.limit = round(limit, 2)

    def snapshot(self):
        with self.lock:
            runtime = self.clock() - self.started
            c = dict(self.counts)
            waits = self.bite_waits
            return {
                "status": self.status,
                "runtime": int(runtime),
                "casts": c["cast"],
                "catches": c["catch"],
                "timeouts": c["timeout"],
                "missing": c["missing"],
                "success": round(100 * c["catch"] / c["cast"], 1) if c["cast"] else 0.0,
                "per_hour": round(c["catch"] * 3600 / runtime, 1) if runtime > 30 else None,
                "avg_wait": round(sum(waits) / len(waits), 1) if waits else None,
                "motion": list(self.motion_values),
                "limit": self.limit,
                "events": list(self.events)[::-1],
            }


def serve(activity, port, host="127.0.0.1"):
    """Startet das Dashboard in einem Hintergrund-Thread und gibt den Server zurueck."""

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self._send(200, "text/html; charset=utf-8", PAGE.read_bytes())
            elif self.path == "/api/state":
                body = json.dumps(activity.snapshot()).encode()
                self._send(200, "application/json", body)
            else:
                self._send(404, "text/plain", b"not found")

        def do_POST(self):
            if self.path == "/api/stop":
                activity.stop_requested = True
                self._send(200, "application/json", b"{}")
            else:
                self._send(404, "text/plain", b"not found")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
