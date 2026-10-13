# Erzvorkommen – 6 Tiers × 5 Größen + abgebauter Zustand

Getestet mit **Godot 4.4.1** (Forward+). Sollte ab Godot 4.3 laufen.

## Installation
1. Den Ordner `erz/` irgendwo in dein Godot-Projekt kopieren, z. B. nach `res://assets/erz/`.
   Alle Pfade sind relativ, der Ort ist egal.
2. Godot öffnen. Die Modelle werden automatisch importiert, das dauert ein paar Sekunden.
3. Zum Ansehen `test/testszene.tscn` öffnen und mit **F6** starten.
   - **Leertaste:** alles abbauen (Respawn in der Testszene nach 5 s)
   - **Pfeiltasten:** Kamera drehen · **Mausrad:** Zoom

## Benutzung im Spiel
`erz_vorkommen.tscn` in die Welt ziehen und im Inspector einstellen:

| Feld | Bedeutung |
|---|---|
| `tier` | Iron, Palladium, Mithril, Glacialore, Sungold, Darksteel |
| `groesse` | 1 (klein) bis 5 (groß) |
| `respawn_zeit` | Sekunden, bis der Brocken wieder da ist (Standard 300) |
| `ertrag` | Erzmenge je Größe 1–5 (Platzhalter: 2, 3, 5, 7, 10) |

Vom Spieler aus abbauen:
```gdscript
# z. B. nach dem Abbau-Fortschrittsbalken:
var vorkommen := raycast.get_collider().get_parent() as ErzVorkommen
if vorkommen:
    var menge := vorkommen.abbauen()   # gibt 0 zurück, wenn schon abgebaut
```
Signale: `abgebaut(tier, menge)` und `nachgewachsen`.
Die Kollision (konvexe Hülle) wird automatisch erzeugt und ist im abgebauten Zustand aus, man läuft also über den Schutt.

## Aussehen anpassen
`materialien/erz_<tier>.tres` öffnen, unter *Shader Parameters* lassen sich Farben, Erzmenge,
Aderbreite und Leuchtstärke live ändern. `schutt_<tier>.tres` gilt für den abgebauten Zustand,
`kristall_<tier>.tres` für die Kristalle von Glacialore und Darksteel.

Der Shader (`erz.gdshader`) berechnet das Muster über die **Weltposition** (Triplanar).
Darum braucht er keine UVs, und die Körnung ist bei jeder Brockengröße gleich fein.
Nebeneffekt: Jeder Brocken sieht je nach Position in der Welt etwas anders aus.

**Wichtig für die leuchtenden Adern:** In deinem `WorldEnvironment` sollte **Glow** aktiv sein.
Mit dem *Compatibility*-Renderer funktioniert alles, wirkt aber flacher (kein SSAO).

## Inhalt
```
erz/
├── erz_vorkommen.gd / .tscn    Abbauen, Schutt, Respawn, Kollision
├── modelle/                    erz_groesse_1-5.glb, kristalle_groesse_1-5.glb, schutt.glb
├── materialien/                erz.gdshader, 6× erz_, 6× schutt_, 2× kristall_, Rausch-Texturen
├── test/                       testszene.tscn (alle 36 Kombinationen)
└── blender/                    Generator-Skripte + Vorschaubilder
```
Dreiecke: Brocken 2.500–7.000 (Godot erzeugt beim Import automatisch LOD-Stufen),
Kristalle 180–420, Schutt ~10.700.

## Modelle neu erzeugen (optional)
Die Skripte in `blender/` brauchen Python 3.13 und `pip install bpy==5.2.2`
(oder in Blender 5.2 über die Skript-Konsole ausführen):
```
python formen.py -- katalog.png 100 20                      # neue Formen zum Aussuchen
python export_godot.py -- ../modelle                        # Modelle exportieren
python godot_materialien.py ../materialien                  # Materialien aus tiers.py schreiben
```
Formen und Tiers sind in `tiers.py` definiert (`SIZES`, `TIERS`).
Achtung: `godot_materialien.py` überschreibt Änderungen, die du in Godot an den `.tres` gemacht hast.
