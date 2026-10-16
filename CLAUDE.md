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
  Raster 4 m/Zelle (über 8 km: 8 m/Zelle, Raster bleibt ≤ 2048²), Weltgröße 2–16,4 km (Vielfache von 512 m, über 8 km von 1024 m).
  Ohne Python: der Build lässt sich in PowerShell nachbauen (Platzhalter `/*ZIP*/` … `/*APP*/` ersetzen, `/*KERN*/` zweimal, UTF-8 ohne BOM).
  Regionen, Seen und Varianten-Galerie in `src/regionen.js`; `WELT_API.variantenErzeugen(anzahl, startSaat)` baut komplette Karten.

### Assets (`godot/assets/`)

- `erz|baeume|sammeln/`: abbaubare Ressourcen. Modelle per Blender-Python (`blender/*.py`, bpy 5.2.2), Materialien als .tres/.gdshader.
  Skripte: `erz_vorkommen.gd` (ErzVorkommen: tier 0–5, groesse 1–5), `baum.gd` (Baum: art Fichte/Kiefer/Eiche, alter jung/alt, variante),
  `aeste_busch.gd` (AesteBusch), `sammelpflanze.gd` (Sammelpflanze: art Hanf/Beeren/Kräuter, farbe, drop).
- `welt/`: Import der Weltgenerator-Exporte in Terrain3D (`welt_import.gd`), Marker, Ressourcen-Streamer (`welt_ressourcen.gd`).
  Terrain3D-Textur-IDs: 0 Sand, 1 Wiese, 2 Laubboden, 3 Nadelboden, 4 Sumpf, 5 Steppe, 6 Fels, 7 Schnee, 8 Kies (Flussbett).
  Der Import ordnet die Böden nach den Biom-Regeln neu zu, ersetzt alte Weg-Pixel (ID 8 in alten Exporten) und legt Kies unter die Flüsse.
- `natur/`: Bodenobjekte und tote Bäume (Blender `natur/blender/natur_modelle.py` → `natur/modelle/`: totbaum, baumstamm, stock, treibholz, alge), nur Deko.
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
| `scripts/hud.gd`, `inventory_ui.gd`, `crafting_ui.gd`, `skill_tree_ui.gd`, `charakter_ui.gd`, `kompass.gd`, `pause_menu.gd` | Oberfläche (Charakterfenster P, Kompass mit Aufspüren und Uhrzeit) |
| `scripts/fehler_melden.gd` | F9: Fehler mit Position, Blick, Biom, Bildschirmfoto und Kommentar nach `%APPDATA%\Godot\app_userdata\RPG\fehler\` (`fehler.json` + `fehler_NNN.jpg`); Start an einer Meldung mit `-- --fehler <nr>` |
| `scripts/tageszeit.gd` | Tag/Nacht-Zyklus (Sonne, Mond, Himmel, Nebel; Uhrzeit in `Game.time_of_day`) |
| `scripts/save_game.gd` | Speichern/Laden (JSON) |
| `data/weapons.json` | 15 Waffen (10 + 5 Magie, `magic`/`element`): Movesets, Fernkampf, Rezepte, je 2 Seiten (`sides`: Passive mit `mechanic`/`params`, 4 Fähigkeiten, Ultimative; Templates strike/dash/leap/buff/evade/shot/zone) |
| `data/attributes.json` | 5 Attribute: Boni je Punkt, Schwellen 25–500 (`stats` → `player.bonus()`, `mechanics` → Sonderregeln, `ab` = noch ohne Wirkung) |
| `data/items|recipes|stations|gathering|professions|enemies.json` | Übrige Inhalte (`level` bei Rezepten/Quellen = benötigter Berufs-Skill 0–300) |

Kollisionsebenen im Spiel: 1 = Welt, 2 = Spieler, 4 = Gegner, 8 = Baumkronen (nur Kamera).

**Umgesetzt:**
- **M1** Kampfkern
- **M2** 5 Sammelberufe, Inventar, Beute
- **M3** 11 Werkstätten, Rezepte Tier 1–2, Ausrüstung mit Zufallswerten und Zusatzmaterialien, Tränke/Essen
- **Speichern** mit Autosave und Esc-Menü
- **M4** 12 Waffentypen plus Schild, Fernkampf, Skillbaum (K), Meisterschaft bis 20, 2 Waffenplätze (X), Übungswaffenständer
- **M5** (15.10.) Charakterlevel 1–100, 5 Attribute mit Schwellen (P), Tod −20 % EP, Waffen-EP nach Schadensanteil, Berufe Skill 0–300 mit 6 Tiers, Aufspüren (Kompass), Bonus-Ausbeute, Tag/Nacht. Details in KONZEPT.md unter „M5 umgesetzt“
- **M6** (15.10.) 10 Waffen mit je 2 Seiten (Passive, 4 Fähigkeiten, Ultimative), 20 Passiven-Mechaniken, Betäubung/Spott/Rüstungsbruch/Gift/Tarnung, Kopftreffer, Ultimative-Leiste, 3. Waffenplatz vorbereitet, Spielstand-Version 3 mit Umzug. Details in KONZEPT.md unter „M6 umgesetzt“
- **M7** (15.10.) 5 Magiewaffen (Feuer/Eis/Blitz/Leben/Leere, je 2 Seiten) mit Hitze, Frost, Ladung, Brennen, Beschwörungen (`scripts/beschwoerung.gd`), Heilung; Arkanes Sanktum stellt sie her. Details in KONZEPT.md unter „M7 umgesetzt“
- **Tasten:** Q/E/R Fähigkeiten, X Ultimative, F Interagieren, T/Mausrad Waffe wechseln, 1 Trank, 2 Essen (3/4 gesperrt bis M8-Level-Quests), K Skillbaum, P Charakter, F9 Fehler melden

**Designregeln des Nutzers:**
- Rohstoffe haben LP pro Tier, Werkzeuge haben Abbaukraft. Abbauzeit = LP ÷ Abbaukraft.
- Klassenlos, die Waffe bestimmt die Rolle.

**Offen/aufgeschoben:**
- Balancing (Kampf zu leicht, erst nach echten Animationen)
- Neues Magie-Konzept
- Munition, Splitter-System, Gilde, Händler, Hauptlevel

**Nächster Schritt (M4.5 Grafik & Welt):**
- Assets aus `assets/` ins Spiel einbinden: Erze auf **6 Tiers** umstellen (Spiel hat bisher Kupfer/Eisen in Tier 1–2), Bäume und Pflanzen ersetzen.
- ✅ Terrain3D-Insel ist eingebaut (Karte 5, Seed 737707, 16,4 km, 2 m/Pixel). Rohdaten: `Welt/welt_export.zip` (+ Projekt `welt_projekt_737707.zip`),
  entpackt nach `godot/welt_daten` (gitignored), Import: `Godot --headless --path godot -s res://tests/welt_importieren.gd`.
  Das Spiel setzt `vertex_spacing` aus `meter_pro_pixel`, startet am Marker „Startdorf“, legt Seen (`welt_seen`) und Brücken an,
  Spielstand-Welt-ID = `insel_<seed>`.
- ✅ Natur auf der ganzen Insel: `scripts/natur.gd` berechnet Bäume/Büsche/Sammelpflanzen je 64-m-Kachel aus Biomkarte, Gelände
  und Sperrflächen (Siedlungen, Felder, Wege, Seen, Startgebiet) – fester Zufall je Kachel, nichts wird gespeichert.
  Nah (110 m): Blender-Modelle aus `assets/` über `scripts/natur_quelle.gd` abbaubar (Werte in `gathering.json`: fichte_/kiefer_/eiche_jung|alt,
  aeste_busch, hanf, beeren, kraut, kraut_selten). Fern (950 m): einfache Bäume als MultiMesh, Shader `natur_fern.gdshader` blendet sie im Nahbereich aus.
  Erze bewusst nicht – die kommen später vor allem in die Minen. Test: `--island --natur` (mit Fenster: misst auch die FPS). Stand 15.10. siehe Biome unten.
- ✅ Grafik-Runde (13.10.2026): Wasser-Shader für Meer/Seen/Flüsse (`scripts/wasser.gd(shader)`, Flüsse aus `fluesse.json`),
  Felsbrocken abbaubar (`assets/erz/felsbrocken.gd`, Stein/Feuerstein), Bodenbewuchs Gras/Farn/Kraut/Blumen (`scripts/gras.gd`),
  Bodentexturen ohne Farbkarte, Wege sichtbar. Karte M zoombar, Wege auf Karte/Minimap, keine Wege am Zentralberg.
- Nutzer-Feedback zur Optik: soll realistisch wirken (Referenz: New World). Gras wirkt noch "Wii-Zelda", Felsen zu low-poly,
  Sand/Wiese/Waldboden-Texturen unausgereift → Vorschlag: CC0-Fotoscans (Poly Haven, ambientCG); Downloads nur mit Bestätigung.

**Nächste Schritte (vom Nutzer festgelegt, 13.10.2026):**
1. ✅ (15.10.) Spieldesign in `godot/KONZEPT.md`: Lore (Zahr, Kalistare, 6 Helden), Spielablauf, Fraktions-/Regionsansehen, Gold, Level 100 mit Attributsschwellen, Berufe, 15 Waffen mit je 2 Seiten (4 Fähigkeiten + Ultimative), Magie ohne Mana. Umsetzungsplan steht dort (M5 Charakterkern, M6 Waffen-Umbau, M7 Magie, M8 Startgebiet, M9 Fraktionen/Regionen, M10 Lebendige Welt, M11 Hauptquest/Raid).
2. ✅ (14.10.) Bäume: alle jungen/alten Bäume geben „Frischholz“ (green_wood, Menge nach Größe); neue uralte Bäume
   (`*_uralt_*.glb`, Blender `kahle_aeste()` in kiefer.py; ~6 % im Wald) geben „Gereiftes Holz“ (aged_wood).
   Felsmonolithen (`assets/erz/modelle/monolith_turm|gruppe_1-3.glb`, Blender `monolith.py`) stehen je 256-m-Kachel in natur.gd
   (`_monolithen()`), mit Kollision, nicht abbaubar. Tests: `--island --natur [--uralt|--monolith]`.
3. ✅ (14.10.) Realismus-Durchgang: Poly-Haven-Scans (CC0, `godot/assets/scans/scans_laden.ps1`, nicht im Repo) –
   Böden (`tests/scans_umwandeln.gd` → `assets/welt/texturen_scan/`), Kopfstein in Städten/Dörfern (beim Weltimport),
   abbaubare Moosfelsen (felsbrocken.gd), Fels-Triplanar auf Monolithen, Gras/Farn/Blumen-Scans mit Alpha (gras.gd).
   Bäume: Blender-Formen mit Scan-Rinde (baum.gd `_scan_rinde`) und aus Atlanten geschnittenen Zweigen
   (`tests/baum_scans_umwandeln.gd` → `assets/baeume/texturen_scan/`). Ohne Scans fällt alles auf die eigenen Texturen zurück.
- ✅ (15.10.) Karte aufgeräumt, **Biome neu** (Nutzerentscheidung): keine Straßen/Brücken mehr (Dörfer und Städte werden später gebaut),
  keine Steine/Felsbrocken/Monolithen (warten auf gute Modelle und eine Verteil-Logik). **6 Biome plus Stadt** in `data/biome.json`
  (gelesen von `scripts/biom_regeln.gd`): Wald (Variante laub/nadel), Wiese (inkl. alter Steppe), Fluss (Kies, nur Algen), Strand (Sand, Treibholz),
  Berg (Variante fels/schnee), Moor (Kräuter, Büsche, Beeren, tote Bäume, Pfützen), Stadt (nichts spawnt). Jedes Biom legt Boden, Bäume, Büsche,
  Sammelpflanzen, Bodenobjekte und Gras fest; Stein/Feuerstein/Erz stehen als `geplant` drin. Die Generator-Biome werden über `generator` abgebildet.
  Nach Änderungen an Böden muss der Weltimport neu laufen. Vorschau ohne Terrain3D: `tests/biom_vorschau.gd` (2D-Karten, Zählung) und
  `tests/biom_3d.tscn` (3D, `-- --biom moor [--luft] [--blick 120] [--objekt Totbaum]`, mit `--rendering-method gl_compatibility`; Sand/Kies wirken dort überbelichtet).
  Test im Spiel: `--island --natur [--biom wald|moor|…] [--uralt]`.
- Weiter offen: Gegner/Tiere (wartet auf Modelle + Animationen), feindliche Lager, Schwierigkeit, Erze in Minen, Siedlungen, Regionsgrenzen auf der Karte.
- Spielfigur, NPCs und Gegner aus fertigen Paketen (Quaternius/KayKit + Mixamo). Downloads macht der Nutzer selbst.
- Danach geht es nach dem Umsetzungsplan in KONZEPT.md weiter: ✅ M6 Waffen-Umbau, ✅ M7 Magie, als Nächstes M8 Startgebiet …

## Testen

Spiel (aus `C:\Users\Philipp\Desktop\RPG`):
```
Godot --headless --path godot --import                     # nach neuen Dateien/Klassen
Godot --headless --path godot -- --autotest                # Kampf + Sammeln
Godot --headless --path godot -- --autotest --weapons      # alle Waffen und Fähigkeiten
Godot --headless --path godot -- --autotest --craft        # Herstellungskette
Godot --headless --path godot -- --autotest --savetest     # Speichern/Laden (eigene Testdatei)
Godot --headless --path godot -- --autotest --character    # Level, Attribute, Waffen-EP, Berufe, Aufspüren, Tag/Nacht
Godot --headless --path godot -- --autotest --m6           # Waffenseiten, Passive, Ultimative, Effekte, Tasten, alte Spielstände
Godot --headless --path godot -- --autotest --m7           # Magie: Hitze, Frost, Ladung, Brennen, Beschwörungen, Heilung, Sanktum
Godot --headless --path godot -- --autotest --fehlertest   # F9-Fehlermeldung (stellt vorhandene Meldungen wieder her)
Godot --path godot --write-movie <ordner>\f.png --fixed-fps 20 -- --autotest --showcase   # Bilder prüfen
```
Weitere Bild-Modi: `--ui`, `--village`, `--pause` (mit `--quit-after N`); Insel: `--island` (Blick aufs Startdorf), `--island --aerial`, `--island --flytest` (nur mit Fenster, headless bewegt sich der Spieler nicht). Im Testmodus ist das Speichern abgeschaltet (`Game.saving_enabled = false`).

Assets und Weltgenerator: Godot headless + Playwright (Chromium). Terrain3D-Nahansichten in Forward+ stürzen im Container ab → `--rendering-method gl_compatibility`.

## GDScript-Hinweise

- `:=` funktioniert nicht bei Variant-Werten (z. B. aus Dictionaries). Dort explizit typisieren: `var x: float = dict["a"]`.
- Methoden anderer Skripte über untypisierte Variablen aufrufen (`var enemy = node`).
- UI-Elemente, die sich während ihres eigenen Signals entfernen würden: `call_deferred` bzw. `CONNECT_DEFERRED`.
