# Asset-Bibliothek (Poly Haven, CC0)

Texturen und 3D-Modelle von [Poly Haven](https://polyhaven.com), alle unter **CC0** (gemeinfrei, auch kommerziell frei nutzbar, keine Namensnennung nötig).
Die Liste steht in `bibliothek_laden.ps1`. Die Dateien selbst sind zu groß für GitHub und liegen nur lokal:
Doppelklick auf `godot/Assets laden.bat` lädt alles (2K) nach

- `texturen/<gruppe>/<id>/` – boden, fels, holz_rinde, mauer_boden_dach, metall
- `modelle/<gruppe>/<id>/` – waffen_werkzeuge, pflanzen, baeume, steine, licht_deko, behaelter, bauten

Noch nichts davon ist im Spiel eingebunden. Ältere Scans, die das Spiel schon nutzt, liegen weiter in `assets/scans/`.

## Von Hand geladen

- Texturen, die als Poly-Haven-Paket `<id>_4k.blend.zip` geladen wurden, wandelt `godot/tools/bibliothek/blend_zip_umwandeln.py`
  in dieselben 2K-Dateien um, die das Ladeskript erzeugt (EXR/PNG → JPG, gepackte ARM-Karte → AO/Rauheit/Metall).
- `modelle/dorf_baukasten_quaternius/`: „Medieval Village MegaKit“ (Standard-Version, kostenlos) von Quaternius, **CC0**.
  176 Baukasten-Teile (Wände, Dächer, Böden, Treppen, Türen, Fenster, Balkone, Props) als glTF mit Texturen.
  Quelle: https://quaternius.com – nicht per Skript ladbar. Noch nicht auf unser 1-m-Raster geprüft.
