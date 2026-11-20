import numpy as np

from fishbot import BiteDetector, find_bobber, motion


def water(rng, h=300, w=500):
    return rng.integers(60, 80, size=(h, w, 3), dtype=np.uint8)


def test_find_bobber_locates_new_object():
    rng = np.random.default_rng(0)
    before = water(rng)
    after = water(rng)  # Wasserrauschen aendert sich komplett
    after[150:170, 310:326] = (200, 40, 40)
    x, y = find_bobber(before, after)
    assert abs(x - 318) <= 3 and abs(y - 160) <= 3


def test_find_bobber_none_without_change():
    rng = np.random.default_rng(1)
    assert find_bobber(water(rng), water(rng)) is None


def test_bite_detector_ignores_bobbing_and_fires_on_splash():
    rng = np.random.default_rng(2)
    det = BiteDetector()
    for _ in range(200):
        assert not det.update(1.0 + rng.random())  # ruhiges Wippen
    assert not det.update(12.0)  # einzelner Ausreisser reicht nicht
    assert det.update(15.0)


def test_single_glitch_does_not_fire():
    det = BiteDetector()
    for v in [1.0] * 20 + [20.0] + [1.0] * 20:
        assert not det.update(v)


def test_motion():
    a = np.zeros((10, 10, 3), np.uint8)
    assert motion(a, a) == 0
    assert motion(a, a + 10) == 10


def test_activity_stats_and_csv(tmp_path):
    import csv
    import json
    import urllib.request

    from dashboard import Activity, serve

    now = [1000.0]
    path = tmp_path / "log.csv"
    act = Activity(str(path), clock=lambda: now[0])
    act.log("cast", "Wurf 1")
    act.motion(1.5, 4.0)
    act.log("catch", "Biss", status="Holt ein", wait=8.0)
    act.log("cast", "Wurf 2")
    act.log("timeout", "Kein Biss")
    now[0] += 3600
    snap = act.snapshot()
    assert (snap["casts"], snap["catches"], snap["timeouts"]) == (2, 1, 1)
    assert snap["success"] == 50.0 and snap["per_hour"] == 1.0 and snap["avg_wait"] == 8.0
    assert snap["motion"] == []  # neuer Wurf leert die Kurve
    assert snap["events"][0]["kind"] == "timeout"
    rows = list(csv.reader(open(path, encoding="utf-8")))
    assert len(rows) == 5 and rows[2][1] == "catch"

    server = serve(act, 0)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    assert json.load(urllib.request.urlopen(base + "/api/state"))["catches"] == 1
    assert b"Angelbot" in urllib.request.urlopen(base + "/").read()
    urllib.request.urlopen(urllib.request.Request(base + "/api/stop", method="POST"))
    assert act.stop_requested
    server.shutdown()
