# Weltgenerator – Etappe 4: Gelände, Biome, Marker, Ressourcen, Wege

Insel 2 × 2 bis 16 × 16 km. Generieren, mit Pinseln formen, nach Godot (Terrain3D) exportieren.

## 1. Editor starten
`weltgenerator.html` per Doppelklick öffnen (Chrome, Edge oder Firefox). Läuft komplett offline, keine Installation.

### Generator
| Regler | Wirkung |
|---|---|
| **Weltgröße** | 2–16,4 km Seitenlänge (gerundet auf 512 m, über 8 km auf 1024 m; z. B. 8 km = 8192 m, 16,4 km = 16384 m). Bis 8 km ist das Raster 4 m, darüber 8 m (Raster höchstens 2048², damit alles flott bleibt). Wirkt beim nächsten „Neu generieren“. Größere Welt = mehr Gebirgszüge, Hügel und Täler (nicht nur größer gezogen). Achtung: Marker, Ressourcen und Wege werden beim Größenwechsel entfernt. |
| Seed / 🎲 | andere Insel |
| Inselgröße | Anteil der Karte, der Land ist |
| Küste zerklüftet | Buchten und Halbinseln |
| Berghöhe | Höhe der höchsten Gipfel (m) |
| Gebirgsanteil | wie viel der Insel Gebirge ist |
| Hügel | Höhe der Hügel im Flachland (m) |
| Erosion | Wassererosion: gräbt Täler und Rinnen (mehr = natürlicher, dauert länger) |
| Meerestiefe | Tiefe vor der Küste (m) |

### Pinsel (Tasten 1–9)
| | |
|---|---|
| **Anheben / Absenken** | Gelände hoch/runter |
| **Glätten** | Kanten und Rauschen weich machen |
| **Ebnen** | auf die Höhe einebnen, auf die du zuerst klickst (gut für Städte, Felder) |
| **Gebirge** | baut Bergkämme mit Graten statt runder Kuppen |
| **Tal** | gräbt ein weiches Tal (U-Form) |
| **Hügel** | unregelmäßige kleine Erhebungen |
| **Meer / Land** | Küstenlinie verschieben, Buchten oder Landbrücken malen |

Linke Maus = malen · rechte Maus oder Leertaste+Ziehen = verschieben · Mausrad = Zoom · `[` `]` = Pinselgröße · Strg+Z / Strg+Y.

**Tipp:** Nach dem Malen von Bergen einmal *Erosion anwenden* – das macht gemalte Formen natürlich.
*Flussbetten einschneiden* gräbt die blau angezeigten Flüsse 1–4 m tief ein (für Wasser in Godot später).
Besser ist *Landschaft überarbeiten* (Abschnitt Regionen): wenige Flüsse in Tälern; danach zeigt die Karte genau diese Flussläufe.

Die Karte zeigt Höhenlinien alle 10 m (dicker alle 50 m), damit auch kleine Höhenunterschiede sichtbar sind.
Unten rechts im Bild steht beim Überfahren die genaue Höhe.

### Biome
Acht Biome: **Strand, Wiese, Laubwald, Nadelwald, Sumpf, Steppe, Fels, Schnee**.
Sie werden automatisch aus Höhe, Hangneigung und Feuchtigkeit berechnet (Nähe zu Flüssen und Meer) und
nach jeder Geländeänderung neu verteilt.

| Regler | Wirkung |
|---|---|
| Schneegrenze | ab dieser Höhe Schnee (auf flacheren Stellen), darüber steiler = Fels |
| Baumgrenze | darüber kein Wald mehr, nur Wiese/Fels |
| Nadelwald ab | ab dieser Höhe wird Wald zu Nadelwald (darunter gemischt) |
| Waldanteil | wie viel der Insel bewaldet ist |
| Feuchtigkeit | mehr Sumpf/Wald (+) oder mehr Steppe (−) |
| Fels ab Hangneigung | Hänge steiler als dieser Winkel werden Fels |

**Biom-Pinsel:** Biom anklicken und malen – gemalte Flächen haben Vorrang vor der Automatik und bleiben
auch erhalten, wenn du das Gelände änderst. **Automatisch** radiert gemalte Biome wieder weg.
Ansicht umschaltbar: *Biome* oder *Höhenfarben*. Beim Überfahren zeigt die Infozeile das Biom („gemalt“ = von Hand).

### Marker
Werkzeuge: **Auswählen**, **Stadt**, **Dorf**, **Dungeon**, **Mine**, **POI**, **Feld**.
Typ anklicken, dann auf die Karte klicken = Marker setzen. Marker anklicken = auswählen, ziehen = verschieben,
**Entf** = löschen. Unter den Marker-Einstellungen steht eine **Liste aller Marker** (nach Typ, mit Suche):
Zeile anklicken = auswählen und hinspringen, ✕ = löschen. Bei Feldern **Umschalt + Ziehen** = drehen. In der Seitenleiste: Name, Radius
(Städte/Dörfer: bebaute Fläche), bei Feldern Anbau (Weizen/Gemüse), Breite, Länge, Drehung.

**Felder & Minen vorschlagen**: legt rund um jede Stadt (5) und jedes Dorf (3) Felder auf flachem, festem Land an
und setzt bis zu 6 Minen an Felshängen. Vorschläge sind normale Marker – verschieben, ändern oder löschen.

### Regionen & Siedlungen
Abschnitt **Regionen & Siedlungen** (in dieser Reihenfolge benutzen):
| Knopf | Wirkung |
|---|---|
| **Nebeninsel formen** | formt eine kleine Insel draußen auf dem offenen Meer (650–1000 m vor der Küste, bei 16 km doppelt so weit, in zufälliger Richtung, mit Abstand zum Kartenrand) |
| **See formen** | sucht eine ebene Stelle im Landesinneren (fern von Küste, Zentralberg und anderen Seen), senkt eine unregelmäßige Mulde ab und füllt sie bis zum Überlauf mit Wasser. Seen sind auf der Karte blau, mit Tiefe schattiert. |
| **Zentralberg formen** | hebt die Inselmitte zu einem großen Berg an (Regler *Höhe Zentralberg*), mit Graten und Erosion |
| **Regionen berechnen** | Startgebiet im Süden (Regler *Startgebiet %*), Fraktionsregionen ringförmig um den Berg (Regler *Fraktionsregionen*), Zentralberg ab *Berg-Grenze*. Die Grenzen folgen Flüssen, Seen und steilen Hängen, die Flächen werden angeglichen. Namen nach Himmelsrichtung. |
| **Siedlungen vorschlagen** | je Region *Städte pro Region*, je Stadt *Dörfer je Stadt* in ihrer Nähe (Name z. B. „Nord – Dorf 2a“ gehört zu „Nord – Stadt 2“), Startdorf, Gipfel-POI und Dungeon-Eingang am Südhang des Bergs, ein Dungeon je Nebeninsel. Ersetzt Städte, Dörfer, Dungeons und POIs (Felder und Minen bleiben). |
| **Landschaft überarbeiten** | nach Regionen und Siedlungen, nach dem Vorbild New World (Haken einzeln abwählbar): Zuerst werden schmale Rinnen aufgefüllt (alte eingeschnittene Flussbetten, Erosionsrillen, schmale Meeresarme an der Küste). **Hochebenen** schieben das Gelände zu Stufen je Höhenlage zusammen (flache Ebenen mit Hängen dazwischen, am Zentralberg ausgeblendet). **Pässe**: auf den Regionsgrenzen entstehen Bergrücken, offen bleiben 1–3 Pässe je Grenze (der erste an der tiefsten Stelle), Flussdurchbrüche, Küste und Seen. **Seen**: einige neue Seen in flachen Mulden, durch die später Flüsse laufen. **Flüsse**: nur noch große Flüsse (Einzugsgebiet ab 0,6 km²) in eigenen Tälern, geschwungen, 11–24 m breit; der Wasserspiegel liegt überall unter dem Ufer. Küste, Zentralberg sowie Städte, Dörfer und Felder bleiben unverändert, alte Wege werden verworfen (sie passen nicht mehr zum Gelände). Rückgängig mit Strg+Z. Ein zweiter Durchgang auf derselben Karte fragt vorher nach. |

Alle Entfernungen sind für 8 km gewählt und wachsen bei größeren Welten mit.

### Varianten
**Varianten erzeugen** baut mit der eingestellten Weltgröße nacheinander komplette Karten (Gelände, Zentralberg, Nebeninsel,
1–2 Seen, Regionen, Siedlungen, danach *Landschaft überarbeiten*), jede mit eigenen Zufallswerten für Seed, Inselform, Küste, Gebirge und Hügel.
Die **Galerie** zeigt alle Karten mit Kennzahlen; ein Klick lädt eine Karte in den Editor (danach Wege, Ressourcen, Export wie gewohnt).
Die Varianten liegen nur im Speicher des Browsers – die gewählte Karte also mit *Projekt speichern* sichern.

Danach wie gewohnt *Felder & Minen vorschlagen*, *Wege generieren*, *Ressourcen verteilen*. Die Regionen werden im Projekt (`regionen.u8`)
und im Export (`regionen_<Raster>.u8`, Namen in `welt.json` unter `regionen`) gespeichert, Seen ebenso
(`seen.u8` / `seen_<Raster>.u8`, Liste mit Position, Wasserspiegel, Fläche und Tiefe in `welt.json` unter `seen`).
IDs: 0 Meer · 1 Startgebiet · 2 … Fraktionsregionen · 250 Zentralberg · 251 Nebeninseln.

### Ressourcen
**Ressourcen verteilen** (beliebig oft neu – z. B. nachdem du Marker gesetzt hast):
| | Wo | Details |
|---|---|---|
| Bäume | Nadelwald: Fichte (65 %) / Kiefer · Laubwald: Eiche (70 %) / Kiefer · Wiese: vereinzelt · Sumpf: lichte Kiefern | 62 % alt, 38 % jung, mit Lichtungen |
| Äste-Büsche | Waldränder, Wälder, Wiese | |
| Erze | Fels, steile Hänge, Hügel | Tier nach Höhe: die tiefsten 30 % Iron … höchsten 6 % Darksteel; kleine Brocken häufiger |
| Sammelpflanzen | Hanf in Gruppen auf Wiese/Steppe nahe Wasser · Beeren in Wiese/Laubwald · Kräuter in Wiese/Wald/Sumpf | Farben zufällig |

Rund um Städte, Dörfer und Felder (und etwas um Minen, Dungeons, POIs) bleibt alles frei, ebenso Flüsse und Meer.
Dichte-Regler je Art. Nach Änderungen an Karte/Markern zeigt der Editor „neu verteilen?“ an.

### Wege & Straßen
**Wege generieren** (beliebig oft neu, z. B. nachdem Marker fertig sind):
- **Straßen** (6 m) verbinden alle Städte und Dörfer: kürzestes Netz + zusätzliche Verbindungen, wo der Umweg sonst groß wäre.
- **Wege** (3 m) führen zu Minen, Dungeons und POIs und münden ins nächste Straßenstück.
- Die Route meidet Steigung, Sumpf, Fels und Felder und nutzt bereits gebaute Straßen und Brücken mit
  → Strecken laufen durch Täler und über Pässe, statt geradeaus über den Berg.
- **Brücken** (rot) über Flüsse und tiefe Senken. Furten durch Flüsse gibt es nicht.

| Regler | Wirkung |
|---|---|
| Straßen / Wege max. Steigung | darüber wird es teuer → Serpentinen oder Umweg |
| Brücken max. Länge | längste erlaubte Brücke |
| Zusätzliche Verbindungen | 0 = nur das Mindestnetz, 1 = viele Querverbindungen |

**Entfernen** löscht die Wege. Bäume/Ressourcen, die auf einer neuen Straße stehen, werden automatisch entfernt;
„Ressourcen verteilen“ hält Wege ebenfalls frei. Nach Änderungen an Gelände oder Markern erscheint „neu generieren?“.

### Speichern
- **Projekt speichern / laden**: deine Arbeitsdatei (`welt_projekt_*.zip`, ~4 MB). Damit machst du später weiter.
- **Export für Godot**: `welt_export.zip` mit
  - Auflösung wählbar: **1 m pro Pixel** oder **2 m pro Pixel**. Bei 8 km sind 1 m = 8192² (~540 MB Export, braucht viel RAM im Browser
    und in Godot) – empfohlen dort 2 m (4096², ~140 MB). Bis 4 km ist 1 m problemlos. Über 8 km gibt es 2 m oder 4 m pro Pixel.
  - `hoehe_<Auflösung>.r32` – Höhen in Metern (Gelände wird beim Export fein hochgerechnet,
    dazu kommen kleine Bodenwellen: Regler *Feindetail*; an Flüssen und Seen ohne Bodenwellen, damit das Wasser nicht schwebt)
  - `steuerung_4096.r32` – Biom-Steuerkarte im Terrain3D-Format (welche Bodentextur wo, mit weichen Übergängen)
  - `biome_1024.u8` – Biom je 4-m-Zelle (0–7), z. B. um Bäume/Ressourcen passend zu verteilen
  - `wege.json` – alle Strecken als 3D-Linien (Meter, y = Fahrbahnhöhe) mit Brückenabschnitten
  - Das Gelände unter Straßen und Wegen ist im Export **eingeebnet** (mit Böschung), die Weg-Textur ist in der Steuerkarte.
  - `marker.json` – alle Marker in Weltkoordinaten (Meter, Weltmitte = 0) mit Höhe
  - `ressourcen.json` – alle Bäume, Büsche, Erze, Pflanzen (nur wenn verteilt)
  - `farbe_1024.png` – Farbkarte, `uebersicht.png` – Kartenbild, `welt.json` – Infos

## 2. In Godot importieren
1. **Terrain3D installieren**: Godot → AssetLib → „Terrain3D“ (getestet mit 1.0.2, Skript läuft auch mit neueren Versionen) → installieren.
   Dann *Projekt → Projekteinstellungen → Plugins* → Terrain3D aktivieren, Godot neu starten.
2. Ordner `godot/assets/welt/` (im Repo) ins Projekt kopieren (z. B. `res://assets/welt/`).
3. `welt_export.zip` in einen Projektordner entpacken, z. B. `res://welt_daten/`.
4. `welt.tscn` in deine Spielszene ziehen, im Inspector `daten_ordner` auf den Ordner setzen,
   auf **„Welt importieren“** klicken und die Szene speichern (Strg+S).

Die Insel liegt zentriert um den Ursprung (x/z von −Größe/2 bis +Größe/2, bei 8 km also ±4096 m), Meeresspiegel = 0.
Der Import wählt Terrain3D-Regionsgröße und Vertex-Abstand automatisch passend zur Weltgröße. `welt.welt_groesse` liefert die Seitenlänge.
`welt.hoehe_bei(position)` liefert die Bodenhöhe an jeder Stelle (z. B. zum Platzieren von Spieler oder Ressourcen).

### Marker in Godot
Der Import legt unter `Welt/Marker/<Typ>/` für jeden Marker einen **Marker3D** an (Position = Boden).
Alle Werte stehen als Metadaten dran: `get_meta("name")`, `get_meta("radius")`, bei Feldern `art`, `breite`, `laenge`, `winkel`.
Außerdem in Gruppen: `welt_marker` und `marker_stadt`, `marker_dorf`, … → z. B. `get_tree().get_nodes_in_group("marker_dungeon")`.
Platzhalter (farbige Säule + Name, Feldfläche) lassen sich mit `marker_platzhalter` ausblenden.

### Wege in Godot
Der Import legt unter `Welt/Wege/` an:
- `Strassen/…`, `Wege/…`: je Strecke ein **Path3D** (Kurve entlang der Fahrbahn) – für NPC-Routen, Händlerwagen,
  Wegweiser usw. Metadaten `typ`, `breite`, Gruppe `welt_wege`.
- `Bruecken/…`: einfache **Holzbrücken** (Planken, Geländer, Pfeiler bis zum Boden) mit Kollision.
  Gemeinsam genutzte Brücken werden nur einmal gebaut. Gern später durch eigene Modelle ersetzen.
- Bodentextur 9 = **weg** (`texturen/weg_*.png`).

### Ressourcen in Godot
`welt_ressourcen.gd` (Klasse **WeltRessourcen**) als Kind unter `Welt` hängen, `ziel` = Spieler bzw. Kamera.
Er lädt die Ressourcen in 64-m-Kacheln nur im Umkreis (`radius`, Standard 220 m) und baut sie mit bis zu
`pro_frame` Objekten pro Frame auf – so ruckelt es nicht. Benötigt die Pakete aus dem Chat unter:
`res://assets/erz/`, `res://assets/baeume/`, `res://assets/sammeln/` (Pfade im Inspector änderbar).

Hinweise:
- Was abgebaut wurde, ist nach dem Wegladen einer Kachel wieder da (gespeicherter Abbau-Zustand folgt später).
- Außerhalb des Radius steht kein Baum → aus großer Höhe wirken Wälder leer. Für Fernsicht kommen später
  vereinfachte Wald-„Impostors“ dazu.

### Bodentexturen
Der Import richtet in Terrain3D automatisch **8 Bodentexturen** ein (Ordner `godot/assets/welt/texturen/`, selbst erzeugt,
1024², kachelbar, mit Höhen- und Normal-Map): Sand, Wiese, Laubboden, Nadelboden, Sumpf, Steppe, Fels, Schnee.
Die Reihenfolge entspricht den Biom-Nummern 0–7. Eigene Texturen: einfach die PNGs gleichen Namens ersetzen
(Format: `*_albedo_hoehe.png` = RGB Farbe + A Höhe, `*_normal_rauheit.png` = RGB Normale (OpenGL) + A Rauheit).
Kachelgrößen stehen oben in `welt_import.gd` (`BODEN`). `farbkarte_anzeigen` zeigt zum Vergleich die flache Editor-Farbe.

Hinweis: Mit dem *Compatibility*-Renderer wirken die Farben deutlich greller; mit **Forward+** (Standard) passen sie.

## Ordner (in diesem Repo)
```
weltgenerator/weltgenerator.html   der Editor (eine Datei, Doppelklick)
weltgenerator/src/                 Quellcode des Editors (kern, app, marker, gl, zip, index.html)
weltgenerator/build.py             baut weltgenerator.html aus src/ neu
weltgenerator/godot_texturen/      boden_texturen.py – erzeugt die 9 Bodentexturen
weltgenerator/vorschau/            Bilder aus den Tests
godot/assets/welt/                 Godot-Import (welt_import.gd, welt_ressourcen.gd, welt.tscn, texturen/, test/)
```
