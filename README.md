# RPG – Spiel, Assets & Weltgenerator

Einzelspieler-RPG im Stil von New World in Godot 4 – mit abbaubaren Ressourcen (6 Tiers) und einem Editor für eine Insel-Spielwelt (2–8 km).
Die Modelle und Texturen sind per Skript erzeugt – die Skripte liegen jeweils bei.

## Das Spiel (`godot/`)

`godot/` ist ein komplettes Godot-Projekt (getestet mit Godot 4.7.2). Starten: `godot/project.godot` im Godot-Editor öffnen und F5 drücken.

- Third-Person-Kampf mit 12 Waffentypen (Nah- und Fernkampf), Skillbäumen und Waffenmeisterschaft
- 5 Sammelberufe, 11 Werkstätten, Ausrüstung mit Zufallswerten und Zusatzmaterialien
- Inventar, Tränke & Essen, Speichern mit Autosave
- Spielkonzept: [godot/KONZEPT.md](godot/KONZEPT.md)

Die Grafik im Spiel besteht noch aus Platzhaltern – die Assets unten werden als Nächstes eingebunden.

## Assets & Weltgenerator

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
