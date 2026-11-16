"""Tier-Stile der Rüstung: gleiche Schnitte wie Iron, eigene Farben und Zierde je Tier.

Zierde wird nach dem Verringern auf die fertigen Teile gesetzt (feine Röhren würden das Verringern nicht überstehen):
- Ranke: verzierte Goldranke (Stiel mit eingerollten Trieben) entlang der Plattenränder, auf der Außenfläche.
- Kamm: Helmkamm in der Mitte über den Scheitel, mit Goldkante (nur Helme mit Platte oben).
- Borte: gestickte Goldborte an den Säumen von Stoff (doppelte Litze und Wellenlinie).
Alles liegt außen auf der Fläche, nie darunter.
"""
import math

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import rgeo as g

STILE = {
	"iron": {"farben": {}, "ranke": False, "kamm": False, "borte": False},
	"palladium": {
		# Palladium (Nutzerentscheidung 16.11.): blau-weißes Metall, Zierde gebläut (tiefes Königsblau),
		# Silberborten auf Stoff, Stoffe elfenbein / Weinrot / dunkles Königsblau
		"farben": {
			"platte": (0.74, 0.78, 0.86), "rand": (0.035, 0.07, 0.30), "niete": (0.035, 0.07, 0.30),
			"borte": (0.80, 0.82, 0.85), "kette": (0.66, 0.69, 0.75), "schuppen": (0.72, 0.76, 0.84),
			"leder": (0.30, 0.15, 0.09), "leder_dunkel": (0.11, 0.06, 0.05),
			"stoff": (0.69, 0.65, 0.56), "stoff_akzent": (0.16, 0.02, 0.04), "stoff_dunkel": (0.02, 0.03, 0.12),
			"futter": (0.79, 0.75, 0.68),
		},
		"ranke": True, "kamm": False, "borte": True,   # Kamm baut palladium.py selbst
	},
}

METALL = {"platte", "schuppen"}
STOFF = {"stoff", "stoff_akzent", "stoff_dunkel"}
ZIER = "rand"
ZIER_STOFF = "borte"   # Borten auf Stoff (eigene Farbe je Tier)


def farben_setzen(tier):
	g.FARBEN.update(STILE[tier]["farben"])


class _Netz:
	"""Schreibt neue Flächen direkt in das bmesh eines Objekts (gleiche Schnittstelle wie rgeo.Teil)."""

	def __init__(self, bm, slots):
		self.bm = bm
		self.slots = slots

	def slot(self, m):
		if m not in self.slots:
			self.slots.append(m)
		return self.slots.index(m)

	def vert(self, co):
		return self.bm.verts.new(co)

	def flaeche(self, verts, m):
		f = self.bm.faces.new(verts)
		f.material_index = self.slot(m)
		f.smooth = True
		return f


def _raender(bm, ok):
	"""Randlinien der Flächenmenge ok (Kanten mit genau einer ok-Fläche) als geordnete Punktfolgen."""
	kanten = [e for e in bm.edges if sum(1 for f in e.link_faces if ok[f.index]) == 1]
	nachbarn = {}
	for e in kanten:
		a, b = e.verts
		nachbarn.setdefault(a.index, []).append(b.index)
		nachbarn.setdefault(b.index, []).append(a.index)
	gesehen = set()
	linien = []
	for start in list(nachbarn):
		if start in gesehen or len(nachbarn[start]) != 2:
			continue
		folge = [start]
		gesehen.add(start)
		zu = False
		for richtung in (0, 1):
			cur, prev = start, None
			nxt = nachbarn[start][richtung]
			while True:
				if nxt == start:
					zu = True
					break
				if nxt in gesehen or len(nachbarn.get(nxt, [])) != 2:
					break
				gesehen.add(nxt)
				if richtung == 0:
					folge.append(nxt)
				else:
					folge.insert(0, nxt)
				prev, cur = cur, nxt
				nxt = [x for x in nachbarn[cur] if x != prev][0]
			if zu:
				break
		linien.append((folge, zu))
	return linien


def _neu_abtasten(P, zu, schritt):
	if zu:
		P = np.vstack([P, P[:1]])
	d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
	L = d[-1]
	if L < 1e-6:
		return None, 0
	u = np.arange(0, L, schritt)
	Q = np.stack([np.interp(u, d, P[:, i]) for i in range(3)], 1)
	return Q, L


class _Flaeche:
	"""Projektion auf eine Flächenmenge (nur die Außenseite eines Teils)."""

	def __init__(self, bm, ok):
		vs = [v.co.copy() for v in bm.verts]
		polys = [[v.index for v in f.verts] for f in bm.faces if ok[f.index]]
		self.bvh = BVHTree.FromPolygons(vs, polys)

	def auf(self, p, max_d=0.012):
		q, n, _, d = self.bvh.find_nearest(Vector(p), max_d)
		return (None, None) if q is None else (np.array(q), np.array(n))


def _band(P, N, F, inneres):
	"""Je Punkt der Randlinie: Tangente T und Richtung D in die Fläche hinein (Vorzeichen per Probe)."""
	T = np.gradient(P, axis=0)
	T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
	D = np.cross(N, T)
	D /= np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-9)
	treffer = [0, 0]
	for k, s in enumerate((1, -1)):
		for i in range(0, len(P), max(1, len(P) // 24)):
			q, _ = F.auf(P[i] + s * D[i] * inneres, 0.006)
			treffer[k] += q is not None
	return D * (1 if treffer[0] >= treffer[1] else -1), max(treffer) / max(1, len(range(0, len(P), max(1, len(P) // 24))))


def _zeichnen(t, F, P, D, linien2d, radius, hoehe, flach=1.0, material=ZIER):
	"""2D-Linien (u = Index entlang des Rands, v = Abstand nach innen) auf die Fläche legen und als Röhre bauen."""
	for lin in linien2d:
		stueck = []
		for ui, v in lin:
			i = int(math.floor(ui))
			if i < 0 or i >= len(P) - 1:
				q = None
			else:
				f = ui - i      # zwischen zwei Randpunkten weich übergehen (Spiralen feiner als die Abtastung)
				pp = P[i] * (1 - f) + P[i + 1] * f
				dd = D[i] * (1 - f) + D[i + 1] * f
				q, n = F.auf(pp + dd * v, 0.008)
			if q is None:
				if len(stueck) > 3:
					_rohr(t, F, stueck, radius, hoehe, flach, material)
				stueck = []
				continue
			stueck.append((q, n))
		if len(stueck) > 3:
			_rohr(t, F, stueck, radius, hoehe, flach, material)


def _rohr(t, F, stueck, radius, hoehe, flach, material):
	pts = [Vector(q + n * (hoehe + radius * flach)) for q, n in stueck]
	# doppelte Punkte entfernen
	sauber = [pts[0]]
	for p in pts[1:]:
		if (p - sauber[-1]).length > 0.0012:
			sauber.append(p)
	if len(sauber) < 3:
		return

	def aussen(p):
		_, n = F.auf(p, 0.02)
		return Vector(n) if n is not None else Vector((0, 0, 1))
	g.zug(t, sauber, radius, material, seg=4, flach=flach, aussen=aussen)


def _streifen(t, F, P, D, v0, v1, hoehe, material=ZIER):
	"""Flacher Streifen zwischen v0 und v1 (Abstand vom Rand nach innen), knapp über der Fläche."""
	reihe = []
	for i in range(len(P)):
		a, na = F.auf(P[i] + D[i] * v0, 0.006)
		b, nb_ = F.auf(P[i] + D[i] * v1, 0.006)
		reihe.append(None if a is None or b is None else (a + na * hoehe, b + nb_ * hoehe, a + na * (hoehe * 0.3), b + nb_ * (hoehe * 0.3)))
	stueck = []
	for r in reihe + [None]:
		if r is not None:
			stueck.append([t.vert(Vector(x)) for x in r])
			continue
		for i in range(len(stueck) - 1):
			a0, b0, ua0, ub0 = stueck[i]
			a1, b1, ua1, ub1 = stueck[i + 1]
			t.flaeche([a0, a1, b1, b0], material)            # Oberseite
			t.flaeche([ua0, ua1, a1, a0], material)          # Kante außen
			t.flaeche([b0, b1, ub1, ub0], material)          # Kante innen
		stueck = []


def _ranke_2d(n, schritt, b=0.020, a=0.0055, wl=0.075):
	"""Stiel als Welle mit eingerollten Trieben an jedem Wellenberg/-tal (Rankenmuster)."""
	u = np.arange(n)
	um = u * schritt
	stiel = [(i, b + a * math.sin(2 * math.pi * x / wl)) for i, x in zip(u, um)]
	linien = [stiel]
	k = 0
	x = wl * 0.25
	while x < um[-1] - wl * 0.3:
		innen = k % 2 == 0
		v0 = b + (a if innen else -a)
		r0 = 0.0095 if innen else 0.0065
		sg = 1 if innen else -1
		# Spirale beginnt am Stiel und rollt sich ein (1,4 Umdrehungen)
		c_u, c_v = x + r0 * 0.6, v0 + sg * r0 * 0.8
		w0 = math.atan2(v0 - c_v, x - c_u)
		sp = []
		for th in np.linspace(0, 2.8 * math.pi, 26):
			r = r0 * (1 - th / (3.4 * math.pi))
			w = w0 + sg * th
			sp.append(((c_u + r * math.cos(w)) / schritt, c_v + r * math.sin(w)))
		linien.append(sp)
		# kleines Blatt gegenüber
		bl = []
		for th in np.linspace(0, math.pi, 7):
			bl.append(((x + wl * 0.25 + 0.006 * math.cos(th) - 0.006) / schritt, v0 - sg * 0.004 - sg * 0.004 * math.sin(th)))
		linien.append(bl)
		x += wl * 0.5
		k += 1
	return linien


def _borte_2d(n, schritt, L, rang):
	"""Stoffsaum: breite Borte (Farbe je Tier), innen eine feine Wellenlinie."""
	u = np.arange(n)
	um = u * schritt
	return [("band", 0.004, 0.016, 0.0004),
		("linie", [(i, 0.0225 + 0.0035 * math.sin(2 * math.pi * x / 0.028)) for i, x in zip(u, um)], 0.0014, 0.6)]


def _rand_2d(n, schritt, L, rang):
	"""Plattenrand: vergoldeter Randstreifen und eine feine Begleitlinie; an langen Rändern zusätzlich die Ranke."""
	u = np.arange(n)
	out = [("band", 0.002, 0.013, 0.0003), ("linie", [(i, 0.019) for i in u], 0.0011, 0.7)]
	if L > 0.6 and rang < 3:            # Ranke nur an den drei längsten Rändern eines Teils
		for lin in _ranke_2d(n, schritt, b=0.033, a=0.005, wl=0.09)[1:]:
			out.append(("linie", lin, 0.0011, 0.7))
		out.append(("linie", [(i, 0.033 + 0.005 * math.sin(2 * math.pi * x / 0.09)) for i, x in zip(u, u * schritt)], 0.0011, 0.7))
	return out


def _aussen_maske(bm, K, mats, erlaubt):
	"""Flächen eines Materials aus erlaubt, deren Normale vom Körper weg zeigt (Außenseite)."""
	bvh = K.bvh_bereich(lambda x, y, z: np.ones(len(x), bool), "alles")
	ok = np.zeros(len(bm.faces), bool)
	for f in bm.faces:
		if mats[f.material_index] not in erlaubt:
			continue
		c = f.calc_center_median()
		q, _, _, _ = bvh.find_nearest(c)
		if q is None:
			continue
		r = c - q
		if r.length > 1e-5 and f.normal.dot(r.normalized()) > 0.2:
			ok[f.index] = True
	return _loecher_fuellen(bm, ok)


def _loecher_fuellen(bm, ok, max_flaeche=0.06):
	"""Kleine Inseln nicht erlaubter Flächen, die nur an ok-Flächen grenzen (z. B. eingezogene Falte am Gesäß),
	zählen mit: sonst entstünden dort Goldringe ohne echten Rand."""
	gesehen = np.zeros(len(bm.faces), bool)
	for f0 in bm.faces:
		if ok[f0.index] or gesehen[f0.index]:
			continue
		insel, stapel, flaeche, offen = [], [f0], 0.0, False
		gesehen[f0.index] = True
		while stapel:
			f = stapel.pop()
			insel.append(f.index)
			flaeche += f.calc_area()
			for e in f.edges:
				if len(e.link_faces) < 2:
					offen = True
				for n in e.link_faces:
					if not ok[n.index] and not gesehen[n.index]:
						gesehen[n.index] = True
						stapel.append(n)
		if not offen and flaeche < max_flaeche:
			ok[insel] = True
	return ok


def _linien_ziehen(bm, ok, t, F, muster, min_l, hoehe, schritt=0.008, material=ZIER):
	n_lin = 0
	bm.verts.ensure_lookup_table()
	linien = []
	for folge, zu in _raender(bm, ok):
		bm.verts.ensure_lookup_table()
		P0 = np.array([bm.verts[i].co[:] for i in folge])
		P, L = _neu_abtasten(P0, zu, schritt)
		if P is None or L < min_l:
			continue
		linien.append((L, P))
	linien.sort(key=lambda x: -x[0])
	for rang, (L, P) in enumerate(linien):
		N = []
		for p in P:
			_, n = F.auf(p, 0.01)
			N.append(n if n is not None else np.array([0, 0, 1.0]))
		N = np.array(N)
		D, anteil = _band(P, N, F, 0.02)
		if anteil < 0.5:
			continue
		for art, *werte in muster(len(P), schritt, L, rang):
			if art == "band":
				_streifen(t, F, P, D, werte[0], werte[1], hoehe + werte[2], material)
			else:
				_zeichnen(t, F, P, D, [werte[0]], werte[1], hoehe, werte[2], material)
		n_lin += 1
	return n_lin


def _kamm(t, bm, mats, K, F_alles):
	"""Kamm über den Scheitel: schmale Blechfinne von der Stirn bis zum Hinterkopf, Goldkante oben."""
	kopf_oben = float(K.p[:, 2].max())
	ys = np.linspace(-0.16, 0.16, 81)
	reihe = []
	for y in ys:
		h = F_alles.bvh.ray_cast(Vector((0, y, 2.4)), Vector((0, 0, -1)), 1.0)
		if h[0] is None or h[0].z < kopf_oben - 0.10:
			reihe.append(None)
			continue
		f = bm.faces[h[2]]
		reihe.append((np.array(h[0]), np.array(h[1])) if mats[f.material_index] in METALL else None)
	# längstes zusammenhängendes Stück
	best, cur = [], []
	for r in reihe + [None]:
		if r is None:
			best = cur if len(cur) > len(best) else best
			cur = []
		else:
			cur.append(r)
	print("  Kamm: %d von %d Stellen auf Blech" % (len(best), len(reihe)))
	if len(best) < 25:
		return False
	m = len(best)
	Q = np.array([q for q, _ in best])
	Nn = np.array([n for _, n in best])
	# glätten, damit der Kamm als ruhiger Bogen läuft (Sehschlitz, Nieten usw. nicht nachzeichnen)
	k = np.ones(9) / 9
	Qg = np.stack([np.convolve(np.pad(Q[:, i], 4, mode="edge"), k, "valid") for i in range(3)], 1)
	Ng = np.stack([np.convolve(np.pad(Nn[:, i], 4, mode="edge"), k, "valid") for i in range(3)], 1)
	Ng /= np.linalg.norm(Ng, axis=1, keepdims=True)
	unten, oben = [], []
	for i in range(m):
		s = i / (m - 1)
		h = 0.040 * math.sin(math.pi * s) ** 0.6 + 0.002
		unten.append(Qg[i] - Ng[i] * 0.004)
		oben.append(Qg[i] + Ng[i] * h)
	dx = np.array([0.0022, 0, 0])
	L = [[t.vert(Vector(p + sx * dx)) for p in (unten if k == 0 else oben)] for sx in (1, -1) for k in (0, 1)]
	ru, ro, lu, lo = L
	for i in range(m - 1):
		t.flaeche([ru[i], ru[i + 1], ro[i + 1], ro[i]], "platte")
		t.flaeche([lu[i + 1], lu[i], lo[i], lo[i + 1]], "platte")
		t.flaeche([ro[i], ro[i + 1], lo[i + 1], lo[i]], "platte")
	g.zug(t, [Vector(p + np.array([0, 0, 0.001])) for p in oben[1:-1]], 0.003, ZIER, seg=6)
	return True


def zieren(ob, K, slot, tier):
	st = STILE[tier]
	if not (st["ranke"] or st["kamm"] or st["borte"]):
		return ob
	me = ob.data
	mats = [m.name for m in me.materials]
	bm = bmesh.new()
	bm.from_mesh(me)
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	bm.normal_update()
	slots = list(mats)
	t = _Netz(bm, slots)
	n_alt = len(bm.faces)
	bericht = []
	if st["ranke"]:
		ok = _aussen_maske(bm, K, mats, METALL)
		if ok.any():
			F = _Flaeche(bm, ok)
			bericht.append("ranke %d" % _linien_ziehen(bm, ok, t, F, _rand_2d, 0.10, 0.0010))
	if st["borte"]:
		bm.faces.ensure_lookup_table()
		ok = np.zeros(len(bm.faces), bool)
		ok[:n_alt] = _aussen_maske(bm, K, slots, STOFF)[:n_alt]
		if ok.any():
			F = _Flaeche(bm, ok)
			bericht.append("borte %d" % _linien_ziehen(bm, ok, t, F, _borte_2d, 0.35, 0.0008, material=ZIER_STOFF))
	if st["kamm"] and slot == "kopf":
		bm.faces.ensure_lookup_table()
		alle = np.zeros(len(bm.faces), bool)
		alle[:n_alt] = True
		if _kamm(t, bm, slots, K, _Flaeche(bm, alle)):
			bericht.append("kamm")
	bm.to_mesh(me)
	bm.free()
	for m in slots[len(mats):]:
		me.materials.append(g.material(m))
	me.update()
	print(ob.name, "Zierde:", ", ".join(bericht) or "keine")
	return ob
