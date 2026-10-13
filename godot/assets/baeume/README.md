# Bäume – Fichte, Kiefer, Eiche (Tier 1), jung + alt, mit Stumpf

Getestet mit **Godot 4.4.1** (Forward+).

## Installation
1. Ordner `baeume/` ins Godot-Projekt kopieren (z. B. `res://assets/baeume/`). Alle Pfade sind relativ.
2. Zum Ansehen: `test/testszene.tscn` öffnen, **F6**.
   **F:** alle Bäume fällen und Büsche ernten (wachsen nach 6 s nach) · **Pfeiltasten:** drehen · **Mausrad:** Zoom

## Benutzung
`baum.tscn` in die Welt ziehen, im Inspector einstellen:

| Feld | Bedeutung |
|---|---|
| `art` | Fichte, Kiefer, Eiche |
| `alter` | Jung → „Grünholz“, Alt → „Reifes Holz“ |
| `respawn_zeit` | Sekunden bis zum Nachwachsen (Standard 600) |
| `ertrag` | Holzmenge [jung, alt] – Platzhalter 3 / 8 |
| `variante` | 1–3 = feste Form, 0 = automatisch (abhängig von der Position) |
| `zufalls_variation` | zufällige Drehung + ±15 % Größe, abhängig von der Position |

```gdscript
var baum := raycast.get_collider().get_parent() as Baum
if baum:
    var menge := baum.faellen()     # 0, wenn schon gefällt
```
Signale: `gefaellt(holz: String, menge: int)` und `nachgewachsen`.
Kollision nur am Stamm (Zylinder), durch die Krone bleibt man nicht hängen.

## Äste-Büsche (~1 m)
`aeste_busch.tscn` in die Welt ziehen. Gibt nur Äste, hat **keine Kollision** (man läuft hindurch),
aber einen `Area3D`-Bereich, den der Spieler per Raycast/Area treffen kann.

| Feld | Bedeutung |
|---|---|
| `respawn_zeit` | Sekunden bis zum Nachwachsen (Standard 300) |
| `ertrag` | Anzahl Äste pro Ernte – Platzhalter 2 |
| `variante` | 1–3 = feste Form, 0 = automatisch |
| `zufalls_variation` | zufällige Drehung + Größe 0,8–1,2 |

```gdscript
var busch := area.get_parent() as AesteBusch   # z. B. aus area_entered / Raycast mit collide_with_areas
if busch:
    var aeste := busch.ernten()                   # 0, wenn schon geerntet
```
Signale: `geerntet(menge)` und `nachgewachsen`. Geernteter Zustand: kurze, abgeschnittene Triebe.
Modelle: `busch_1..3.glb` (~450–550 Dreiecke), `busch_geerntet.glb`.

## Größen (70 % von echten Bäumen)
| | Höhe | Stamm Ø | Krone breit | Krone ab | Dreiecke |
|---|---|---|---|---|---|
| Fichte jung | 5,6 m | 0,18 m | 2,1 m | 2,2 m | ~1.150 |
| Fichte alt | 12,6 m | 0,42 m | 4,2 m | 3,5 m | ~2.200 |
| Kiefer jung | 4,9 m | 0,18 m | 2,5 m | 2,2 m | ~1.050 |
| Kiefer alt | 11,2 m | 0,35 m | 4,9 m | 6,3 m | ~2.300 |
| Eiche jung | 4,5 m | 0,21 m | 2,2 m (oval) | 2,0 m | ~880 |
| Eiche alt | 9,8 m | 0,70 m | 6,0 m (oval) | 2,8 m | ~1.800 |

Je Art und Alter gibt es **3 Varianten** (z. B. `fichte_jung_1..3.glb`, `kiefer_alt_1..3.glb`): leicht schiefer Wuchs,
einseitig vollere Krone, Lücken und unterschiedlich lange Äste. Zusammen mit Drehung und Größe wiederholt sich kaum ein Baum.
Büsche ansehen: Testszene mit `-- --buesche`. Ansicht aller Baum-Varianten: Testszene mit `-- --varianten --art=kiefer` starten. Gemischter Wald (alle drei Arten): `-- --art=gemischt`.

**Kiefer:** Hauptäste sind echte Geometrie, Nadelbüschel sitzen als Karten an den Astenden (Schirmkrone).
Rinde unten graubraun-grob (`kiefer_rinde`), oben orange Spiegelrinde (`kiefer_rinde_oben`) mit unregelmäßigem Übergang.

**Eiche:** kurzer, dicker Stamm gabelt sich (alt) in 3–4 knorrige Hauptäste mit Nebenästen.
Laubbüschel liegen gleichmäßig auf einer ovalen Hülle plus innere Schicht; dazu ein Laub-Kern für Dichte.
Das Laub nutzt denselben Shader wie die Nadeln (Material-Slot heißt deshalb auch bei der Eiche `nadeln`).

## Aussehen anpassen
- `materialien/fichte_nadeln.tres`: Farbe, Wind (`wind_staerke`, `wind_tempo`), Durchleuchtung
- `materialien/fichte_rinde.tres`: Rinde (Textur + Normal-Map)
- `materialien/fichte_kern.tres`: dunkler Innenkegel, der die Krone dichter wirken lässt
- Texturen in `texturen/` sind selbst erzeugt und kachelbar.

## Neu erzeugen (optional)
Python 3.13 + `pip install bpy==5.2.2`, im Ordner `blender/`:
```
python texturen.py ../texturen
python fichte.py -- ../modelle
python kiefer.py -- ../modelle
python eiche.py -- ../modelle
python busch.py -- ../modelle
```
