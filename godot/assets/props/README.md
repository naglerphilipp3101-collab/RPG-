# Props und Haus-Baukasten

Alle Modelle entstehen per Blender-Skript, jedes **heil** und **kaputt** (`<name>.glb`, `<name>_kaputt.glb`).
Maße in Metern, Boden bei y = 0, Vorderseite zeigt in Godot nach +z (in Blender nach -y).

## Benutzen
`Prop.new()` bzw. ein Node3D mit `prop.gd` in die Szene setzen und im Inspector wählen:

| Feld | Bedeutung |
|---|---|
| `modell` | Name ohne `_kaputt`, z. B. `kiste`, `zelt`, `wand_fenster` |
| `kaputt` | kaputte Variante |
| `kollision` | statischer Körper (kleine Props: konvexe Hülle, sonst genaue Form) |
| `licht` | flackerndes Licht an Glut und Kerzen (Lagerfeuer, Laternen) |

Ansehen: `test/galerie.tscn` öffnen und mit **F6** starten (vorne heil, dahinter kaputt;
am Ende ein Fachwerk-Beispiel; Pfeiltasten drehen/fahren, Mausrad Zoom, N Tag/Nacht).

## Inhalt
**Lager und Dorf** (`blender/props.py`): kiste, fass, stuhl, hocker, tisch, bank, zaun (2 m, Pfosten bei x = -1),
palisade (2 m), zelt, lagerfeuer, karren, laterne (Ring zum Aufhängen 0,30 m über dem Boden), laternenpfahl,
saeule, mauer (3 m), bogen.

**Haus-Baukasten** (`blender/baukasten.py`), wird gerade neu aufgebaut. Regeln: 1-m-Raster (Stockwerkshöhe frei, Teile drehbar und überlappbar), alle Stoßflächen eben
und genau im Raster (damit Blueprints einrasten und beim späteren Backen verdeckte Flächen entfernt werden können).

| Teil | Maße / Anschluss |
|---|---|
| `wand`, `wand_2x1`, `wand_1x1` | massiv, 2 × 2 m, 2 × 1 m (gedreht 1 × 2 m) und 1 × 1 m, 0,10 m dick, Putz. Ursprung Mitte Unterkante |
| `balken_2m`, `balken_1m` | Fachwerk-Balken 0,14 × 0,16 m (steht je Seite 3 cm über die Wand). Ursprung Balkenmitte. Waagerecht innen an die Kanten (Mitte 0,07 m über Unter- bzw. unter Oberkante), senkrecht als Ständer auf den Stoß zweier Wände |
| `strebe_2m` | Schräge über eine ganze Wand, unten links nach oben rechts. Ursprung wie die Wand |

## Materialien
Die Modelle enthalten nur Material-Namen. `prop.gd` setzt dafür `materialien/<name>.tres` ein:
holz, holz_alt, holz_verkohlt, eisen, stoff, seil, stein, putz, schindeln, dielen, glut, glas, asche.
Die Texturen (`texturen/`, 1024², kachelbar) sind prozedural erzeugt (`blender/texturen.py`, numpy),
die UVs der Modelle sind schon in Metern gerechnet. Ein Material im Inspector ändern = alle Props ändern sich mit.
Neu anlegen: `Godot --headless --path godot -s res://assets/props/test/materialien_erzeugen.gd`.

## Modelle neu erzeugen (optional)
Python 3.13 mit `pip install bpy==5.2.2` (oder in Blender 5.2):
```
python blender/texturen.py                         # Texturen
python blender/props.py   [-- <ziel> --nur kiste,fass --vorschau <ordner>]
python blender/baukasten.py [-- <ziel> --nur wand --vorschau <ordner>]
```
Ohne Ziel landen die Modelle in `modelle/`. `--vorschau` rendert jedes Modell mit Cycles als JPG.
