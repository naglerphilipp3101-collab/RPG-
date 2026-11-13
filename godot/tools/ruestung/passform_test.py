"""Strenger Passform-Test: Rüstung auf vielen Körpern (Mann/Frau, alle Regler bis an die Grenzen).

python3 passform_test.py <glb-ordner> [satz,satz,...] [--koerper N] [--json bericht.json]

Prüft je Satz und Körper (alle 5 Teile angelegt):
- Haut: kein Rüstungspunkt liegt unter sichtbarer Haut (Haut stößt durch). Verdeckte Haut zählt nicht,
  sie wird im Spiel ausgeblendet.
- Schichten: Teile, die übereinanderliegen (Stiefel über Hose, Handschuh über Ärmel ...), behalten
  ihre Reihenfolge – kein inneres Teil stößt durch ein äußeres.
Ausgabe: Anzahl Verstöße und größte Tiefe (mm) je Satz und Körper, schlechteste Fälle zuerst.
"""
import json
import os
import sys

import bpy  # noqa: F401
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mensch_lesen import Mensch  # noqa: E402
import anpassen as ap  # noqa: E402

SLOTS = ["kopf", "brust", "haende", "beine", "fuesse"]
TOL_HAUT = 0.0015      # 1,5 mm unter der Haut gilt als Durchstoßen
TOL_SCHICHT = 0.0015

KOERPER_REGLER = ["schultern", "v_form", "taille", "bauch", "huefte", "po", "oberarm_muskel", "arm_laenge",
	"bein_laenge", "haende", "fuesse", "hals_dicke", "hals_laenge"]
KOPF_REGLER = ["kopf_breite", "kopf_hoehe", "kopf_tiefe", "kopf_fett", "kinn_vor", "kinn_breite", "kiefer",
	"nase_groesse", "nase_vor", "ohr_groesse", "ohr_abstand", "stirn_neigung", "wangen_voll"]


def koerper_liste(n_zufall=24, saat=7):
	"""Feste Liste: Standard Mann/Frau, Extreme jedes Grundreglers, dann Zufallskörper über alle Bereiche."""
	L = [("mann", {}), ("frau", {"geschlecht": 0.0})]
	for g, gn in ((1.0, "mann"), (0.0, "frau")):
		for k in ("alter", "groesse", "muskeln", "gewicht"):
			for v in (0.0, 1.0):
				L.append(("%s_%s_%d" % (gn, k, v), {"geschlecht": g, k: v}))
		L.append((gn + "_schwer_dick", {"geschlecht": g, "muskeln": 1.0, "gewicht": 1.0, "groesse": 1.0}))
		L.append((gn + "_klein_duenn", {"geschlecht": g, "muskeln": 0.0, "gewicht": 0.0, "groesse": 0.0}))
	for b in (0.0, 1.0):
		for f in (0.0, 1.0):
			L.append(("frau_brust_%d_%d" % (b, f), {"geschlecht": 0.0, "brust": b, "brust_fest": f, "gewicht": 0.7}))
	for r in KOERPER_REGLER + KOPF_REGLER:
		for v in (-1.0, 1.0):
			L.append(("regler_%s_%+d" % (r, v), {"geschlecht": 1.0 if v > 0 else 0.0, "regler": {r: v}}))
	rng = np.random.default_rng(saat)
	for i in range(n_zufall):
		a = {k: float(rng.uniform(0, 1)) for k in ("geschlecht", "alter", "groesse", "muskeln", "gewicht", "brust", "brust_fest")}
		a["geschlecht"] = float(rng.choice([0.0, 1.0, rng.uniform(0, 1)]))
		a["regler"] = {r: float(rng.uniform(-1, 1)) for r in KOERPER_REGLER + KOPF_REGLER}
		L.append(("zufall_%02d" % i, a))
	return L


def _bvh(p, dr):
	return BVHTree.FromPolygons([Vector(v) for v in p], dr.tolist(), all_triangles=True)


def vorzeichen_abstand(bvh, pts, max_d, flaeche=False):
	"""Abstand zur Fläche mit Vorzeichen (Normale), nan wenn weiter als max_d; optional Flächennummer."""
	out = np.full(len(pts), np.nan)
	fl = np.full(len(pts), -1)
	for i, p in enumerate(pts):
		q, n, f, d = bvh.find_nearest(Vector(p), max_d)
		if q is not None:
			out[i] = (Vector(p) - q).dot(n)
			fl[i] = f
	return (out, fl) if flaeche else out


class Satz:
	def __init__(self, ordner, name, mensch, k0, verdeckt_cache=None):
		self.name = name
		self.teile = {}
		for slot in SLOTS:
			pf = os.path.join(ordner, "iron_%s_%s.glb" % (name, slot))
			p, dr, mat, _ = ap.glb_netz(pf)
			t = {"p": p, "dr": dr, "bind": ap.bindung(p, k0.p)}
			t["verdeckt"] = ap.verdeckt(k0.p, k0.n, k0.dreiecke, p, dr)
			self.teile[slot] = t
		# Schichtpaare: Punkte von A, die im Standard-Körper nahe an B liegen (2 cm)
		self.paare = []
		for a in SLOTS:
			for b in SLOTS:
				if a == b:
					continue
				ta, tb = self.teile[a], self.teile[b]
				s = vorzeichen_abstand(_bvh(tb["p"], tb["dr"]), ta["p"], 0.02)
				nah = ~np.isnan(s) & (np.abs(s) > TOL_SCHICHT)
				if nah.sum() > 10:
					self.paare.append((a, b, np.where(nah)[0], np.sign(s[nah])))

	def pruefen(self, k0, k, korr=None):
		haut_weg = np.zeros(len(k.p), bool)
		pos = {}
		for slot, t in self.teile.items():
			haut_weg |= t["verdeckt"]
			pos[slot] = ap.anwenden(t["p"], t["bind"], k0.p, k.p)
			if korr is not None:
				pos[slot] = pos[slot] + korr(slot, t)
		sichtbar = ~haut_weg[k.dreiecke].all(1)
		bvh_haut = _bvh(k.p, k.dreiecke)
		erg = {"haut": {}, "schicht": {}}
		for slot, t in self.teile.items():
			s, f = vorzeichen_abstand(bvh_haut, pos[slot], 0.05, True)
			s[(f >= 0) & ~sichtbar[np.maximum(f, 0)]] = np.nan     # unter verdeckter Haut: unsichtbar
			schlecht = s < -TOL_HAUT
			erg["haut"][slot] = (int(np.nansum(schlecht)), float(-np.nanmin(np.append(s, 0)) * 1000))
		for a, b, idx, sg in self.paare:
			s = vorzeichen_abstand(_bvh(pos[b], self.teile[b]["dr"]), pos[a][idx], 0.03)
			gekippt = (~np.isnan(s)) & (np.sign(s) != sg) & (np.abs(s) > TOL_SCHICHT)
			if gekippt.any():
				erg["schicht"]["%s>%s" % (a, b)] = (int(gekippt.sum()), float(np.nanmax(np.abs(s[gekippt])) * 1000))
		return erg, pos, sichtbar


def main():
	arg = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
	ordner = arg[0]
	saetze = arg[1].split(",") if len(arg) > 1 and not arg[1].startswith("--") else None
	n = int(arg[arg.index("--koerper") + 1]) if "--koerper" in arg else 24
	ziel = arg[arg.index("--json") + 1] if "--json" in arg else None
	if saetze is None:
		saetze = sorted({f[5:].rsplit("_", 1)[0] for f in os.listdir(ordner) if f.startswith("iron_") and f.endswith(".glb")})
	m = Mensch()
	k0 = ap.Koerper(m)
	koerper = [(name, ap.Koerper(m, a)) for name, a in koerper_liste(n)]
	bericht = {}
	for sn in saetze:
		satz = Satz(ordner, sn, m, k0)
		zeilen = []
		for kn, k in koerper:
			erg, _, _ = satz.pruefen(k0, k)
			h = sum(v[0] for v in erg["haut"].values())
			s = sum(v[0] for v in erg["schicht"].values())
			tief = max([v[1] for v in erg["haut"].values()] + [v[1] for v in erg["schicht"].values()] + [0])
			zeilen.append((kn, h, s, tief, erg))
		bericht[sn] = zeilen
		gesamt = sum(z[1] + z[2] for z in zeilen)
		print("== %-16s Verstöße gesamt %6d, Körper mit Verstoß %d/%d" % (sn, gesamt, sum(1 for z in zeilen if z[1] + z[2]), len(zeilen)))
		for kn, h, s, tief, erg in sorted(zeilen, key=lambda z: -(z[1] + z[2]))[:6]:
			if h + s == 0:
				break
			det = {k: v for k, v in erg["haut"].items() if v[0]}
			print("   %-26s haut %5d  schicht %5d  tiefe %5.1f mm  %s %s" % (kn, h, s, tief, det, erg["schicht"]))
		sys.stdout.flush()
	if ziel:
		json.dump({k: [[z[0], z[1], z[2], z[3], z[4]] for z in v] for k, v in bericht.items()}, open(ziel, "w"), indent=1)


if __name__ == "__main__":
	main()
