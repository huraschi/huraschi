# WoW-Angelbot (pixelbasiert)

Wirft die Angel aus, findet den Schwimmer auf dem Bildschirm, erkennt den Biss an der
Bewegung des Schwimmers und klickt ihn zum Einholen an. Arbeitet nur mit Screenshots und
simulierten Eingaben - kein Zugriff auf den Spielspeicher.

> **Hinweis:** Automatisierung verstoesst gegen die Nutzungsbedingungen von Blizzard und
> kann zur Sperrung des Accounts fuehren. Nutzung auf eigenes Risiko.

## Installation

```
pip install -r requirements.txt
```

## Vorbereitung im Spiel

- Angeln auf eine Taste legen (Standard: `1`), Angel ausruesten
- **Automatisch pluendern** aktivieren
- Fenstermodus (randlos) verwenden, Kamera so stellen, dass der Schwimmer in der oberen
  Bildmitte landet - am besten ganz hineinzoomen (Ego-Perspektive)
- Ruhige Stelle waehlen: keine anderen Spieler, NPCs oder Effekte in der Suchregion

## Start

```
python fishbot.py --key 1
```

Nach dem Start bleiben 5 Sekunden, um ins Spiel zu wechseln.
**Stopp:** `F8`, „Bot stoppen“ im Dashboard oder Maus in die linke obere Bildschirmecke.

## Dashboard und Aktivitaetslog

Solange der Bot laeuft, zeigt <http://127.0.0.1:8765> im Browser (am besten auf einem
zweiten Monitor oder nach der Sitzung):

- Kennzahlen: Faenge, Wuerfe, Erfolgsquote, Faenge pro Stunde, mittlere Zeit bis zum Biss,
  Fehlwuerfe, Laufzeit
- Live-Kurve der Bewegung am Schwimmer samt Biss-Schwelle - hilfreich zum Einstellen von
  `--factor` und `--min-motion`
- Aktivitaetslog mit Zeitstempel (neueste Eintraege oben)

Jedes Ereignis wird zusaetzlich an `fishbot_log.csv` angehaengt (Zeit, Ereignis, Nachricht)
und bleibt so ueber mehrere Sitzungen erhalten. Anpassen mit `--port 9000` bzw.
`--log-file pfad.csv`; `--port 0` schaltet das Dashboard ab, `--log-file ""` die Datei.
Das Dashboard ist nur vom eigenen Rechner aus erreichbar.

## Wie es funktioniert

1. Referenzbild der Suchregion, dann Auswerfen.
2. Vergleich vorher/nachher: Die Stelle mit der dichtesten Aenderung ist der Schwimmer.
3. Ein kleines Fenster (70 px) um den Schwimmer wird ~20x pro Sekunde abgetastet. Das
   ruhige Wippen bildet den Grundwert; steigt die Bewegung in zwei Bildern hintereinander
   ueber `Faktor x Grundwert`, gilt das als Biss.
4. Rechtsklick auf den Schwimmer, kurze Pause, naechster Wurf.

## Feinabstimmung

| Problem | Loesung |
|---|---|
| Schwimmer wird nicht gefunden | `--cast-wait 2.5`, Suchregion anpassen (`--region x1,y1,x2,y2` als Bildschirmanteile) |
| Falsche Stelle erkannt | Region verkleinern, eigene Figur aus der Region halten |
| Biss wird verpasst | `--factor 2.5` oder `--min-motion 3` |
| Zu fruehes Einholen | `--factor 4` oder `--min-motion 6` |
| Klick trifft daneben | Windows-Skalierung pruefen, `--monitor` korrekt setzen |

Mit `--debug` werden die Bewegungswerte samt Schwelle ausgegeben und das Suchbild jedes
Wurfs als `debug_NNN.png` gespeichert. Alle Optionen: `python fishbot.py --help`.

## Tests

```
pytest
```
