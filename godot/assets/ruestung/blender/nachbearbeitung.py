"""Nachbearbeitung fertiger Rüstungsteile: weniger „aufgeblasen“, mehr Handwerk.

- Faltenwurf: hängender Stoff, Leder und Kette unterhalb der Hüfte (Roben, Röcke, Wappenröcke)
  bekommt senkrechte Falten. Das Muster hängt nur von Ort und Winkel ab, deshalb falten
  übereinanderliegende Lagen gleich und kreuzen sich nicht. Hosen (nah am Bein) bleiben glatt.
- Grat: Brustplatten und Beinschienen bekommen einen scharfen Mittelgrat wie getriebenes Blech.
- Unruhe: leichte, unregelmäßige Wellen (Stoff/Leder stärker, Blech kaum), damit Flächen nicht
  wie gegossen wirken. Immer vom Körper weg, nie hinein.
Alles verschiebt Punkte nur nach außen (weg vom Körper bzw. von der Körperachse).
"""
import math

import bmesh
import numpy as np
from mathutils import Vector

import rgeo as g

STOFFE = {"stoff": 1.0, "stoff_akzent": 1.0, "stoff_dunkel": 1.0, "futter": 1.0, "leder": 0.55, "leder_dunkel": 0.55,
	"kette": 0.45, "fell": 0.6}
METALL = {"platte", "rand", "niete", "schuppen"}
HUEFTE = 0.98
FALTEN_A = 0.026


def _inseln(bm):
	"""Zusammenhängende Flächengruppen -> Liste von Punktmengen und Materialmengen."""
	gesehen = set()
	out = []
	for f in bm.faces:
		if f.index in gesehen:
			continue
		stapel = [f]
		gesehen.add(f.index)
		pts, mats = set(), set()
		while stapel:
			x = stapel.pop()
			mats.add(x.material_index)
			for v in x.verts:
				pts.add(v.index)
			for e in x.edges:
				for y in e.link_faces:
					if y.index not in gesehen:
						gesehen.add(y.index)
						stapel.append(y)
		out.append((pts, mats))
	return out


def _faltenmuster(x, y, z):
	"""0..1 je Punkt: senkrechte Falten, leicht gewunden, unregelmäßig hoch."""
	th = np.arctan2(x, -y)
	# runde Bäuche, scharfe Täler (|sin|), Falten laufen nach unten leicht auseinander
	ph = 7.0 * th + 0.35 * np.sin(2 * th + z * 2.0) + 0.2 * np.sin(z * 4.0 + 1.0) + 0.12 * np.sin(13 * th)
	f = np.abs(np.sin(ph)) ** 0.75
	f2 = (0.5 + 0.5 * np.sin(17 * th + 2.0 + 0.6 * np.sin(z * 4))) ** 2
	return 0.9 * f + 0.1 * f2


def _rauschen(p, staerke, saat=3):
	"""Glatte 3D-Wellen 0..1 (Summe weniger Sinus in festen Zufallsrichtungen)."""
	rng = np.random.default_rng(saat)
	s = np.zeros(len(p))
	for wl, gew in ((0.16, 0.7), (0.07, 0.3)):
		for _ in range(3):
			d = rng.normal(size=3)
			d /= np.linalg.norm(d)
			s += gew * np.sin(p @ d * (2 * math.pi / wl) + rng.uniform(0, 6.3))
	return np.clip(0.5 + s / 3.0, 0, 1) * staerke


def bearbeiten(ob, K, slot, falten=True, grat=True, unruhe=True):
	me = ob.data
	bm = bmesh.new()
	bm.from_mesh(me)
	bm.verts.ensure_lookup_table()
	bm.faces.ensure_lookup_table()
	mats = [m.name for m in me.materials]
	p = np.array([v.co[:] for v in bm.verts])
	n = len(p)
	# Material je Punkt (Stoff-Faktor, Metall ja/nein)
	stoff = np.zeros(n)
	metall = np.zeros(n, bool)
	for f in bm.faces:
		mn = mats[f.material_index] if mats else ""
		for v in f.verts:
			stoff[v.index] = max(stoff[v.index], STOFFE.get(mn, 0.0))
			if mn in METALL:
				metall[v.index] = True
	# Inseln mit Blech bewegen sich nicht mit dem Stoff (Beintaschen samt Nieten bleiben starr)
	insel_metall = np.zeros(n, bool)
	insel_stoff = np.zeros(n)
	haengt = np.zeros(n, bool)
	inseln = []
	for pts, ms in _inseln(bm):
		names = {mats[i] for i in ms} if mats else set()
		idx = np.fromiter(pts, int)
		q = p[idx]
		# hängt frei, wenn das Teil zwischen den Beinen hindurch reicht (Rock, Robe, Wappenrock; keine Hose)
		u = q[q[:, 2] < 0.62]
		haengt[idx] = len(u) > 0 and bool((np.abs(u[:, 0]) < 0.03).any() and (u[:, 0] < -0.06).any() and (u[:, 0] > 0.06).any()) and not (names & {"platte", "schuppen"})
		inseln.append(idx)
	# Besätze, Säume, Knöpfe auf hängendem Stoff hängen mit (überwiegend nah an hängenden Punkten)
	if haengt.any():
		from scipy.spatial import cKDTree
		baum = cKDTree(p[haengt])
		for idx in inseln:
			if not haengt[idx[0]]:
				d, _ = baum.query(p[idx], distance_upper_bound=0.02)
				if np.mean(np.isfinite(d)) > 0.5:
					haengt[idx] = True
		if names & {"platte", "schuppen"}:
			insel_metall[idx] = True
		insel_stoff[idx] = max([STOFFE.get(x, 0.0) for x in names] + [0.0])
	# Abstand und Richtung zur Haut
	bvh = K.bvh_bereich(lambda x, y, z: np.ones(len(x), bool), "alles")
	beine = K.bvh(["UpperLeg", "LowerLeg", "Foot"])
	weg = np.zeros((n, 3))
	aussen = np.zeros((n, 3))
	d_bein = np.full(n, 1.0)
	for i, q in enumerate(p):
		v = Vector(q)
		h = bvh.find_nearest(v)
		if h[0] is not None:
			r = v - h[0]
			aussen[i] = (r.normalized() if r.length > 1e-6 else h[1])[:]
		if q[2] < HUEFTE + 0.02:
			hb = beine.find_nearest(v, 0.2)
			if hb[0] is not None:
				d_bein[i] = (v - hb[0]).length
	x, y, z = p[:, 0], p[:, 1], p[:, 2]
	# ---- Faltenwurf
	if falten and slot in ("brust", "beine"):
		a = FALTEN_A * np.clip((HUEFTE - z) / 0.55, 0, 1) ** 0.8
		a *= haengt                                                   # Hosen bleiben glatt
		a *= np.where(insel_metall, 0.0, np.maximum(stoff, insel_stoff))
		radial = np.stack([x, y + 0.0, np.zeros(n)], 1)
		radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-6)
		weg += radial * (a * _faltenmuster(x, y, z))[:, None]
		# Blechteile über/neben gefaltetem Stoff (Beintaschen, Gürtelplatten) als Ganzes mitschieben
		bewegt = np.linalg.norm(weg, axis=1)
		if (bewegt > 1e-4).any():
			from scipy.spatial import cKDTree
			baum = cKDTree(p[bewegt > 1e-4])
			for idx in inseln:
				if insel_metall[idx[0]]:
					d, j = baum.query(p[idx], distance_upper_bound=0.03)
					ok = np.isfinite(d)
					if ok.any():
						quelle = np.where(bewegt > 1e-4)[0][j[ok]]
						weg[idx] += weg[quelle].max(axis=0) * 0 + weg[quelle][np.argmax(bewegt[quelle])]
	# ---- Mittelgrat auf Blech
	if grat and slot == "brust":
		m = insel_metall & (y < -0.03) & (np.abs(x) < 0.11)
		t = np.clip(1 - np.abs(x) / 0.11, 0, 1)
		fz = np.clip((z - 1.02) / 0.08, 0, 1) * np.clip((1.47 - z) / 0.1, 0, 1)
		weg[:, 1] -= np.where(m, 0.007 * t ** 1.4 * fz, 0)
	if grat and slot == "beine":
		for seite in (1, -1):
			knie = K.gelenk(("Left" if seite > 0 else "Right") + "LowerLeg")
			fuss = K.gelenk(("Left" if seite > 0 else "Right") + "Foot")
			u = np.clip((z - fuss.z) / (knie.z - fuss.z), 0, 1)
			mx = fuss.x + (knie.x - fuss.x) * u
			m = insel_metall & (np.sign(x) == seite) & (y < -0.02) & (np.abs(x - mx) < 0.05)
			t = np.clip(1 - np.abs(x - mx) / 0.05, 0, 1)
			fz = np.clip((z - fuss.z - 0.07) / 0.06, 0, 1) * np.clip((knie.z - 0.04 - z) / 0.06, 0, 1)
			weg[:, 1] -= np.where(m, 0.004 * t ** 1.4 * fz, 0)
	# ---- Unruhe
	if unruhe:
		# gleich stark für alle Lagen an einem Ort -> übereinanderliegende Teile bleiben in Reihenfolge
		weg += aussen * _rauschen(p, 0.0009)[:, None]
	for i, v in enumerate(bm.verts):
		v.co = Vector(p[i] + weg[i])
	bm.to_mesh(me)
	bm.free()
	me.update()
	return ob
