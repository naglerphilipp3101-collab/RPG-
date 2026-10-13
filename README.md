# RPG – Assets & Weltgenerator

Godot-4-Projektbausteine für ein RPG im Stil von New World: abbaubare Ressourcen (6 Tiers) und ein Editor für eine Insel-Spielwelt (2–8 km).
Alles ist mit Godot 4.4.1 (Forward+) getestet. Die Modelle und Texturen sind per Skript erzeugt – die Skripte liegen jeweils bei.

## Inhalt
```
godot/assets/                in dein Godot-Projekt nach res://assets/ kopieren
├── erz/                     Erzvorkommen: 6 Tiers × 5 Größen, Kristalle, Schutt, Abbau + Respawn
├── baeume/                  Fichte, Kiefer, Eiche (jung/alt, je 3 Varianten), Stümpfe, Äste-Büsche
├── sammeln/                 Hanf, Beerensträucher (4 Farben), Kräuter (4 Farben)
└── welt/                    Import des Weltgenerators nach Terrain3D, Bodentexturen, Ressourcen-Streamer
weltgenerator/               Browser-Editor für die Insel (weltgenerator.html) + Quellcode
```
Jeder Ordner hat eine eigene README mit Bedienung und Details.

## Schnellstart
1. Godot 4.4+ Projekt anlegen, Plugin **Terrain3D** (AssetLib) installieren und aktivieren.
2. `godot/assets/` nach `res://assets/` kopieren.
3. `weltgenerator/weltgenerator.html` im Browser öffnen → Insel bauen → Marker, Ressourcen, Wege → **Export für Godot**.
4. Export nach `res://welt_daten/` entpacken, `assets/welt/welt.tscn` in die Szene ziehen, **Welt importieren**.
5. `WeltRessourcen` als Kind unter `Welt` hängen, `ziel` = Spieler → Bäume, Erze, Pflanzen erscheinen um den Spieler.

## Tiers
| Tier | Erz |
|---|---|
| 1 | Iron |
| 2 | Palladium |
| 3 | Mithril |
| 4 | Glacialore |
| 5 | Sungold |
| 6 | Darksteel |

## Modelle neu erzeugen
Die Python-Skripte in `*/blender/` und `weltgenerator/godot_texturen/` brauchen Python 3.13 + `pip install bpy==5.2.2 numpy pillow`.
