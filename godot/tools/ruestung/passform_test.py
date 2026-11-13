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
TOL_SCHICHT = 0.003
WEITE = 0.12

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
		self._basis = None

	def _aussen(self, k, pos, sichtbar):
		"""Je Hautpunkt: welches Teil (oder die Haut) ganz außen liegt, gesehen entlang der Hautnormale
		von außen nach innen – also das, was man an dieser Stelle sieht. -> (Teil-Nr., Abstand)"""
		bvhs = [_bvh(pos[sl], self.teile[sl]["dr"]) for sl in SLOTS] + [_bvh(k.p, k.dreiecke[sichtbar])]
		start = k.p + k.n * WEITE
		wer = np.full(len(k.p), -1)
		t_best = np.full(len(k.p), np.inf)
		tiefe = np.full((len(k.p), len(bvhs)), np.inf)
		for j, b in enumerate(bvhs):
			for i in range(len(k.p)):
				h = b.ray_cast(Vector(start[i]), Vector(-k.n[i]), WEITE + 0.03)
				if h[0] is not None:
					tiefe[i, j] = h[3]
					if h[3] < t_best[i]:
						t_best[i], wer[i] = h[3], j
		return wer, tiefe

	def pruefen(self, k0, k, korr=None):
		"""Vergleicht, was außen sichtbar ist, mit dem Standard-Körper: wechselt an einem Hautpunkt das
		äußerste Teil (inneres Teil oder Haut sticht durch), ist das ein Verstoß."""
		if self._basis is None:
			self._basis = self._aussen_fuer(k0, k0)
		wer0 = self._basis
		wer, tiefe, pos, sichtbar = self._aussen_fuer(k0, k, mit_tiefe=True)
		erg = {"haut": {}, "schicht": {}}
		namen = SLOTS + ["haut"]
		for i in np.where((wer0 >= 0) & (wer0 < len(SLOTS)) & (wer >= 0) & (wer != wer0))[0]:
			a, b = wer0[i], wer[i]
			ueber = tiefe[i, a] - tiefe[i, b]          # wie weit das neue Teil vor dem alten liegt
			if not np.isfinite(ueber):
				ueber = 0.01
			if ueber < TOL_SCHICHT:
				continue
			if namen[b] == "haut":
				z = erg["haut"].setdefault(namen[a], [0, 0.0])
			else:
				z = erg["schicht"].setdefault("%s>%s" % (namen[b], namen[a]), [0, 0.0])
			z[0] += 1
			z[1] = max(z[1], float(ueber * 1000))
		# Loch: vorher Rüstung, jetzt gar nichts (auch keine Haut, weil verdeckt) -> man sieht ins Leere
		loch = (wer0 >= 0) & (wer0 < len(SLOTS)) & (wer < 0)
		if loch.any():
			erg["haut"]["loch"] = [int(loch.sum()), 0.0]
		return erg, pos, sichtbar

	def _aussen_fuer(self, k0, k, mit_tiefe=False):
		haut_weg = np.zeros(len(k.p), bool)
		pos = {}
		for slot, t in self.teile.items():
			haut_weg |= t["verdeckt"]
			pos[slot] = ap.anwenden(t["p"], t["bind"], k0.p, k.p)
		sichtbar = ~haut_weg[k.dreiecke].all(1)
		wer, tiefe = self._aussen(k, pos, sichtbar)
		return (wer, tiefe, pos, sichtbar) if mit_tiefe else wer


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
