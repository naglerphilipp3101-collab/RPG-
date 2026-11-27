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
  „Landschaft überarbeiten“ (`landschaftUeberarbeiten` in `kern.js`, Knopf in `regionen.js`): Hochebenen, Bergrücken mit Pässen auf den Regionsgrenzen,
  neue Seen, wenige Flüsse in Tälern (ab 0,6 km²). Flussläufe im Format `{v:2, punkte:[[x,y,spiegel,breite]]}` (Zellen, Breite in m), Flussflächen in `zustand.FM`
  (Projekt: `flussmaske.u8`). Der Export rechnet an Wasser bilinear und ohne Feindetail hoch. Godot: Seen als Flächen aus den Seezellen (+1 Zelle), Kies als Seeboden, Felder ohne Platzhalter-Platte. `FLUSS_SCHWELLE` (Biome/Feuchte) bleibt bewusst klein.

### Assets (`godot/assets/`)

- `erz|baeume|sammeln/`: abbaubare Ressourcen. Modelle per Blender-Python (`blender/*.py`, bpy 5.2.2), Materialien als .tres/.gdshader.
  Skripte: `erz_vorkommen.gd` (ErzVorkommen: tier 0–5, groesse 1–5), `baum.gd` (Baum: art Fichte/Kiefer/Eiche, alter jung/alt, variante),
  `aeste_busch.gd` (AesteBusch), `sammelpflanze.gd` (Sammelpflanze: art Hanf/Beeren/Kräuter, farbe, drop).
- `welt/`: Import der Weltgenerator-Exporte in Terrain3D (`welt_import.gd`), Marker, Ressourcen-Streamer (`welt_ressourcen.gd`).
  Terrain3D-Textur-IDs: 0 Sand, 1 Wiese, 2 Laubboden, 3 Nadelboden, 4 Sumpf, 5 Steppe, 6 Fels, 7 Schnee, 8 Kies (Flussbett).
  Der Import ordnet die Böden nach den Biom-Regeln neu zu, ersetzt alte Weg-Pixel (ID 8 in alten Exporten) und legt Kies unter die Flüsse.
- `charakter/`: Menschen auf MakeHuman-Basis (CC0, `LIZENZ_MAKEHUMAN.txt`). Daten `daten/mensch.json|bin` erzeugt `tools/charakter/mensch_daten.py <mpfb2> <makehuman> <godot> [<systemassets>]`
  (Quellen: MPFB2, MakeHuman-Repo, System-Asset-Pack; Auswahl liegt als `makehuman_auswahl.zip` in den Projektdateien). `mensch.gd` (Mensch: Formen, Skelett mit
  Godot-Humanoid-Namen in T-Pose für Mixamo-Retargeting, Haare/Brauen/Wimpern/Zähne, Hauttexturen, gemalte Bärte, Unterwäsche), `charakter_aussehen.gd` (Standard, Zufall,
  NPC-Liste `data/npc_aussehen.json`), Regler/Farben/Zufallsgrenzen in `data/charakter.json`. Erstellung: `scripts/charakter_erstellung.gd` (neues Spiel, Esc → „Aussehen ändern“).
  Gegner mit `"mensch"` in `enemies.json` nutzen ein gemeinsames Modell (`gegner_aussehen`). Test: `assets/charakter/test/erstellung.tscn -- --bild x.png [--zufall 7] [--gruppe Nase]`.
- `props/`: Props und Haus-Baukasten, je heil und kaputt (Blender `props/blender/props.py`, `baukasten.py`, Texturen prozedural `texturen.py`).
  `prop.gd` (Prop: modell, kaputt) setzt die Materialien aus `props/materialien/*.tres` ein; Galerie: `props/test/galerie.tscn`. Baukasten (26.10./12.11., Philipp): massive Wände 2×2, 2×1, 1×1 m (0,1 m dick, 1-m-Raster, Stockwerkshöhe frei), Balken 20×20 cm für 1/2 m mit je 10 cm Überstand (1,2/2,2 m lang, Ständer = gedrehter Balken) und Strebe als eigene Modelle; Vorrang bei Überlappung im Shader `props/materialien/balken.gdshader`: je waagerechter, desto höher; Wände und Balken mittig auf den Rasterlinien, Ursprung = Anfangspunkt auf einem Rasterpunkt, später Blueprints und „Blueprint backen“ (ein Mesh, verdeckte Flächen raus). Dazu (12.11.) Tür-/Fensterwände, Giebel, Böden, Dach 45° (Traufe, First, Ortgang, Giebelzier, Kehle und Grat für Eckhäuser/Walmdächer), Treppen. **Gebäude-Baukasten** im Browser: `props/baukasten_editor/gebaeude_baukasten.html` (Quelle `editor.js` + `vorlage.html`, Build `bauen.py`), speichert Gebäude als `data/gebaeude/*.json`, Godot lädt sie mit `props/gebaeude.gd` (Test `props/test/gebaeude_test.tscn`). Noch nicht in der Welt platziert (kommt mit dem Karten-Editor).
  **Vorratsbehälter** (26.11., `props/blender/behaelter.py`): vorratskiste, versorgungswagen, grubenlore, fischerkorb, schatzkiste_klein; `_kaputt` = geplündert (offen, leer). Konzept für Zusatzmaterialien und Fundquellen im Claude Doc „Zusatzmaterialien und Vorratsbehälter“. Schatzbehälter (große Truhe, Grab, Sarkophag) folgen.
  **Deko-Props** (26.11., `props/blender/deko.py`, nicht interagierbar): Stühle, Tische, Krug, Humpen, Kochtopf, Bücher, Wandfackel, Hängelampe, Kerzen, Kerzenständer, Grabstein, Brunnen, Trainingspuppe, Zielscheibe, Amboss, Waffen- und Rüstungsständer. Neue Materialien ton, stroh, leder, farbe_rot/weiss. Umgefallene kaputte Modelle mit `m.umfallen_start()` … `m.umfallen_ende(azimut)` (basis.py): kippt um die vorderste Bodenkante, bis es auf dem liegt, was zuerst den Boden berührt. Dazu **Taverne** (`props/blender/taverne.py`: Bett, Strohlager, Truhe, Schrank, Regal mit Geschirr, Gedeck, Flaschen, Feuerstelle mit Kesselgalgen, Teppich, Zapffass) und **Friedhof** (`props/blender/friedhof.py`: Gruft, Holzkreuz, Grabkreuz mit Erdhügel (kaputt = Loch, als wäre jemand herausgekommen), Eisenzaun, umgestürzte Säule, Knochenhaufen, Schädel nur heil (`nur_heil = True`, Abstandsfeld, braucht scikit-image)); Materialien teppich (Textur = ganzes Bild), wolle_rot, knochen, glas_gruen, erde. **Küche** (`props/blender/kueche.py`: Brotlaib, Käselaib, Wurststange unter der Decke, Kräuterbündel an der Wand, Mehlsack, Gemüsekorb; kaputt = angefressen/geplündert/verdorben) mit einfarbigen Lebensmittel-Materialien. **Werkstätten** (`werkstaetten.py`: Schleifstein, Werkbank, Holzstapel mit Hackklotz, Webstuhl, Gerberrahmen, Wassertrog; Materialien haut, wasser). **Dorf** (`dorf.py`: Marktstand, Wegweiser, Pranger, Brennholzstapel, Heuballen, Schubkarre, Hühnerkäfig, Futtertrog). **Militär** (`militaer.py`: 6 Fraktionsbanner `banner_<farbe>`, Spanische Reiter, Pfeilbündel, Rüstungsstapel, Feldbett, Kartentisch). **Mine/Strand** (`mine_strand.py`: Stützbalken, Schienen, Erzhaufen, Spitzhacke im Fels, Ruderboot, Steg, Hummerkorb, Fischgestell). **Burg/Kirche** (`burg_kirche.py`: Thron, Wandteppich, Kronleuchter, Altar, Kirchenbank, Weihwasserbecken, Statue). Gemeinsame Helfer für diese Sets: `kueche.py` (`drehstueck`, `haufen`, `ellipsoid`). Statue aus dem Körper des Charakter-Editors (`statue_mensch.py`). Bruch-Helfer in basis.py (27.11.): gesplitterte Rundholz-Enden (`stab(..., bruch=)`), natürliche Risse (`flaeche(..., loch_uv=risse(...), fein=3)`), `ruhelage(bm)` für lose Bruchstücke. Philipps Regel: Kaputtes folgt der Physik (nichts schwebt, Ungestütztes sackt zu Boden), Bruchstellen nie glatt, Löcher nie eckig.
- `ruestung/`: Rüstungsmodelle (ab 12.11.), je Tier 3 Sätze leicht/mittel/schwer, 5 Slots kopf/brust/haende/beine/fuesse, nicht modular.
  Blender-Python (`blender/rgeo.py` Bausteine, `blender/iron.py` Iron-Grundsätze, `blender/waffensaetze.py` 15 Waffensätze je Tier
  (`iron_<waffen-id>_<slot>`, Klasse je Teil in `SAETZE`, z. B. Axt M/S/M/S/M), `blender/alle.py <ausgabe> [klassen | waffen [ids]]` baut,
  rendert und exportiert GLB; `blender/test_satz.py -- <waffe> [slots]` für schnelle Testbilder).
  Gewicht je Teil L 1/3/1/2/1, M 2/6/2/4/2, S 4/10/3/7/4 kg (Kopf/Brust/Hände/Beine/Füße); Gesamt ≤ 12 kg leicht, ≤ 22 kg mittel, sonst schwer.
  Geformt um den Körper aus `tools/ruestung/mensch_lesen.py` (liest `charakter/daten` wie das Spiel): Röhren um Rumpf/Arm/Bein-Achsen und Kugelfelder (Helm, Schulter),
  abgetastet per Strahl, konvex geglättet, nie unter der Haut. Materialnamen: platte, rand, niete, kette, leder, leder_dunkel, stoff, stoff_akzent, futter.
  Passform (`tools/ruestung/`): `anpassen.py` bindet jeden Rüstungspunkt an nahe Hautpunkte (Gauß über den Mehrabstand, linear in den Körperformen,
  dieselbe Regel rechnet die Rüstkammer in JS) und bestimmt die verdeckte Haut (5 Strahlen je Hautpunkt, Ohren ganz oder gar nicht).
  `passform_test.py <glb-ordner> [sätze]` prüft 102 Körper (Extreme aller Regler, Zufall): sichtbar äußerste Fläche je Hautpunkt gegen den Standard-Mann.
  `passform_bild.py` / `bilderbogen.py` rendern Sätze auf beliebigen Körpern, `vorschau_daten.py` schreibt Körperformen und verdeckte Haut für die Rüstkammer.
  `blender/nachbearbeitung.py` (in alle.py, `NACH=0` schaltet ab): Falten auf hängendem Stoff, Mittelgrat auf Blech, leichte Unruhe, nur nach außen.
  Tiers: `blender/tierstil.py` (Farben und Zierde je Tier, nach dem Verringern aufgesetzt), Bau mit `TIER=palladium python3 alle.py …` → `palladium_<satz>_<slot>`;
  Palladium hat eigene Formen je Satz in `blender/palladium.py` (`BAU[satz]`, von alle.py/test_satz.py bei `TIER=palladium` genutzt: Riffelharnisch, Burgonet, Morion,
  Cabasset, attischer Helm, Halskrausen, Pelerinen, gezackte Säume, Diademe); tierstil.py setzt danach die Zierde: Palladium gebläut (Königsblau) an Rändern und Ranken, Silberborten (Material `borte`) auf Stoff, Stoffe elfenbein/Weinrot/Königsblau. Passform-Werkzeuge lesen `TIER` ebenfalls.
  Noch nicht im Spiel (offen: Skelett-Bindung, Texturen nach Liste).
- `gegner/`: Gegnermodelle (ab 21.11., Rohfassung, noch nicht im Spiel). Gegnerliste als Claude Doc „Gegnerliste Morvane“.
  Menschen: `blender/kleidung.py` (Kleidung ohne Rüstung auf den Rüstungs-Bausteinen), `blender/gegner_typen.py` (23 Typen: Banditen mit zufälliger
  Iron-Mischung, Piraten, Wachen, Zombies, Vampire, Kultisten; Körper, Haut, Farben, Abnutzung), `blender/bauen.py -- <ausgabe> [typen]`
  (gebaut um den Standard-Mann, danach mit `passform.py`/`anpassen.py` auf den Körper des Typs gesetzt; `GLB=1` exportiert je Slot).
  Wachen sind ein generischer Typ, Name und Level kommen vom Ort. Tiere und Ungeheuer: `blender/tierform.py` (Abstandsfeld aus Kapseln/Ellipsoiden,
  Marching Cubes, Fell, Punktfarben, Skelett) und `blender/tiere.py -- <ausgabe> [art] [varianten]`: Wolf, Wildschwein, Bär, Berglöwe, Krokodil,
  Hirsch, Riesenkrabbe, Riesenspinne, Moorschrat, Kalistare (Splitterling, Krieger, Seher, Zahr-Koloss). Varianten teilen die Form, Größe als Skalierung.
  Braucht `pip install scipy scikit-image` und für Bilder `apt install libegl1` + `xvfb-run`.
- `animationen/`: Menschen-Animationen (ab 21.11.). Quelle Quaternius „Universal Animation Library“ 1+2 (CC0, `quaternius/UAL*_Standard.glb`), beim Import per
  `knochen_ue.tres` + Rest-Fixer auf das Godot-Humanoid-Profil umgerechnet (Einstellungen in den `.import`-Dateien). `mensch_animationen.gd` (MenschAnimationen:
  Bibliothek „mensch“, Spuren auf `Skelett:<Knochen>`), `scripts/spieler_animation.gd` (SpielerAnimation: Grundbewegung je Bild, einmalige Schläge/Rolle/Treffer/Tod,
  Waffen per BoneAttachment in die Hand). Genutzt von player.gd (`anim_figur`) und menschlichen Gegnern in enemy.gd (`figur`). Die T-Pose in mensch.gd richtet dafür
  Beine, Füße (`FUSS_RICHTUNG`) und Rumpf (`RUMPF_RICHTUNG`) nach der Quaternius-Puppe aus. Bilderbogen: `animationen/test/bogen.tscn -- --anims Idle,Walk [--waffe sword] [--bild x.png]`.
  Mixamo (ab 22.11.): FBX „Without Skin“ in `animationen/mixamo/<ordner>/` (schwert_schild, grossschwert, axt, bogen, gewehr, magie, bewegung, einzeln),
  `animationen/mixamo_umwandeln.gd` (`Godot --headless --path godot -s res://assets/animationen/mixamo_umwandeln.gd [-- --liste]`) rechnet sie auf das Mensch-Skelett um
  (Weltdrehung je Knochen + Richtungsangleich der Ruhe, Hüftwanderung raus, Meta `weg` m/s und `treffer` = schnellste rechte Hand) und schreibt `mixamo/<ordner>.res`.
  Alles unter `mixamo/` ist gitignored (nicht frei weiterzugeben); Claude legt die .res direkt in Philipps Ordner. Ohne sie fällt das Spiel auf Quaternius zurück.
  `SpielerAnimation.SAETZE` ordnet je Waffe Ruhe, Gehen/Rennen in 4 Richtungen, Block, Zielen, Schläge je Schlagart, Treffer, Tod, Fähigkeiten (buff/dash/leap/spin/zone) zu;
  `waffe_setzen(typ)` (player.gd bei Waffenwechsel, Gegner: Axt-Satz). Bogen hängt in der linken Hand (`BOGEN_HAND_*` in player.gd).
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
- Grafik im Spiel noch **Platzhalter aus Grundformen** (`mesh_util.gd`, `weapon_models.gd`). Spieler und menschliche Gegner sind animierte Menschen (siehe `animationen/`).

| Datei | Zweck |
|---|---|
| `scripts/main.gd` | Testwelt (flach): Teich, Handwerksdorf, Rohstoffe, Gegnerlager, Laden/Autosave |
| `scripts/player.gd` | Bewegung, Kamera, Nah-/Fernkampf, Fähigkeiten, Meisterschaft, Inventar, Berufe, Sammeln, Herstellen, Speichern |
| `scripts/enemy.gd` | Gegner-KI, Beute, Häuten, Blutung, Debuffs |
| `scripts/resource_node.gd` | Abbaubare Quellen des Spiels (LP pro Tier, Nachwachsen). Soll mit den Asset-Skripten zusammengeführt werden |
| `scripts/crafting_station.gd`, `projectile.gd`, `zone.gd`, `loot_bag.gd` | Werkstätten, Geschosse, Flächenangriffe, Beute |
| `scripts/ausruestung_ui.gd` | Ausrüstungsschrank im Dorf (Werkstatt `schrank`): ein Knopf je Waffe legt Stufe 1 + Schild + Lederrüstung an, Meisterschaft auf 20 (zum Ansehen der Animationen); Test `--autotest --schrank` |
| `scripts/hud.gd`, `inventory_ui.gd`, `crafting_ui.gd`, `skill_tree_ui.gd`, `charakter_ui.gd`, `kompass.gd`, `pause_menu.gd` | Oberfläche (Charakterfenster P, Kompass mit Aufspüren und Uhrzeit) |
| `scripts/fehler_melden.gd` | Taste B: Fehler mit Position, Blick, Biom, Bildschirmfoto und Kommentar nach `%APPDATA%\Godot\app_userdata\RPG\fehler\` (`fehler.json` + `fehler_NNN.jpg`); Start an einer Meldung mit `-- --fehler <nr>` |
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
- **Skillbäume wie New World** (22.10., Prototyp Schwert und Schild): 1 Punkt je Meisterschaftsstufe und Knoten, je Seite 4 Fähigkeiten (Sechsecke) mit 2 Verbesserungen (`upgrades`: `add`/`mul`/`set` auf die Fähigkeitswerte),
  6 kleine Passiven (`minors`), große Passive (ab 3 Punkten) und Ultimative (ab 7). Eine große Passive und eine Ultimative aktiv. Logik in `Game._build_weapon_trees`/`effective_skill`, Fenster `skill_tree_ui.gd`,
  Bilder `skill_icons.gd` (Datei unter `assets/icons/faehigkeiten/<id>.png|svg` hat Vorrang). Die übrigen 14 Waffen haben noch keine Verbesserungen/kleinen Passiven. Details in KONZEPT.md „Skillbäume (22.10.)“
- **Freie Kamera** (25.11., `scripts/freie_kamera.gd`): F4 an/aus, WASD/Leertaste/C fliegen, Umschalt schnell, Alt langsam, Mausrad Zoom, G Zeitlupe, V Standbild; die Figur bleibt stehen und greift weiter an. Test `--autotest --freecam`
- **Tasten:** Q/E/R Fähigkeiten, X Ultimative, F Interagieren, T/Mausrad Waffe wechseln, 1 Trank, 2 Essen (3/4 gesperrt bis M8-Level-Quests), K Skillbaum, P Charakter, B Fehler melden (nicht F9: die pausiert im Godot-Editor das laufende Spiel)

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
  entpackt nach `godot/welt_daten` (gitignored), Import: `godot/Welt importieren.bat` (Doppelklick) bzw. `Godot --headless --path godot -s res://tests/welt_importieren.gd`.
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
- ✅ (20.10.) **Steine:** 35 Modelle (`assets/erz/blender/steine.py` → `assets/erz/modelle/stein_<größe 1–5>_<variante 1–7>.glb`):
  Icosphere, jeder Punkt mit 9 Noise-Schichten verschoben (Grundform, Buckel, Bruchflächen, Schichtung, Großrisse, Kerben, Körnung, Haarrisse, Rauheit),
  7 Varianten rund/kantig/plattig/gespalten/hoch/liegend/zerklüftet, Höhlen-Abdunklung als Vertexfarbe. `felsbrocken.gd` (groesse, variante, art Stein/Feuerstein)
  mit `scripts/fels_triplanar.gdshader` (Fels-Scan aus `texturen_scan/`, sonst eigene Felstextur). natur.gd setzt sie nach `"steine"` in biome.json
  (dichte, Feuerstein-Anteil, Gewichte der Größen und Formen, Steinfelder per Rauschen, kleine Begleitsteine um große). Abbau: gathering.json felsbrocken_klein/–/_gross, feuerstein.
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
Godot --headless --path godot -- --autotest --fehlertest   # Fehlermeldung mit B (stellt vorhandene Meldungen wieder her)
Godot --path godot --write-movie <ordner>\f.png --fixed-fps 20 -- --autotest --showcase   # Bilder prüfen
```
Weitere Bild-Modi: `--ui`, `--village`, `--pause` (mit `--quit-after N`); Insel: `--island` (Blick aufs Startdorf), `--island --aerial`, `--island --flytest` (nur mit Fenster, headless bewegt sich der Spieler nicht). Im Testmodus ist das Speichern abgeschaltet (`Game.saving_enabled = false`).

Assets und Weltgenerator: Godot headless + Playwright (Chromium). Terrain3D-Nahansichten in Forward+ stürzen im Container ab → `--rendering-method gl_compatibility`.

## GDScript-Hinweise

- `:=` funktioniert nicht bei Variant-Werten (z. B. aus Dictionaries). Dort explizit typisieren: `var x: float = dict["a"]`.
- Methoden anderer Skripte über untypisierte Variablen aufrufen (`var enemy = node`).
- UI-Elemente, die sich während ihres eigenen Signals entfernen würden: `call_deferred` bzw. `CONNECT_DEFERRED`.
