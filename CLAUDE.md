# Projektkontext für Claude

RPG in **Godot 4.4** (GDScript), Vorbild New World. Kommunikation mit dem Nutzer auf **Deutsch**. Code-Bezeichner und Kommentare ebenfalls deutsch.

- `godot/assets/erz|baeume|sammeln/`: abbaubare Ressourcen. Modelle per Blender-Python (`blender/*.py`, bpy 5.2.2) erzeugt, Materialien als .tres/.gdshader.
  Skripte: `erz_vorkommen.gd` (ErzVorkommen: tier 0–5, groesse 1–5), `baum.gd` (Baum: art Fichte/Kiefer/Eiche, alter jung/alt, variante),
  `aeste_busch.gd` (AesteBusch), `sammelpflanze.gd` (Sammelpflanze: art Hanf/Beeren/Kräuter, farbe, drop).
- `godot/assets/welt/`: Import der Weltgenerator-Exporte in Terrain3D (`welt_import.gd`), Marker, Wege/Brücken, Ressourcen-Streamer (`welt_ressourcen.gd`).
  Biom-/Textur-IDs: 0 Sand, 1 Wiese, 2 Laubboden, 3 Nadelboden, 4 Sumpf, 5 Steppe, 6 Fels, 7 Schnee, 8 Weg.
- `weltgenerator/`: Browser-Editor in Vanilla-JS ohne Abhängigkeiten. Nach Änderungen in `src/` immer `python3 build.py` ausführen (erzeugt `weltgenerator.html`).
  Raster 4 m/Zelle, Weltgröße 2–8 km (Vielfache von 512 m).
- Testen: Godot headless + Playwright (Chromium vorinstalliert); Terrain3D-Nahansichten in Forward+ stürzen im Container ab → `--rendering-method gl_compatibility`.
