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
**Stopp:** `F8` oder Maus in die linke obere Bildschirmecke.

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
