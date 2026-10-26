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
Pfeiltasten drehen/fahren, Mausrad Zoom, N Tag/Nacht).

## Inhalt
**Lager und Dorf** (`blender/props.py`): kiste, fass, stuhl, hocker, tisch, bank, zaun (2 m, Pfosten bei x = -1),
palisade (2 m), zelt, lagerfeuer, karren, laterne (Ring zum Aufhängen 0,30 m über dem Boden), laternenpfahl,
saeule, mauer (3 m), bogen.

**Haus-Baukasten** (`blender/baukasten.py`), 2-m-Raster, Geschoss 3 m:

| Teil | Maße / Anschluss |
|---|---|
| `wand`, `wand_fenster`, `wand_tuer` | Fachwerk 2 m breit, 3 m hoch, 0,2 m dick, Mitte auf der Rasterlinie. Eckständer halbiert: zwei Wände ergeben einen Ständer |
| `tuer` | Türblatt 1 × 2,1 m, Ursprung an der Angel; in `wand_tuer` bei x = -0,5 einsetzen, dreht um die Hochachse |
| `boden` | Dielen 2 × 2 m, Oberkante 0 (Erdgeschoss) |
| `decke` | Dielen auf Balken, Oberkante 0; auf 3 m setzen = Boden oben, Decke unten |
| `dach` | eine Dachfläche 45°, 2 m lang, von der Traufe (0/0) zum First (2 m weiter, 2 m höher), 0,4 m Überstand; auf die Wandkrone, Gegenseite um 180° gedreht |
| `dach_first` | Firstbalken und Abdeckung, am First |
| `giebel` | Giebeldreieck für 4 m Hausbreite, auf die Wandkrone |
| `treppe_holz` | 1 m breit, 4 m lang, 3 m hoch (ein Geschoss) |
| `treppe_stein` | 2 m breit, 2 m lang, 1 m hoch, stapelbar |

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
