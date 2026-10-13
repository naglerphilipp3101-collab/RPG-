# Sammelpflanzen – Hanf, Beeren, Kräuter

Getestet mit **Godot 4.4.1** (Forward+).

## Installation
1. Ordner `sammeln/` ins Godot-Projekt kopieren (z. B. `res://assets/sammeln/`). Alle Pfade sind relativ.
2. Zum Ansehen: `test/testszene.tscn` öffnen, **F6**.
   **E:** alles sammeln (wächst nach 6 s nach) · **Pfeiltasten:** drehen · **Mausrad:** Zoom
   Einzelansichten: `-- --beeren`, `-- --kraeuter`, `-- --varianten` (Hanf)

## Benutzung
`sammelpflanze.tscn` in die Welt ziehen, im Inspector einstellen:

| Feld | Bedeutung |
|---|---|
| `art` | Hanf, Beeren, Kräuter |
| `farbe` | Beeren: rot, blau, schwarz, gelb · Kräuter: weiß, gelb, lila, rot · Hanf: egal |
| `drop` | was der Spieler bekommt; leer = Standard („Hanf“, „Beeren (rot)“, „Kraut (weiß)“ …). **Für regionale Drops hier überschreiben**, z. B. roter Strauch im Wald = „Himbeere“, in den Bergen = „Preiselbeere“ |
| `ertrag` | Menge pro Ernte – Platzhalter 3 |
| `respawn_zeit` | Sekunden bis zum Nachwachsen (Standard 300) |
| `variante` | 1–3 = feste Form, 0 = automatisch (abhängig von der Position) |
| `zufalls_variation` | zufällige Drehung + Größe 0,85–1,15 |

```gdscript
var pflanze := area.get_parent() as Sammelpflanze   # Raycast mit collide_with_areas = true
if pflanze:
    var menge := pflanze.sammeln()                   # 0, wenn schon geerntet
```
Signale: `gesammelt(drop: String, menge: int)` und `nachgewachsen`.
Keine Kollision (man läuft hindurch), aber ein `Area3D` für die Interaktion.

## Hanf
- 1,3–1,8 m hoch, 3–5 Stängel, gefingerte Blätter paarweise an den Knoten, Seitentriebe, lila Blütenstand an der Spitze (hebt sich vom Grün ab)
- 3 Varianten (`hanf_1..3.glb`, ~260–400 Dreiecke), geernteter Zustand `hanf_geerntet.glb` (Stängelstummel)
- Materialien: `hanf_rinde.tres` (Stängel), `hanf_nadeln.tres` (Blätter), `hanf_bluete.tres` – Wind und Farbe einstellbar

## Beerenstrauch
- ~0,9 m, runder, dichter Strauch; Beeren sind echte kleine Kugeln in Trauben
- Strauch (`beeren_1..3.glb`, ~400 Dreiecke) und Beeren (`beeren_frucht_1..3.glb`, ~1.100–1.300 Dreiecke) sind getrennt:
  **beim Ernten verschwinden nur die Beeren**, der Strauch bleibt stehen
- Beerenfarbe = Material `beeren_<farbe>.tres` (glänzend, mit Randlicht)

## Kräuter
- ~0,4–0,6 m: Blattrosette am Boden + 3–6 Blütenstängel mit Dolden
- `kraut_1..3.glb` (~100 Dreiecke), geerntet `kraut_geerntet.glb` (kleine Rosette)
- Eine helle Blütentextur, eingefärbt über `kraut_bluete_<farbe>.tres` (Parameter `farbe`)

## Neue Farbe hinzufügen
Material kopieren (z. B. `beeren_rot.tres` → `beeren_orange.tres`), Farbe ändern, dann in `sammelpflanze.gd`
den Namen in `Farbe`, `FARB_DATEI`, `FARB_NAME` und in der passenden `erlaubt`-Liste ergänzen.

## Neu erzeugen (optional)
Python 3.13 + `pip install bpy==5.2.2`, im Ordner `blender/`:
```
python texturen_sammeln.py ../texturen
python hanf.py -- ../modelle
python beeren.py -- ../modelle
python kraut.py -- ../modelle
```
