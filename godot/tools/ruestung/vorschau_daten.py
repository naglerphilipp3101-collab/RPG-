"""Daten für die Rüstkammer (Browser-Vorschau mit Körperreglern).

python3 vorschau_daten.py <glb-ordner> <ausgabe-ordner>

Schreibt:
- koerper.json: Haut des Grundkörpers, Dreiecke, Formen für die Regler (Alter fest 0,1, Herkunft „Nord“),
  je Form auch die Verschiebung des Bodenpunkts (Füße bleiben auf dem Boden).
- verdeckt.json: je Rüstungsteil die Hautpunkte, die darunter ausgeblendet werden.
Die Bindung Rüstung -> Haut rechnet die Seite selbst (gleiche Regel wie anpassen.bindung).
"""
import base64
import json
import os
import sys

import bpy  # noqa: F401
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anpassen as ap  # noqa: E402
from mensch_lesen import Mensch, STANDARD  # noqa: E402

REGLER = ["schultern", "v_form", "taille", "bauch", "huefte", "po", "oberarm_muskel", "arm_laenge", "bein_laenge",
	"hals_dicke"]


def b64(a):
	return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def main():
	ordner, aus = sys.argv[sys.argv.index("--") + 1:][:2] if "--" in sys.argv else sys.argv[1:3]
	os.makedirs(aus, exist_ok=True)
	m = Mensch()
	k0 = ap.Koerper(m)
	hidx = k0.haut_idx
	boden_idx = []
	for b in m.meta["gruppen"]["joint-ground"]:
		boden_idx.extend(range(int(b[0]), int(b[1]) + 1))
	boden_idx = np.array(boden_idx)
	n_alle = len(m.grund)
	# Formen, Alter fest: young 0.92, old 0.08 (wie Standard alter 0.1)
	alt = float(STANDARD["alter"]) * 0.8
	alter = {"young": 1 - alt, "old": alt}

	def dicht(name):
		d = np.zeros((n_alle, 3))
		if name in m.meta["formen"]:
			i, dd = m.form(name)
			np.add.at(d, i, dd)
		return d

	formen = {}

	def dazu(schl, d):
		dh = d[hidx]
		nz = np.where(np.abs(dh).max(1) > 2e-5)[0]
		formen[schl] = {"i": b64(nz.astype(np.uint16)), "d": b64(np.round(dh[nz] / 0.0001).astype(np.int16)),
			"boden": d[boden_idx].mean(0).round(6).tolist()}

	for gs in ("female", "male"):
		dazu("herkunft-%s" % gs, sum(alter[a] * dicht("caucasian-%s-%s" % (gs, a)) for a in alter))
		for mu in ("minmuscle", "averagemuscle", "maxmuscle"):
			for gw in ("minweight", "averageweight", "maxweight"):
				dazu("universal-%s-%s-%s" % (gs, mu, gw), sum(alter[a] * dicht("universal-%s-%s-%s-%s" % (gs, a, mu, gw)) for a in alter))
		for hh in ("minheight", "maxheight"):
			dazu("hoehe-%s-%s" % (gs, hh), sum(alter[a] * dicht("hoehe-%s-%s-%s" % (gs, a, hh)) for a in alter))
	for c in ("mincup", "averagecup", "maxcup"):
		for f in ("minfirmness", "averagefirmness", "maxfirmness"):
			dazu("brust-%s-%s" % (c, f), sum(alter[a] * dicht("brust-%s-%s-%s" % (a, c, f)) for a in alter))
	for r in REGLER:
		for v in "+-":
			dazu(r + v, dicht(r + v))
	grund = m.grund
	koerper = {
		"punkte": b64(grund[hidx].astype(np.float32)),
		"boden0": grund[boden_idx].mean(0).tolist(),
		"dreiecke": b64(k0.dreiecke.astype(np.uint16)),
		"formen": formen,
		"regler": [{"id": r["id"], "name": r["name"]} for r in m.meta["regler"] if r["id"] in REGLER],
		"bindung": {"faktor": ap.SIGMA_FAKTOR, "min": ap.SIGMA_MIN, "max": ap.SIGMA_MAX, "max_n": ap.MAX_N,
			"raster": ap.RASTER},
	}
	json.dump(koerper, open(os.path.join(aus, "koerper.json"), "w"), separators=(",", ":"))
	# Prüfung: JS-Rechnung nachgestellt == form_berechnen
	verdeckt = {}
	for f in sorted(os.listdir(ordner)):
		if f.startswith("iron_") and f.endswith(".glb"):
			p, dr, _, _ = ap.glb_netz(os.path.join(ordner, f))
			v = ap.verdeckt(k0.p, k0.n, k0.dreiecke, p, dr)
			verdeckt[f[:-4]] = b64(np.where(v)[0].astype(np.uint16))
			print(f, int(v.sum()))
	json.dump(verdeckt, open(os.path.join(aus, "verdeckt.json"), "w"), separators=(",", ":"))
	print("koerper.json %.1f MB" % (os.path.getsize(os.path.join(aus, "koerper.json")) / 1e6))


if __name__ == "__main__":
	main()
