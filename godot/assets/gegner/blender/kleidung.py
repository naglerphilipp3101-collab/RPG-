"""Kleidung ohne Rüstung für menschliche Gegner (Bauer, Bürger, Seemann, Pirat, Vampir, Kutte).

Baut auf denselben Bausteinen wie die Spieler-Rüstung (assets/ruestung/blender: rgeo, iron, waffensaetze) und auf demselben
MakeHuman-Körper. Jede Funktion gibt eine Liste von Objekten zurück; die Sätze in gegner_typen.py vereinen sie je Slot.
Materialnamen wie bei der Rüstung (stoff, stoff_akzent, stoff_dunkel, futter, leder, leder_dunkel, rand ...),
damit das Spiel sie gleich behandelt. Farben je Gegner kommen aus gegner_typen.py.
"""
import math
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "..", "ruestung", "blender"))

import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

import rgeo as g  # noqa: E402
import iron as ir  # noqa: E402
import waffensaetze as ws  # noqa: E402
from iron import tabelle, ZW  # noqa: E402

PI = math.pi


# ---------------------------------------------------------------- Abnutzung

STOFFE = ("stoff", "stoff_akzent", "stoff_dunkel", "futter")


def zerreissen(obs, saat=1, loecher=0.0, fransen=0.0, fransen_hoehe=0.05):
	"""Löcher und ausgefranste untere Säume: entfernt Flächen nach Rauschen.
	loecher: Anteil 0..1 (0.15 = ein paar Löcher), fransen: Saum unten gezackt (nur unterstes Stück jedes Teils)."""
	versatz = Vector((saat * 13.7, saat * 5.3, saat * 9.1))
	for ob in obs:
		bm = bmesh.new()
		bm.from_mesh(ob.data)
		if not bm.faces:
			bm.free()
			continue
		z_min = min(v.co.z for v in bm.verts)
		mats = [m.name for m in ob.data.materials]
		weg = []
		for f in bm.faces:
			if mats and mats[f.material_index] not in STOFFE:
				continue   # Metall und Leder bleiben heil
			c = f.calc_center_median()
			if loecher > 0:
				n = noise.noise(c * 11.0 + versatz)
				if n > 1.0 - 1.6 * loecher:
					weg.append(f)
					continue
			if fransen > 0:
				# gezackter Rand: Zacken aus scharfem Rauschen
				zack = abs(noise.noise(Vector((c.x * 40.0, c.y * 40.0, 0.0)) + versatz))
				if c.z - z_min < fransen_hoehe * fransen * zack:
					weg.append(f)
		bmesh.ops.delete(bm, geom=weg, context="FACES")
		bm.to_mesh(ob.data)
		bm.free()
	return obs


# ---------------------------------------------------------------- Kopf


def kopftuch(K, material="stoff_akzent"):
	"""Eng gebundenes Tuch über Schädel und Hinterkopf, Knoten mit zwei Zipfeln hinten."""
	f = ir.kopf_feld(K)
	A = 0.008
	bis = lambda w: 1.02 + 0.42 * math.exp(-(g.wdiff(w, PI) / 1.1) ** 2)
	falten = lambda s, w: 0.003 * math.sin(w * 9 + s * 4) * g.weich(s, 0.3, 1.0)
	t = g.Teil("kopftuch")
	g.platte(t, f, 0.0, bis, A, nu=26, nw=96, extra=falten, material_name=material)
	teile = [ws.obj(t, 60, 0.004)]
	r = g.Teil("knoten")
	p0 = f.punkt(1.2, PI, A + 0.012)
	n0 = f.normale(1.2, PI, A)
	g.zug(r, [p0 - n0 * 0.01, p0 + n0 * 0.012], 0.018, material, seg=10)
	for seite in (1, -1):
		pts = [p0 + n0 * 0.01 + Vector((seite * 0.025 * u, 0.04 * u, -0.17 * u - 0.03 * u * u)) for u in np.linspace(0, 1, 10)]
		ws.blatt(r, pts, lambda u: 0.022 * (1 - 0.55 * u) + 0.004, Vector((0, 1, 0)), material)
	teile.append(ws.obj(r, 60, 0.003))
	return teile


def dreispitz(K, material="stoff_dunkel", borte="rand"):
	"""Dreispitz: flacher Hutkopf, Krempe an drei Seiten hochgeschlagen, Spitzen vorne und hinten seitlich."""
	f = ir.kopf_feld(K)
	ab, H, R = ws.topf_flaeche(f, 0.016, rund=0.035, hoeher=0.03, weiter=0.008)
	s_r = 1.1
	teile = [ws.blech("hut", f, 0.0, s_r, ab, d=0.004, nu=32, nw=96, material_name=material)]
	r = g.Teil("krempe")
	hoch = lambda w: 0.13 * (0.5 - 0.5 * math.cos(3 * w)) ** 0.45
	breite = lambda w: 0.09 + 0.035 * (0.5 + 0.5 * math.cos(3 * w)) ** 3
	aussen = ws.krempe(r, f, s_r, ab, breite, material, neigung=0.05, n=96, hoch=hoch, stufen=6)
	teile.append(ws.obj(r, 50, 0.004))
	if borte:
		b = g.Teil("borte")
		g.zug(b, aussen, 0.004, borte, zu=True, flach=0.6)
		teile.append(b.objekt())
	return teile


def filzkappe(K, material="stoff_dunkel"):
	o, f = ws.kappe(K, material, A=0.012, s_bis=lambda w: 1.0 + 0.1 * math.exp(-(g.wdiff(w, PI) / 1.0) ** 2),
		extra=lambda s, w: 0.012 * math.sin(min(1.0, s / 1.0) * PI) ** 2)
	r = g.Teil("rand")
	ws.ring(r, f, 1.0, 0.016, 0.008, material, flach=0.6, n=96)
	return [o, r.objekt()]


def kutten_kapuze(K, material="stoff", saum="stoff_akzent"):
	teile, f, weit = ws.kapuze(K, material, A=0.03, gesicht=0.78, tief=0.06, zipfel=0.02, saum=saum, kragen_weite=0.04)
	return teile


# ---------------------------------------------------------------- Rumpf


def hemd(K, material="futter", unten_z=0.74, aermel=0.95, offen=0.0, puff=0.0, abstand=0.008, weite=0.05):
	teile, f = ir.wams(K, material, abstand, unten_z=unten_z, kragen_z=1.52, aermel_bis=aermel, weite=weite,
		aermel_abstand=0.006, offen=offen, puff=puff, manschette=0.008 if aermel > 0.8 else 0.0)
	return teile


def strick(K, z=0.98, material="leder", abstand=0.03):
	"""Gürtel aus gedrehtem Strick mit herabhängendem Ende."""
	f = ir.wams_feld(K)
	r = g.Teil("strick")
	pts, zu = g.rand_punkte(f, z - ZW, abstand, n=96)
	g.zug(r, pts, 0.009, material, zu=zu)
	p0 = f.punkt(z - ZW, -0.5, abstand + 0.008)
	ende = [p0 + Vector((-0.01 * u, -0.012 * u, -0.28 * u)) for u in np.linspace(0, 1, 10)]
	g.zug(r, ende, 0.008, material)
	g.niete(r, p0, f.normale(z - ZW, -0.5, abstand), 0.016, material)
	return [r.objekt()]


def schaerpe(K, z=0.99, material="stoff_akzent", breite=0.06):
	"""Breite Stoffschärpe um die Hüfte, Knoten links mit zwei hängenden Enden."""
	f = ir.wams_feld(K)
	t = g.Teil("schaerpe")
	falten = lambda s, w: 0.004 * math.sin((s - (z - ZW)) / breite * 2 * PI) ** 2
	g.platte(t, f, z - ZW - breite / 2, z - ZW + breite / 2, 0.034, nu=8, nw=96, extra=falten, material_name=material)
	teile = [ws.obj(t, 60, 0.004)]
	r = g.Teil("enden")
	w0 = 1.05
	p0 = f.punkt(z - ZW, w0, 0.05)
	n0 = f.normale(z - ZW, w0, 0.04)
	g.zug(r, [p0 - n0 * 0.01, p0 + n0 * 0.01], 0.025, material, seg=10)
	for k, (dx, l) in enumerate(((0.02, 0.30), (-0.02, 0.24))):
		pts = [p0 + n0 * (0.012 + 0.02 * u) + Vector((dx * u, 0, -l * u)) for u in np.linspace(0, 1, 12)]
		ws.blatt(r, pts, lambda u: 0.028 + 0.008 * u, n0, material)
	teile.append(ws.obj(r, 60, 0.003))
	return teile


def mantel(K, material="stoff_akzent", unten_z=0.45, offen=0.32, manschette_material="futter", abstand=0.022,
		weite=0.10, aufschlag=True, knoepfe="rand"):
	"""Langer offener Mantel (Gehrock) bis zum Knie mit weiten Ärmelaufschlägen."""
	z0 = min(0.5, unten_z - 0.02)
	teile, f = ir.wams(K, material, abstand, unten_z=unten_z, kragen_z=1.55, aermel_bis=1.0, weite=weite, z0=z0,
		aermel_abstand=0.012, offen=offen, rock_ab=1.0)
	r = g.Teil("mantel_zier")
	if aufschlag:
		for seite in (1, -1):
			fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
			at = g.Teil("aufschlag")
			glocke = lambda s, w: 0.02 * g.weich(s, l_ges - 0.16, l_ges - 0.02)
			g.platte(at, fa, l_ges - 0.17, l_ges - 0.01, lambda s, w: 0.02 + glocke(s, w), nu=8, nw=40,
				material_name=manschette_material)
			teile.append(ws.obj(at, 60, 0.004))
	if knoepfe:
		for seite in (1, -1):
			w = seite * (offen + 0.06)
			for k in range(6):
				z = 1.32 - 0.07 * k
				g.niete(r, f.punkt(z - ZW, w, abstand + 0.004), f.normale(z - ZW, w, abstand), 0.007, knoepfe)
	# Saum an der Vorderkante
	links = [f.punkt(s, offen, abstand + 0.002) for s in np.linspace(unten_z - ZW, 1.55 - ZW, 40)]
	rechts = [f.punkt(s, -offen, abstand + 0.002) for s in np.linspace(unten_z - ZW, 1.55 - ZW, 40)]
	g.zug(r, links, 0.005, manschette_material, flach=0.5)
	g.zug(r, rechts, 0.005, manschette_material, flach=0.5)
	teile.append(r.objekt())
	return teile


def stehkragen(K, material="stoff_dunkel", futter="stoff_akzent", hoehe=0.2, weit=0.09, z=1.47):
	"""Hoher, nach außen gestellter Kragen hinter dem Kopf (Vampir), vorne offen."""
	f = ir.wams_feld(K)
	t = g.Teil("stehkragen")
	NW, NU = 48, 8
	w_von, w_bis = 0.75, 2 * PI - 0.75
	gitter = []
	for j in range(NW + 1):
		w = w_von + (w_bis - w_von) * j / NW
		basis = f.punkt(z - ZW, w, 0.02)
		aus = basis - f.achse.punkt(z - ZW)
		aus.z = 0
		aus.normalize()
		# hinten am höchsten, zu den Spitzen vorne niedriger
		hinten = 0.45 + 0.55 * math.cos(g.wdiff(w, PI) / 2.4 * PI / 2) ** 2
		zeile = []
		for i in range(NU + 1):
			u = i / NU
			zeile.append(t.vert(basis + aus * (weit * u ** 1.6) + Vector((0, 0, hoehe * hinten * u))))
		gitter.append(zeile)
	for j in range(NW):
		for i in range(NU):
			t.flaeche([gitter[j][i], gitter[j][i + 1], gitter[j + 1][i + 1], gitter[j + 1][i]], futter)
	o = ws.obj(t, 60, 0.006, 1.0)
	return [o]


def halstuch(K, material="futter"):
	"""Weißes Jabot / Halstuch vorne am Hals."""
	f = ir.wams_feld(K)
	r = g.Teil("halstuch")
	p0 = f.punkt(1.5 - ZW, 0.0, 0.025)
	pts = [p0 + Vector((0, -0.012 * u, -0.13 * u)) for u in np.linspace(0, 1, 10)]
	ws.blatt(r, pts, lambda u: 0.02 + 0.025 * u, Vector((0, -1, 0)), material)
	pts, zu = g.rand_punkte(f, 1.5 - ZW, 0.018, n=64)
	g.zug(r, pts, 0.012, material, zu=zu, flach=0.6)
	return [ws.obj(r, 60, 0.003)]


def kutte(K, material="stoff", unten_z=0.05):
	teile, f = ir.wams(K, material, 0.022, unten_z=unten_z, kragen_z=1.53, aermel_bis=1.0, weite=0.09, z0=unten_z - 0.01,
		aermel_abstand=0.016, manschette=0.03, rock_ab=1.0)
	return teile


def cape(K, material="stoff_dunkel", futter="stoff_akzent", unten_z=0.35):
	"""Umhang hinten von den Schultern bis zur Wade."""
	f = ir.wams_feld(K, z0=min(0.30, unten_z - 0.02))
	oben = tabelle([(1.3, 0.74), (PI / 2, 0.78), (PI, 0.79)])
	t = g.Teil("cape")
	A = lambda s, w: 0.06 + 0.06 * g.weich(-s, -0.45, -(unten_z - ZW)) + 0.006 * math.sin(w * 14)
	g.platte(t, f, unten_z - ZW, lambda w: oben(min(abs(g.wdiff(w, 0)), PI)) + 0.79 - ZW, A, nu=50, nw=60,
		w_von=1.3, w_bis=2 * PI - 1.3, material_name=material)
	return [ws.obj(t, 60, 0.005)]


# ---------------------------------------------------------------- Beine und Füße


def hose(K, material="stoff", unten=1.0, weit=0.0):
	ex = (lambda s, w, lk, lg: weit * g.weich(s, lk - 0.1, lk + 0.05)) if weit else None
	return ir.hose(K, material, 0.007, unten=unten, bein_extra=ex)


def schuhe(K, material="leder"):
	return [ir.stiefel(K, s, material, 0.007, 0.05) for s in (1, -1)]


def stiefel(K, material="leder", schaft=0.3, umschlag=True):
	teile = []
	for s in (1, -1):
		teile.append(ir.stiefel(K, s, material, 0.011, schaft, weite=0.02))
		if umschlag:
			teile.append(ws.umschlag(K, s, schaft, 0.034, material, 0.06, 0.01))
	return teile


def fusslappen(K, material="stoff"):
	"""Um die Füße gewickelte Lappen (Lumpen, Zombies)."""
	teile = []
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("lappen")
		ws.wickel(r, fb, l_ges - 0.14, l_ges - 0.03, 0.006, n=5, material=material, breite=0.013)
		teile.append(r.objekt())
		ff = ir.fuss_feld(K, seite)
		t = g.Teil("fuss")
		g.platte(t, ff, ff.achse.laenge() * 0.15, ff.achse.laenge() * 0.75, 0.004, nu=14, nw=40, material_name=material)
		teile.append(ws.obj(t, 60, 0.003))
	return teile


def handschuhe(K, material="leder_dunkel"):
	return [ir.handschuh(K, s, material, 0.0028, 0.06) for s in (1, -1)]
