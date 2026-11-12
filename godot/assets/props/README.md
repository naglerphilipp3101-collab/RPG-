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

**Haus-Baukasten** (`blender/baukasten.py`). Regeln: 1-m-Raster (Stockwerkshöhe frei, Teile drehbar und überlappbar), alle Stoßflächen eben
und genau im Raster (damit Blueprints einrasten und beim späteren Backen verdeckte Flächen entfernt werden können).

Wände (10 cm) und Balken (20 × 20 cm) liegen **mittig auf den Rasterlinien**. Ursprung jedes Teils ist sein
Anfangspunkt auf einem Rasterpunkt, von dort läuft es 1 oder 2 m entlang x; gedreht wird um diesen Punkt.

| Teil | Maße / Anschluss |
|---|---|
| `wand`, `wand_2x1`, `wand_1x1` | massiv, 2 × 2 m, 2 × 1 m (gedreht 1 × 2 m) und 1 × 1 m, 0,10 m dick, Putz |
| `balken_2m`, `balken_1m` | 20 × 20 cm für 2 bzw. 1 m von Rasterpunkt zu Rasterpunkt, je Ende 10 cm Überstand (2,2 bzw. 1,2 m lang). Waagerecht auf eine Wandkante, hochkant (90° um z) als Ständer |
| `strebe_2m` | Schräge über eine 2 × 2-Wand, Mittellinie von (0/0) nach (2/2) |

| `wand_tuer` + `tuer` | 2 × 2-Wand mit Öffnung 0,9 × 1,9 m (x 0,55..1,45) und Zarge; Türblatt 0,8 × 1,85 m mit **demselben Ursprung**, Angel bei x = 0,6 |
| `wand_fenster`, `wand_fenster_2x1`, `wand_fenster_1x1` | Fensterwände 2 × 2 (Fenster 0,8 × 0,8), 2 × 1 (1,0 × 0,6), 1 × 1 (0,6 × 0,6), mit Rahmen, Kreuz, Glas, Fensterbank vorne. Rahmen stecken 1 cm in der Wand (keine Fläche auf der Laibung, kein Flackern) |
| `wand_dreieck`, `wand_dreieck_1x1` | Giebel: Dreieck (0\|0), (b\|0), (b\|b); die Schräge liegt auf der Diagonale wie `strebe_2m`. Andere Seite: um 180° drehen |
| `boden_2x2`, `boden_1x1` | Dielen, x 0..b und z 0..-b, Oberkante 0,1 m über dem Rasterpunkt (bündig auf den Balken) |
| `dach_2x2`, `dach_2x1`, `dach_1x2`, `dach_1x1` | Dach 45°, Breite × Lauf: Traufe am Rasterpunkt, steigt nach -z bis zum First. Liegt auf den Balkenkanten, Enden senkrecht im Raster: zwei Seiten (eine um 180° gedreht) treffen sich am First genau |
| `dach_traufe`, `dach_first` | 0,5 m Dachüberstand an der Traufe (gleicher Ursprung wie das Dach), Firstabdeckung (Ursprung am First-Rasterpunkt) |
| `dach_ortgang_l/_r`, `dach_ortgang_1m_l/_r`, `dach_ecke_l/_r` | Seitlicher Überstand 0,5 m mit Windbrett (Lauf 2 oder 1 m) links (x -0,5..0) bzw. rechts (x 0..0,5) am Giebel, Ecke zwischen Traufe und Seite; Ursprung wie das Dach. Auf der Gegenseite (Dach um 180° gedreht) tauschen links und rechts |
| `dach_zier_l/_r` | Giebelzier am First über dem Ortgang: zwei gekreuzte Zierbretter mit Kopf und Firstkappe für den Überstand. Ursprung am First-Rasterpunkt wie `dach_first`. Die Windbretter enden am First senkrecht, die Zier deckt den Stoß ab |
| `treppe_holz`, `treppe_stein` | 1 m breit, 2 m Lauf nach -z, 1 m hoch (5 Stufen à 20 × 40 cm), von Boden zu Boden; stapelbar |

Tiefe läuft bei Boden, Dach und Treppe immer nach **-z** (von der Vorderseite einer ungedrehten Wand weg).

Durch den Überstand reicht ein Balken an jedem Rasterpunkt genau so weit wie ein querliegender: Ecken sind ohne Stufe geschlossen.

**Vorrang bei Überlappung:** Wo sich Teile treffen, zeigt die Fläche nur das Teil mit dem höchsten Vorrang, die anderen verlieren dort ihre Fläche.
Je waagerechter, desto höher (waagerecht > schräg > senkrecht); bei gleicher Neigung geht entlang x vor entlang z, und zwei aneinanderstoßende
Balken wechseln sich fest nach der Rasterposition ab. Das macht das Holz-Material `materialien/balken.gdshader` aus der Lage des Teils,
von Hand ist nichts einzustellen. Was höher ist oder übersteht, sieht man ganz normal.

## Materialien
Die Modelle enthalten nur Material-Namen. `prop.gd` setzt dafür `materialien/<name>.tres` ein:
holz, holz_alt, holz_verkohlt (für Balken/Strebe als `*_balken`/`*_strebe` mit Vorrang), eisen, stoff, seil, stein, putz, schindeln, dielen, glut, glas, asche.
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

## Gebäude-Baukasten (Browser) und Gebäude in Godot
`baukasten_editor/gebaeude_baukasten.html` per Doppelklick im Browser öffnen (läuft ohne Internet, alles eingebettet).
Teile links wählen, ins Raster klicken, **R** drehen, **T** hochkant, **G** kippen, **Q/E** Höhe, **K** kaputt, **Alt+Klick** Teil übernehmen,
Werkzeuge Bearbeiten (Pfeile verschieben, Strg+D verdoppeln) und Löschen, Strg+Z/Y. Speichern im Browser, **Exportieren** gibt die JSON-Datei.
Dieselbe Seite liegt auch als claude.ai-Artifact; dort gespeicherte Gebäude kann Claude direkt ins Repository übernehmen.

Gebäude liegen in `godot/data/gebaeude/*.json` (Format `rpg_gebaeude`, Version 1: `teile` mit `modell`, `kaputt`, `pos`, `dreh` in Godot-Koordinaten,
Grad, Reihenfolge YXZ). In Godot: Node3D mit `gebaeude.gd` (Gebaeude), Feld `datei`; `alles_kaputt` zeigt die Ruine.
Ansehen: `test/gebaeude_test.tscn` (F6, `-- --datei res://data/gebaeude/x.json [--kaputt] [--screenshot]`).
Der Editor wird mit `python baukasten_editor/bauen.py` neu gebaut (nach neuen Modellen, Texturen oder Vorlagen; bettet three.js aus `lib/` ein, MIT-Lizenz).
