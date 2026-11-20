"""WoW-Angelbot auf Pixelbasis.

Ablauf pro Runde:
  1. Referenzbild der Suchregion aufnehmen
  2. Angel auswerfen (Tastendruck)
  3. Schwimmer finden: Stelle mit der groessten Bildaenderung gegenueber dem Referenzbild
  4. Kleines Fenster um den Schwimmer beobachten; bei ploetzlicher starker Bewegung = Biss
  5. Rechtsklick auf den Schwimmer, kurz warten, von vorn

Stoppen: F8 druecken, "Bot stoppen" im Dashboard oder Maus in die linke obere Ecke.
Dashboard: http://127.0.0.1:8765 (Kennzahlen, Bewegungskurve, Aktivitaetslog).
"""
import argparse
import statistics
import sys
import time
from collections import deque

import numpy as np

from dashboard import Activity, serve

CELL = 16  # Rastergroesse in Pixeln fuer die Schwimmersuche


# ---------------------------------------------------------------- Bildlogik

def find_bobber(before, after, threshold=40, min_pixels=30):
    """Sucht die Stelle mit der dichtesten Aenderung zwischen zwei Bildern.

    before/after: (H, W, 3) uint8. Gibt (x, y) relativ zum Bild zurueck oder None.
    """
    diff = np.abs(after.astype(np.int16) - before.astype(np.int16)).max(axis=2)
    mask = diff > threshold
    h, w = mask.shape
    gh, gw = h // CELL, w // CELL
    if gh < 3 or gw < 3:
        return None
    grid = mask[: gh * CELL, : gw * CELL].reshape(gh, CELL, gw, CELL).sum(axis=(1, 3))
    # 3x3-Nachbarschaft aufsummieren, damit ein Schwimmer auf einer Rastergrenze nicht verloren geht
    padded = np.pad(grid, 1)
    hood = sum(
        padded[dy : dy + gh, dx : dx + gw] for dy in range(3) for dx in range(3)
    )
    gy, gx = np.unravel_index(np.argmax(hood), hood.shape)
    if hood[gy, gx] < min_pixels:
        return None
    y0, y1 = max(0, (gy - 1) * CELL), min(h, (gy + 2) * CELL)
    x0, x1 = max(0, (gx - 1) * CELL), min(w, (gx + 2) * CELL)
    ys, xs = np.nonzero(mask[y0:y1, x0:x1])
    return int(x0 + xs.mean()), int(y0 + ys.mean())


def motion(prev, cur):
    """Mittlere Pixelaenderung zwischen zwei Bildern (0..255)."""
    return float(np.abs(cur.astype(np.int16) - prev.astype(np.int16)).mean())


class BiteDetector:
    """Erkennt einen Biss als Ausreisser der Bewegung gegenueber dem ruhigen Wippen."""

    def __init__(self, factor=3.0, min_motion=4.0, warmup=10, confirm=2, history=40):
        self.factor = factor
        self.min_motion = min_motion
        self.warmup = warmup
        self.confirm = confirm
        self.values = deque(maxlen=history)
        self.hits = 0
        self.last_limit = min_motion

    def update(self, value):
        if len(self.values) < self.warmup:
            self.values.append(value)
            return False
        self.last_limit = max(self.min_motion, self.factor * statistics.median(self.values))
        if value > self.last_limit:
            self.hits += 1  # Ausreisser nicht in die Ruhewerte aufnehmen
        else:
            self.hits = 0
            self.values.append(value)
        return self.hits >= self.confirm


# ---------------------------------------------------------------- Bot

def parse_region(text, screen):
    """'x1,y1,x2,y2' als Bruchteile (0..1) des Bildschirms -> mss-Region."""
    x1, y1, x2, y2 = (float(v) for v in text.split(","))
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError("Region muss 0 <= x1 < x2 <= 1 und 0 <= y1 < y2 <= 1 erfuellen")
    return {
        "left": screen["left"] + int(screen["width"] * x1),
        "top": screen["top"] + int(screen["height"] * y1),
        "width": int(screen["width"] * (x2 - x1)),
        "height": int(screen["height"] * (y2 - y1)),
    }


def main():
    p = argparse.ArgumentParser(description="WoW-Angelbot auf Pixelbasis")
    p.add_argument("--key", default="1", help="Taste, auf der Angeln liegt (Standard: 1)")
    p.add_argument("--region", default="0.25,0.10,0.75,0.55",
                   help="Suchregion als Bildschirmanteile x1,y1,x2,y2")
    p.add_argument("--monitor", type=int, default=1, help="Monitornummer (1 = Hauptmonitor)")
    p.add_argument("--cast-wait", type=float, default=2.0,
                   help="Sekunden nach dem Auswerfen, bis der Schwimmer liegt")
    p.add_argument("--timeout", type=float, default=22.0, help="Max. Wartezeit auf einen Biss")
    p.add_argument("--box", type=int, default=70, help="Kantenlaenge des Beobachtungsfensters")
    p.add_argument("--factor", type=float, default=3.0,
                   help="Biss, wenn Bewegung > Faktor x Ruhebewegung (kleiner = empfindlicher)")
    p.add_argument("--min-motion", type=float, default=4.0, help="Untergrenze fuer einen Biss")
    p.add_argument("--fps", type=float, default=20.0, help="Abtastrate beim Beobachten")
    p.add_argument("--loot-wait", type=float, default=1.5, help="Pause nach dem Einholen")
    p.add_argument("--start-delay", type=float, default=5.0,
                   help="Sekunden zum Wechseln ins Spiel")
    p.add_argument("--stop-key", default="f8", help="Taste zum Beenden")
    p.add_argument("--port", type=int, default=8765, help="Dashboard-Port (0 = aus)")
    p.add_argument("--log-file", default="fishbot_log.csv",
                   help="CSV-Datei fuer das Aktivitaetslog ('' = keine Datei)")
    p.add_argument("--debug", action="store_true",
                   help="Bewegungswerte ausgeben und Suchbild als debug_*.png speichern")
    args = p.parse_args()

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()  # Screenshot- und Mauskoordinaten angleichen

    import mss
    import mss.tools
    import pyautogui
    from pynput import keyboard

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.02

    activity = Activity(args.log_file or None)
    if args.port:
        serve(activity, args.port)
        print(f"Dashboard: http://127.0.0.1:{args.port}")

    stop_key = getattr(keyboard.Key, args.stop_key.lower(), None)

    def on_press(key):
        if key == stop_key or getattr(key, "char", None) == args.stop_key:
            activity.stop_requested = True
            return False

    keyboard.Listener(on_press=on_press, daemon=True).start()

    with mss.mss() as sct:
        region = parse_region(args.region, sct.monitors[args.monitor])

        def grab(reg):
            return np.asarray(sct.grab(reg))[:, :, :3]

        activity.log("start", f"Start in {args.start_delay:.0f}s - jetzt ins Spiel wechseln. "
                     f"Stopp mit {args.stop_key.upper()}. Suchregion: {region}",
                     status="Wartet auf Start")
        time.sleep(args.start_delay)

        casts = 0
        while not activity.stop_requested:
            # Maus aus der Suchregion nehmen, damit Cursor/Tooltip nicht stoeren
            pyautogui.moveTo(region["left"] + region["width"] // 2,
                             region["top"] + region["height"] + 40)
            time.sleep(0.3)
            before = grab(region)
            pyautogui.press(args.key)
            casts += 1
            activity.log("cast", f"Wurf {casts}", status="Wirft aus")
            time.sleep(args.cast_wait)
            after = grab(region)

            pos = find_bobber(before, after)
            if args.debug:
                shot = sct.grab(region)
                mss.tools.to_png(shot.rgb, shot.size, output=f"debug_{casts:03d}.png")
            if pos is None:
                activity.log("missing", "Schwimmer nicht gefunden - neuer Wurf")
                time.sleep(1.0)
                continue

            bx, by = region["left"] + pos[0], region["top"] + pos[1]
            half = args.box // 2
            box = {"left": bx - half, "top": by - half, "width": args.box, "height": args.box}
            activity.log("found", f"Schwimmer bei ({bx}, {by})", status="Wartet auf Biss")
            watch_start = time.time()

            detector = BiteDetector(args.factor, args.min_motion)
            prev = grab(box)
            deadline = time.time() + args.timeout
            bite = False
            while time.time() < deadline and not activity.stop_requested:
                time.sleep(1.0 / args.fps)
                cur = grab(box)
                value = motion(prev, cur)
                prev = cur
                bite = detector.update(value)
                activity.motion(value, detector.last_limit)
                if args.debug:
                    print(f"    Bewegung {value:6.2f}  Schwelle {detector.last_limit:6.2f}")
                if bite:
                    break

            if activity.stop_requested:
                break
            if bite:
                pyautogui.moveTo(bx, by)
                time.sleep(0.1)
                pyautogui.click(button="right")
                wait = time.time() - watch_start
                activity.log("catch", f"Biss nach {wait:.1f}s - eingeholt",
                             status="Holt ein", wait=wait)
                time.sleep(args.loot_wait)
            else:
                activity.log("timeout", "Kein Biss erkannt - neuer Wurf")

    done = activity.snapshot()
    activity.log("stop", f"Beendet. {done['catches']} Faenge bei {done['casts']} Wuerfen.",
                 status="Gestoppt")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Abgebrochen.")
