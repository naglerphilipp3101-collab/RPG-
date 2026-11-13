"""Bilderbogen: jeder Satz auf mehreren Extremkörpern (vorne), ein Bild je Satz.

python3 bilderbogen.py -- <glb-ordner> <ausgabe-ordner> [satz,satz,...]
"""
import json
import os
import sys

import bpy

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.join(HIER, "..", "..", "assets", "ruestung", "blender"))
import anpassen as ap  # noqa: E402
import passform_bild as pb  # noqa: E402
from mensch_lesen import Mensch  # noqa: E402

KOERPER = [
	("Mann", {}),
	("Frau", {"geschlecht": 0.0}),
	("Frau kräftig, klein", {"geschlecht": 0.0, "gewicht": 1.0, "muskeln": 0.8, "groesse": 0.1, "brust": 0.9}),
	("Mann schmal, groß", {"gewicht": 0.0, "muskeln": 0.0, "groesse": 1.0}),
	("Mann massig", {"gewicht": 1.0, "muskeln": 1.0, "regler": {"bauch": 1.0, "schultern": 1.0, "oberarm_muskel": 1.0}}),
	("Frau Zufall", {"geschlecht": 0.0, "groesse": 0.7, "gewicht": 0.3, "regler": {"huefte": 1.0, "po": 1.0, "taille": -1.0,
		"schultern": -1.0, "bein_laenge": 1.0, "kopf_breite": 1.0}}),
]


def main():
	a = sys.argv[sys.argv.index("--") + 1:]
	ordner, aus = a[:2]
	os.makedirs(aus, exist_ok=True)
	saetze = a[2].split(",") if len(a) > 2 else sorted({f[5:].rsplit("_", 1)[0] for f in os.listdir(ordner)
		if f.startswith("iron_") and f.endswith(".glb")})
	m = Mensch()
	k0 = ap.Koerper(m)
	import vorschau
	from PIL import Image, ImageDraw
	for satz in saetze:
		bilder = []
		for name, aus_k in KOERPER:
			bpy.ops.wm.read_factory_settings(use_empty=True)
			pb.satz_auf_koerper(ordner, satz, aus_k, m=m, k0=k0)
			f = vorschau.bilder(os.path.join(aus, "_tmp"), hoehe=(-0.02, 1.95), groesse=(300, 520),
				ansichten=[(25, "v")])
			im = Image.open(f).convert("RGB")
			ImageDraw.Draw(im).text((8, 6), name, fill=(20, 20, 20))
			bilder.append(im)
		w, h = bilder[0].size
		bogen = Image.new("RGB", (w * len(bilder), h))
		for i, im in enumerate(bilder):
			bogen.paste(im, (i * w, 0))
		bogen.save(os.path.join(aus, "koerper_%s.png" % satz))
		print(satz, "fertig")
		sys.stdout.flush()
	if os.path.exists(os.path.join(aus, "_tmp.png")):
		os.remove(os.path.join(aus, "_tmp.png"))


if __name__ == "__main__":
	main()
