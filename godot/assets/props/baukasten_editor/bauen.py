"""Baut den Gebäude-Baukasten als eine einzige HTML-Datei (läuft ohne Internet, Doppelklick genügt).
Aufruf: python bauen.py [--artifact <datei>]
  - schreibt gebaeude_baukasten.html (vollständige Seite zum Öffnen im Browser)
  - mit --artifact zusätzlich die Fassung ohne <html>/<head> für ein claude.ai-Artifact
Bettet ein: three.js (lib/three_bundle.js), alle Modelle aus ../modelle (*.glb), die Texturen aus ../texturen
(verkleinert auf 512 px, braucht Pillow; ohne Pillow in Originalgröße) und die Vorlagen aus godot/data/gebaeude/*.json."""
import base64, io, json, os, sys

HIER = os.path.dirname(os.path.abspath(__file__))
PROPS = os.path.dirname(HIER)
GEBAEUDE = os.path.join(PROPS, "..", "..", "data", "gebaeude")
MATERIALIEN = ["holz", "holz_alt", "holz_verkohlt", "eisen", "stoff", "seil", "stein", "putz", "schindeln", "dielen", "glut"]


def lesen(pfad, modus="r"):
    with open(pfad, modus, **({} if "b" in modus else {"encoding": "utf-8"})) as f:
        return f.read()


def bild(pfad, groesse=512):
    try:
        from PIL import Image
        b = Image.open(pfad).convert("RGB")
        b = b.resize((groesse, groesse), Image.LANCZOS)
        puffer = io.BytesIO()
        b.save(puffer, "JPEG", quality=82)
        roh = puffer.getvalue()
    except ImportError:
        roh = lesen(pfad, "rb")
    return "data:image/jpeg;base64," + base64.b64encode(roh).decode()


def daten():
    modelle = {}
    ordner = os.path.join(PROPS, "modelle")
    for f in sorted(os.listdir(ordner)):
        if f.endswith(".glb"):
            modelle[f[:-4]] = base64.b64encode(lesen(os.path.join(ordner, f), "rb")).decode()
    texturen = {}
    for m in MATERIALIEN:
        farbe = os.path.join(PROPS, "texturen", m + "_farbe.jpg")
        if os.path.exists(farbe):
            texturen[m] = {"farbe": bild(farbe), "normal": bild(os.path.join(PROPS, "texturen", m + "_normal.jpg"))}
    vorlagen = []
    if os.path.isdir(GEBAEUDE):
        for f in sorted(os.listdir(GEBAEUDE)):
            if f.endswith(".json"):
                vorlagen.append(json.loads(lesen(os.path.join(GEBAEUDE, f))))
    return {"modelle": modelle, "texturen": texturen, "vorlagen": vorlagen}


def skript(text):
    return text.replace("</script", "<\\/script")


def main():
    vorlage = lesen(os.path.join(HIER, "vorlage.html"))
    inhalt = vorlage.replace("<script>/*THREE*/</script>", "<script>" + skript(lesen(os.path.join(HIER, "lib", "three_bundle.js"))) + "</script>", 1)
    inhalt = inhalt.replace("/*DATEN*/", skript(json.dumps(daten(), ensure_ascii=False, separators=(",", ":"))), 1)
    inhalt = inhalt.replace("<script>/*EDITOR*/</script>", "<script>" + skript(lesen(os.path.join(HIER, "editor.js"))) + "</script>", 1)
    seite = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
             '<style>[hidden]{display:none!important}body{margin:0}</style>\n</head>\n<body>\n' + inhalt + "\n</body>\n</html>\n")
    ziel = os.path.join(HIER, "gebaeude_baukasten.html")
    with open(ziel, "w", encoding="utf-8", newline="\n") as f:
        f.write(seite)
    print(f"{ziel}: {len(seite.encode()) / 1e6:.1f} MB")
    if "--artifact" in sys.argv:
        a = sys.argv[sys.argv.index("--artifact") + 1]
        with open(a, "w", encoding="utf-8", newline="\n") as f:
            f.write(inhalt)
        print(f"{a}: {len(inhalt.encode()) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
