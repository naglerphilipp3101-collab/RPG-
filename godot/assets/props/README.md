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
am Ende ein Fachwerk-Beispiel mit Außenecke; Pfeiltasten drehen/fahren, Mausrad Zoom, N Tag/Nacht).

## Inhalt
**Lager und Dorf** (`blender/props.py`): kiste, fass, stuhl, hocker, tisch, bank, zaun (2 m, Pfosten bei x = -1),
palisade (2 m), zelt, lagerfeuer, karren, laterne (Ring zum Aufhängen 0,30 m über dem Boden), laternenpfahl,
saeule, mauer (3 m), bogen.

**Haus-Baukasten** (`blender/baukasten.py`), wird gerade neu aufgebaut. Regeln: 1-m-Raster (Stockwerkshöhe frei, Teile drehbar und überlappbar), alle Stoßflächen eben
und genau im Raster (damit Blueprints einrasten und beim späteren Backen verdeckte Flächen entfernt werden können).

Wände (10 cm) und Balken (20 × 20 cm) liegen **mittig auf den Rasterlinien**. Ursprung jedes Teils ist sein
Anfangspunkt auf einem Rasterpunkt, von dort läuft es 1 oder 2 m entlang x; gedreht wird um diesen Punkt.

| Teil | Maße / Anschluss |
|---|---|
| `wand`, `wand_2x1`, `wand_1x1` | massiv, 2 × 2 m, 2 × 1 m (gedreht 1 × 2 m) und 1 × 1 m, 0,10 m dick, Putz |
| `balken_2m`, `balken_1m` | 20 × 20 cm, steht je Seite 5 cm über die Wand. Waagerecht auf eine Wandkante, hochkant (90° um z) als Ständer auf einen Rasterpunkt |
| `staender_2m`, `staender_1m` | senkrechter Balken (19,6 cm), steht auf dem Rasterpunkt und läuft nach oben |
| `strebe_2m` | Schräge über eine 2 × 2-Wand, Mittellinie von (0/0) nach (2/2) |
| `eckklotz` | Würfel 20,4 cm um einen Rasterpunkt: füllt Außenecken, deckt Kreuzungen ab |

**Vorrang bei Überlappung** (welche Textur sichtbar ist): Eckklotz > Balken (waagerecht, läuft durch) > Ständer > Strebe.
Jede Stufe ist je Seite 2 mm schmaler als die nächsthöhere, deshalb liegen nie zwei Flächen genau aufeinander und nichts flackert.
Darum senkrecht immer `staender_*` nehmen (nicht den Balken drehen) und auf jeden Knoten, an dem Balken zusammenkommen, einen `eckklotz` setzen.

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
