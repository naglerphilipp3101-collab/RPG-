# Projektkontext für Claude

RPG in Godot (GDScript), Vorbild New World. Kommunikation mit dem Nutzer auf **Deutsch**. Code-Bezeichner und Kommentare ebenfalls deutsch.
Der Nutzer hat kein Blender-Vorwissen. Das Spielkonzept steht in [godot/KONZEPT.md](godot/KONZEPT.md).
GitHub: https://github.com/naglerphilipp3101-collab/RPG- (öffentlich). Lokal: `C:\Users\Philipp\Desktop\RPG`.

## Aufbau des Repositorys

- `godot/` ist **das Godot-Projekt** (Godot 4.7.2 lokal; die Assets wurden mit 4.4.1 erstellt und laufen unter 4.7).
  - `scripts/`, `data/`, `scenes/`, `tests/`: das spielbare Spiel (Meilensteine M1–M4, siehe unten)
  - `assets/`: per Blender-Skript erzeugte Ressourcen und Welt-Bausteine (siehe nächster Abschnitt)
  - `tools/blender/`: Blender-Testskript (Kiefer, Kupferader, Schwert)
- `weltgenerator/`: Browser-Editor in Vanilla-JS ohne Abhängigkeiten. Nach Änderungen in `src/` immer `python3 build.py` ausführen (erzeugt `weltgenerator.html`).
  Raster 4 m/Zelle, Weltgröße 2–8 km (Vielfache von 512 m).

### Assets (`godot/assets/`)

- `erz|baeume|sammeln/`: abbaubare Ressourcen. Modelle per Blender-Python (`blender/*.py`, bpy 5.2.2), Materialien als .tres/.gdshader.
  Skripte: `erz_vorkommen.gd` (ErzVorkommen: tier 0–5, groesse 1–5), `baum.gd` (Baum: art Fichte/Kiefer/Eiche, alter jung/alt, variante),
  `aeste_busch.gd` (AesteBusch), `sammelpflanze.gd` (Sammelpflanze: art Hanf/Beeren/Kräuter, farbe, drop).
- `welt/`: Import der Weltgenerator-Exporte in Terrain3D (`welt_import.gd`), Marker, Wege/Brücken, Ressourcen-Streamer (`welt_ressourcen.gd`).
  Biom-/Textur-IDs: 0 Sand, 1 Wiese, 2 Laubboden, 3 Nadelboden, 4 Sumpf, 5 Steppe, 6 Fels, 7 Schnee, 8 Weg.
- Terrain3D ist ein Plugin aus der AssetLib und liegt **nicht** im Repository (muss unter `godot/addons/` installiert werden).
- **6 Erz-Tiers:** Iron, Palladium, Mithril, Glacialore, Sungold, Darksteel. Das Repository ist der neuere Stand und hat bei Abweichungen Vorrang (Nutzerentscheidung).

## Spiel (`godot/`): Stand

- Starten: `godot/Spiel starten.bat`, Editor: `godot/Editor oeffnen.bat` (F5 im Editor).
- Godot lokal: `C:\Users\Philipp\Desktop\Godot\Godot_v4.7.2-stable_win64.exe`. Blender: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`.
- Projekteinstellungen vom Nutzer: Name „RPG“, Jolt Physics, D3D12. Nicht ändern.
- Spielstand: `%APPDATA%\Godot\app_userdata\RPG\savegame.json`.
- **Alles wird per Code aufgebaut**, Szenen minimal (`scenes/main.tscn` enthält nur `main.gd`). **Datengetrieben** über `data/*.json`.
- Autoload `Game` (`scripts/game.gd`): Daten laden, Waffen-Gegenstände, Rezepte und Übungswaffen aus `weapons.json` erzeugen, Hilfsfunktionen, Tastenbelegung.
- Grafik im Spiel noch **Platzhalter aus Grundformen** (`mesh_util.gd`, `weapon_models.gd`). Die Assets aus `assets/` sind noch **nicht eingebunden**.

| Datei | Zweck |
|---|---|
| `scripts/main.gd` | Testwelt (flach): Teich, Handwerksdorf, Rohstoffe, Gegnerlager, Laden/Autosave |
| `scripts/player.gd` | Bewegung, Kamera, Nah-/Fernkampf, Fähigkeiten, Meisterschaft, Inventar, Berufe, Sammeln, Herstellen, Speichern |
| `scripts/enemy.gd` | Gegner-KI, Beute, Häuten, Blutung, Debuffs |
| `scripts/resource_node.gd` | Abbaubare Quellen des Spiels (LP pro Tier, Nachwachsen). Soll mit den Asset-Skripten zusammengeführt werden |
| `scripts/crafting_station.gd`, `projectile.gd`, `zone.gd`, `loot_bag.gd` | Werkstätten, Geschosse, Flächenangriffe, Beute |
| `scripts/hud.gd`, `inventory_ui.gd`, `crafting_ui.gd`, `skill_tree_ui.gd`, `pause_menu.gd` | Oberfläche |
| `scripts/save_game.gd` | Speichern/Laden (JSON) |
| `data/weapons.json` | 12 Waffentypen: Movesets, Fernkampf, Rezepte, Skillbäume (Templates strike/dash/leap/buff/evade/shot/zone) |
| `data/items|recipes|stations|gathering|professions|enemies.json` | Übrige Inhalte |

Kollisionsebenen im Spiel: 1 = Welt, 2 = Spieler, 4 = Gegner, 8 = Baumkronen (nur Kamera).

**Umgesetzt:**
- **M1** Kampfkern
- **M2** 5 Sammelberufe, Inventar, Beute
- **M3** 11 Werkstätten, Rezepte Tier 1–2, Ausrüstung mit Zufallswerten und Zusatzmaterialien, Tränke/Essen
- **Speichern** mit Autosave und Esc-Menü
- **M4** 12 Waffentypen plus Schild, Fernkampf, Skillbaum (K), Meisterschaft bis 20, 2 Waffenplätze (X), Übungswaffenständer

**Designregeln des Nutzers:**
- Rohstoffe haben LP pro Tier, Werkzeuge haben Abbaukraft. Abbauzeit = LP ÷ Abbaukraft.
- Klassenlos, die Waffe bestimmt die Rolle.

**Offen/aufgeschoben:**
- Balancing (Kampf zu leicht, erst nach echten Animationen)
- Neues Magie-Konzept
- Munition, Splitter-System, Gilde, Händler, Hauptlevel

**Nächster Schritt (M4.5 Grafik & Welt):**
- Assets aus `assets/` ins Spiel einbinden: Erze auf **6 Tiers** umstellen (Spiel hat bisher Kupfer/Eisen in Tier 1–2), Bäume und Pflanzen ersetzen.
- Terrain3D und Weltgenerator-Insel statt der flachen Testwelt.
- Spielfigur, NPCs und Gegner aus fertigen Paketen (Quaternius/KayKit + Mixamo). Downloads macht der Nutzer selbst.
- Danach M5 (Startgebiet, Tutorial, NPCs, Dialoge), M6 (Fraktionsregion, Händler), M7 (lebendige Welt).

## Testen

Spiel (aus `C:\Users\Philipp\Desktop\RPG`):
```
Godot --headless --path godot --import                     # nach neuen Dateien/Klassen
Godot --headless --path godot -- --autotest                # Kampf + Sammeln
Godot --headless --path godot -- --autotest --weapons      # alle Waffen und Fähigkeiten
Godot --headless --path godot -- --autotest --craft        # Herstellungskette
Godot --headless --path godot -- --autotest --savetest     # Speichern/Laden (eigene Testdatei)
Godot --path godot --write-movie <ordner>\f.png --fixed-fps 20 -- --autotest --showcase   # Bilder prüfen
```
Weitere Bild-Modi: `--ui`, `--village`, `--pause` (mit `--quit-after N`). Im Testmodus ist das Speichern abgeschaltet (`Game.saving_enabled = false`).

Assets und Weltgenerator: Godot headless + Playwright (Chromium). Terrain3D-Nahansichten in Forward+ stürzen im Container ab → `--rendering-method gl_compatibility`.

## GDScript-Hinweise

- `:=` funktioniert nicht bei Variant-Werten (z. B. aus Dictionaries). Dort explizit typisieren: `var x: float = dict["a"]`.
- Methoden anderer Skripte über untypisierte Variablen aufrufen (`var enemy = node`).
- UI-Elemente, die sich während ihres eigenen Signals entfernen würden: `call_deferred` bzw. `CONNECT_DEFERRED`.
