"""Iron-Rüstungen (Tier 1): schlicht mittelalterlich. leicht = Stoff/Leder, mittel = Kette/Leder, schwer = Platte."""
import math
import numpy as np
from mathutils import Vector
import rgeo as g

PI = math.pi


def tabelle(punkte):
	"""Symmetrische Funktion von w aus (|w|, wert)-Paaren."""
	xs = [p[0] for p in punkte]
	ys = [p[1] for p in punkte]

	def f(w):
		a = abs(((w + PI) % (2 * PI)) - PI)
		return float(np.interp(a, xs, ys))
	return f


# ---------------------------------------------------------------- Rumpf


def _cache(K, schl, bau):
	c = K.__dict__.setdefault("_feldcache", {})
	if schl not in c:
		c[schl] = bau()
	return c[schl]


def rumpf_feld(K, glatt=(3, 2), konvex=1.0):
	return _cache(K, ("rumpf", glatt, konvex), lambda: _rumpf_feld(K, glatt, konvex))


def _rumpf_feld(K, glatt=(3, 2), konvex=1.0):
	bvh = K.bvh(["Hips", "Spine", "Chest", "UpperChest", "Shoulder", "Neck", "UpperLeg"])
	achse = g.Achse([(0, 0.0, 0.80), (0, -0.01, 1.62)])
	return g.Feld(bvh, achse, ringe=84, seg=72, konvex_anteil=konvex, glatt=glatt)


Z0 = 0.80   # s = z - Z0 auf der Rumpfachse


def schwer_brust(K, riffel=0, fauld=3, unter=None, arme=True, halsberge=True, name="iron_schwer_brust", nur_vorne=False,
		A=0.03):
	"""Harnisch. riffel: Anzahl Kehlungen (Riffelung) auf der Brust, unter: dict für wams() (None = Gambeson),
	nur_vorne: nur Bruststück mit Riemen statt Rücken."""
	arme = schwer_brust_arme(K) if arme else []
	f = rumpf_feld(K)
	t = g.Teil("brust_platte")
	oben = tabelle([(0, 0.665), (0.4, 0.70), (0.75, 0.66), (1.15, 0.52), (1.57, 0.49), (2.0, 0.52),
		(2.4, 0.70), (2.8, 0.72), (PI, 0.71)])
	unten = tabelle([(0, 0.205), (0.6, 0.225), (PI / 2, 0.24), (PI, 0.235)])
	def grat(s, w):
		d = g.wdiff(w, 0)
		e = 0.012 * math.exp(-(d / 0.22) ** 2) * g.weich(s, 0.2, 0.45)
		if riffel:
			e += 0.005 * (0.5 + 0.5 * math.cos(w * riffel * 2)) * math.exp(-(d / 1.0) ** 2) * g.weich(s, 0.15, 0.35)
		return e
	w0, w1 = (-1.75, 1.75) if nur_vorne else (0.0, 2 * PI)
	g.platte(t, f, unten, oben, A, nu=36, nw=96 if not nur_vorne else 56, extra=grat, w_von=w0, w_bis=w1)
	brust = t.objekt(30)
	g.dicke(brust, 0.003, -1.0)
	# Wulst an Hals und Armlöchern, Nieten unten
	r = g.Teil("brust_rand")
	pts, zu = g.rand_punkte(f, oben, A + 0.002, n=160, extra=grat, w_von=w0, w_bis=w1)
	g.zug(r, pts, 0.005, "platte", zu=zu)
	pts, zu = g.rand_punkte(f, unten, A, n=120, extra=grat, w_von=w0, w_bis=w1)
	g.zug(r, pts, 0.003, "rand", zu=zu)
	g.nieten_reihe(r, f, lambda w: unten(w) + 0.012, A, [w0 + 0.1 + i * (w1 - w0 - 0.2) / 17 for i in range(18)], 0.005, extra=grat)
	if nur_vorne:
		# Riemen über Schultern und um den Rücken
		for z in (0.95 - Z0 + 0.12, 0.95 - Z0 + 0.32):
			pts, _ = g.rand_punkte(f, z, 0.012, w_von=1.6, w_bis=2 * PI - 1.6, n=40)
			g.zug(r, pts, 0.012, "leder_dunkel", flach=0.3)
	# Gürtelriemen (Leder) für die Bauchreifen
	teile = [brust, r.objekt()]
	# Bauchreifen (Fauld): drei Lamellen
	for k in range(fauld):
		lt = g.Teil("fauld_%d" % k)
		a = lambda w, k=k: unten(w) - 0.055 * (k + 1)
		b = lambda w, k=k: unten(w) - 0.055 * k + 0.012
		ab = A + 0.004 + 0.004 * k
		weite = lambda s, w, k=k: 0.012 * g.weich(-s, -0.2, 0.05) * (k + 1) * 0.6
		g.platte(lt, f, a, b, ab, nu=6, nw=96, extra=weite)
		o = lt.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teile.append(o)
		rr = g.Teil("fauld_rand_%d" % k)
		pts, zu = g.rand_punkte(f, a, ab, n=120, extra=weite)
		g.zug(rr, pts, 0.003, "rand", zu=zu)
		g.nieten_reihe(rr, f, lambda w, k=k: unten(w) - 0.055 * k + 0.004, ab, [i * 2 * PI / 12 + 0.26 for i in range(12)],
			0.0045, extra=weite)
		teile.append(rr.objekt())
	if not halsberge:
		unter = unter or {}
		u, _ = wams(K, **dict(dict(material="stoff", abstand=0.008, unten_z=0.86, kragen_z=1.50, aermel_bis=1.0, steppung=0.003,
			weite=0.0, aermel_abstand=0.004), **unter))
		return g.vereinen(teile + arme + u, name)
	# Halsberge (Kragen) über dem Brustrand
	kt = g.Teil("halsberge")
	hk_u = tabelle([(0, 0.63), (0.6, 0.66), (1.2, 0.635), (PI / 2, 0.63), (2.4, 0.67), (PI, 0.68)])
	hk_o = tabelle([(0, 0.77), (PI / 2, 0.785), (PI, 0.80)])
	g.platte(kt, f, hk_u, hk_o, 0.034, nu=14, nw=96)
	o = kt.objekt(30)
	g.dicke(o, 0.003, -1.0)
	teile.append(o)
	kr = g.Teil("halsberge_rand")
	pts, zu = g.rand_punkte(f, hk_o, 0.036, n=120)
	g.zug(kr, pts, 0.005, "platte", zu=zu)
	pts, zu = g.rand_punkte(f, hk_u, 0.034, n=120)
	g.zug(kr, pts, 0.003, "rand", zu=zu)
	teile.append(kr.objekt())
	unter = unter or {}
	u, _ = wams(K, **dict(dict(material="stoff", abstand=0.008, unten_z=0.86, kragen_z=1.50, aermel_bis=1.0, steppung=0.003,
		weite=0.0, aermel_abstand=0.004), **unter))
	return g.vereinen(teile + arme + u, name)


# ---------------------------------------------------------------- Arme


def arm_achse(K, seite=1):
	"""Achse Schulter -> Ellbogen -> Handgelenk (seite 1 = links/+X)."""
	n = "Left" if seite > 0 else "Right"
	s = K.gelenk(n + "UpperArm")
	e = K.gelenk(n + "LowerArm")
	h = K.gelenk(n + "Hand")
	return g.Achse([s, e, h]), (s - e).length, (s - e).length + (h - e).length


def arm_feld(K, seite=1, konvex=1.0):
	return _cache(K, ("arm", seite, konvex), lambda: _arm_feld(K, seite, konvex))


def _arm_feld(K, seite=1, konvex=1.0):
	achse, l_ober, l_ges = arm_achse(K, seite)
	n = "Left" if seite > 0 else "Right"
	bvh = K.bvh([n + "UpperArm", n + "LowerArm"], 0.5)
	return g.Feld(bvh, achse, ringe=60, seg=48, r_max=0.2, konvex_anteil=konvex, glatt=(3, 2)), l_ober, l_ges


def schulter_feld(K, seite=1):
	n = "Left" if seite > 0 else "Right"
	s = K.gelenk(n + "UpperArm")
	bvh = K.bvh([n + "Shoulder", n + "UpperArm", "UpperChest"], 0.3)
	mitte = s + Vector((-0.035 * seite, 0.0, -0.035))
	return g.Kugelfeld(bvh, mitte, Vector((0.55 * seite, 0, 1.0)), ringe=48, seg=72, r_max=0.3, phi_max=2.2, huelle=8)


def oberarm_feld(K, seite=1):
	"""Oberarm mit nach oben verlängerter Achse (für Schulterlamellen)."""
	n = "Left" if seite > 0 else "Right"
	s = K.gelenk(n + "UpperArm")
	e = K.gelenk(n + "LowerArm")
	d = (e - s).normalized()
	bvh = K.bvh([n + "UpperArm", n + "Shoulder"], 0.4)
	return g.Feld(bvh, g.Achse([s - d * 0.05, e]), ringe=40, seg=48, r_max=0.25, konvex_anteil=1.0, glatt=(3, 2))


def _schulter(K, seite):
	f = schulter_feld(K, seite)
	aussen = PI / 2 if seite > 0 else 3 * PI / 2
	kappe_bis = lambda w: 0.72 + 0.6 * (1 - (g.wdiff(w, aussen) / PI) ** 2)
	t = g.Teil("schulter")
	A = 0.03
	g.platte(t, f, 0.0, kappe_bis, A, nu=22, nw=72)
	o = t.objekt(30)
	g.dicke(o, 0.003, -1.0)
	teile = [o]
	r = g.Teil("schulter_rand")
	pts, zu = g.rand_punkte(f, kappe_bis, A + 0.002, n=120)
	g.zug(r, pts, 0.005, "platte", zu=zu)
	# Lamellen um den Oberarm (Achse oben verlängert, außen = 3π/2 links, π/2 rechts)
	fa = oberarm_feld(K, seite)
	aussen_arm = 3 * PI / 2 if seite > 0 else PI / 2
	for k in range(3):
		a0 = 0.075 + 0.042 * k
		breite = 1.55 - 0.12 * k
		ab = 0.03 - 0.004 * k
		lt = g.Teil("schulter_lamelle")
		g.platte(lt, fa, a0, a0 + 0.058, ab, nu=6, nw=28, w_von=aussen_arm - breite, w_bis=aussen_arm + breite)
		o = lt.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teile.append(o)
		pts, zu = g.rand_punkte(fa, a0 + 0.058, ab, w_von=aussen_arm - breite, w_bis=aussen_arm + breite, n=40)
		g.zug(r, pts, 0.003, "rand", zu=False)
		g.nieten_reihe(r, fa, a0 + 0.02, ab, [aussen_arm - breite + 0.2, aussen_arm + breite - 0.2], 0.004)
	g.nieten_reihe(r, f, lambda w: kappe_bis(w) - 0.06, A, [aussen - 1.2, aussen + 1.2], 0.005)
	teile.append(r.objekt())
	return teile


def _oberarm(K, seite):
	f, l_ober, l_ges = arm_feld(K, seite)
	teile = []
	t = g.Teil("oberarm")
	A = 0.012
	g.platte(t, f, 0.11, l_ober - 0.035, A, nu=12, nw=48)
	o = t.objekt(30)
	g.dicke(o, 0.0025, -1.0)
	teile.append(o)
	r = g.Teil("oberarm_rand")
	for s in (0.11, l_ober - 0.035):
		pts, zu = g.rand_punkte(f, s, A, n=64)
		g.zug(r, pts, 0.004, "rand", zu=zu)
	# Ellbogenkachel
	ell = PI   # Ellbogenspitze zeigt nach hinten
	kt = g.Teil("ellbogen")
	g.platte(kt, f, l_ober - 0.06, l_ober + 0.05, A + 0.01, nu=10, nw=32, w_von=ell - 1.6, w_bis=ell + 1.6,
		extra=lambda s, w: 0.018 * math.exp(-((s - l_ober + 0.005) / 0.03) ** 2) * math.cos(g.wdiff(w, ell) / 2) ** 2)
	o = kt.objekt(30)
	g.dicke(o, 0.0025, -1.0)
	teile.append(o)
	teile.append(r.objekt())
	return teile


def schwer_brust_arme(K):
	teile = []
	for seite in (1, -1):
		teile += _schulter(K, seite)
		teile += _oberarm(K, seite)
	return teile


# ---------------------------------------------------------------- Wams / Gambeson (Grundlage für alle Klassen)


def wams_feld(K, z0=0.50):
	"""Rumpf ab z0 abwärts (z0 < 0.5 für Roben bis zum Knöchel; s bleibt z - ZW)."""
	def bau():
		namen = ["Hips", "Spine", "Chest", "UpperChest", "Shoulder", "Neck", "UpperLeg"] + (["LowerLeg"] if z0 < 0.5 else [])
		bvh = K.bvh(namen)
		pk = ([(0, 0.0, z0)] if z0 < 0.5 else []) + [(0, 0.0, 0.50), (0, 0.0, 0.80), (0, -0.01, 1.62)]
		a = g.Achse(pk)
		f = g.Feld(bvh, a, ringe=int(110 * a.laenge() / 1.12), seg=72, konvex_anteil=0.7 if z0 >= 0.5 else 1.0, glatt=(4, 3),
			s0=0.0)
		f.versatz = 0.5 - z0
		return f
	f = _cache(K, ("wams", z0), bau)
	return f if z0 >= 0.5 else _Verschoben(f, 0.5 - z0)


class _Verschoben:
	"""Feld, dessen s um d verschoben ist (damit s = z - ZW überall gilt)."""

	def __init__(self, f, d):
		self.f, self.d = f, d
		self.achse = _VerschobeneAchse(f.achse, d)

	def punkt(self, s, w, extra=0.0):
		return self.f.punkt(s + self.d, w, extra)

	def normale(self, s, w, extra=0.0):
		return self.f.normale(s + self.d, w, extra)

	def radius(self, s, w):
		return self.f.radius(s + self.d, w)


class _VerschobeneAchse:
	def __init__(self, a, d):
		self.a, self.d = a, d

	def punkt(self, s):
		return self.a.punkt(s + self.d)

	def rahmen(self, s):
		return self.a.rahmen(s + self.d)

	def laenge(self):
		return self.a.laenge() - self.d


ZW = 0.50   # s = z - ZW auf der Wamsachse


def wams(K, material="stoff", abstand=0.012, unten_z=0.66, kragen_z=1.56, aermel_bis=0.92, steppung=0.0,
		weite=0.05, name="wams", aermel_abstand=None, offen=0.0, puff=0.0, manschette=0.0, z0=0.50, rock_ab=0.95,
		aermel_material=None, extra_fn=None):
	"""Rumpf mit Ärmeln. aermel_bis: Anteil der Armlänge (0 = Schulter, 1 = Handgelenk).
	weite: zusätzliche Weite des Rocks unten (m). steppung: Tiefe der Steppnähte (m)."""
	f = wams_feld(K, z0)
	teile = []
	def extra(s, w):
		e = 0.0
		z = s + ZW
		# Rock weitet sich unterhalb der Hüfte
		e += weite * g.weich(-z, -rock_ab, -max(z0, unten_z) - 0.0)
		if extra_fn:
			e += extra_fn(s, w)
		# Brust weniger eng, Bauch etwas weiter
		if steppung > 0:
			e -= steppung * abs(math.sin(w * 9)) ** 0.3 * 0.0 + steppung * (1 - abs(math.cos(w * 9))) ** 6
		return e
	t = g.Teil(name)
	if offen > 0:
		g.platte(t, f, unten_z - ZW, kragen_z - ZW, abstand, nu=56, nw=96, extra=extra, material_name=material,
			w_von=offen, w_bis=2 * PI - offen)
	else:
		g.platte(t, f, unten_z - ZW, kragen_z - ZW, abstand, nu=56, nw=96, extra=extra, material_name=material)
	o = t.objekt(60)
	g.dicke(o, 0.004, -1.0)
	g.verringern(o, 5000)
	teile.append(o)
	# Ärmel
	aa = abstand if aermel_abstand is None else aermel_abstand
	for seite in ((1, -1) if aermel_bis > 0 else ()):
		fa, l_ober, l_ges = arm_feld(K, seite, konvex=0.5)
		at = g.Teil(name + "_aermel")
		def aex(s, w, l_ober=l_ober, l_ges=l_ges):
			e = 0.0
			if puff > 0:
				e += puff * math.sin(min(1.0, max(0.0, s / (l_ges * aermel_bis))) * PI) ** 1.5
			if manschette > 0:
				e += manschette * g.weich(s, l_ges * aermel_bis - 0.08, l_ges * aermel_bis)
			if steppung > 0:
				e -= steppung * (1 - abs(math.cos(w * 5))) ** 6
			return e
		g.platte(at, fa, -0.02, l_ges * aermel_bis, aa, nu=32, nw=40, extra=aex, material_name=aermel_material or material)
		o = at.objekt(60)
		g.dicke(o, 0.004, -1.0)
		g.verringern(o, 1600)
		teile.append(o)
	return teile, f


# ---------------------------------------------------------------- Kopf


def kopf_feld(K, huelle=10, mitte=(0, -0.045, 1.65)):
	return _cache(K, ("kopf", huelle, tuple(mitte)), lambda: _kopf_feld(K, huelle, mitte))


def _kopf_feld(K, huelle=10, mitte=(0, -0.045, 1.65)):
	bvh = K.bvh(["Head", "Neck"], 0.4)
	return g.Kugelfeld(bvh, Vector(mitte), Vector((0, 0, 1)), ringe=64, seg=96, r_max=0.35, phi_max=2.5, huelle=huelle,
		glatt=(3, 3))


def schwer_kopf(K):
	f = kopf_feld(K)
	teile = []
	A = 0.024
	# Kamm über den Scheitel (vorne nach hinten)
	def kamm(s, w):
		return 0.006 * math.exp(-(math.sin(w) * math.sin(s) / 0.05) ** 2) * g.weich(-s, -1.9, -1.0)
	# Schnauze des Visiers
	def schnauze(s, w):
		return 0.045 * math.exp(-(g.wdiff(w, 0) / 0.55) ** 2) * math.exp(-((s - 1.62) / 0.28) ** 2)
	SPALT_O, SPALT_U = 1.20, 1.29
	unten = lambda w: 2.28 + 0.06 * math.cos(g.wdiff(w, PI) / 2) ** 2
	# Glocke
	t = g.Teil("helm")
	g.platte(t, f, 0.0, SPALT_O, A, nu=30, nw=96, extra=kamm)
	g.platte(t, f, SPALT_O, unten, A, nu=24, nw=60, w_von=0.95, w_bis=2 * PI - 0.95, extra=kamm)
	o = t.objekt(30)
	g.dicke(o, 0.003, -1.0)
	teile.append(o)
	# Visier
	v = g.Teil("visier")
	vu = lambda w: 2.36
	ex = lambda s, w: 0.008 + schnauze(s, w)
	g.platte(v, f, SPALT_U, vu, A, nu=26, nw=40, w_von=-1.08, w_bis=1.08, extra=ex)
	o = v.objekt(30)
	g.dicke(o, 0.003, -1.0)
	teile.append(o)
	r = g.Teil("helm_rand")
	pts, _ = g.rand_punkte(f, unten, A, w_von=0.95, w_bis=2 * PI - 0.95, n=80, extra=kamm)
	g.zug(r, pts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, SPALT_O, A, w_von=-0.95, w_bis=0.95, n=40, extra=kamm)
	g.zug(r, pts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, SPALT_U, A, w_von=-1.08, w_bis=1.08, n=40, extra=ex)
	g.zug(r, pts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, vu, A, w_von=-1.08, w_bis=1.08, n=40, extra=ex)
	g.zug(r, pts, 0.004, "rand")
	# Visierbolzen und Atemlöcher
	for w in (PI / 2, 3 * PI / 2):
		g.niete(r, f.punkt(1.3, w, A + 0.008), f.normale(1.3, w, A + 0.008), 0.009)
	for i in range(-3, 4):
		for j in range(2):
			s, w = 1.72 + 0.07 * j, (0.42 + 0.09 * j) * (1 if i > 0 else -1) + i * 0.0
			if i == 0:
				continue
			w = (0.36 + abs(i) * 0.08) * (1 if i > 0 else -1)
			s = 1.62 + 0.06 * j
			g.niete(r, f.punkt(s, w, A + ex(s, w) + 0.0005), f.normale(s, w, A + ex(s, w)), 0.0035, "leder_dunkel")
	teile.append(r.objekt())
	return g.vereinen(teile, "iron_schwer_kopf")


# ---------------------------------------------------------------- Hände


HAND = ["Hand", "Thumb", "Index", "Middle", "Ring", "Little"]


def handschuh(K, seite, material="leder", abstand=0.003, stulpe=0.07):
	"""Handschuh aus der aufgeblasenen Hand, endet 'stulpe' Meter hinter dem Handgelenk."""
	n = "Left" if seite > 0 else "Right"
	h = K.gelenk(n + "Hand")
	e = K.gelenk(n + "LowerArm")
	d = (h - e).normalized()
	namen = [n + x for x in HAND] + [n + "LowerArm"]
	behalten = lambda p: (p - h).dot(d) > -stulpe
	ob = g.huelle_aus_koerper(K, namen, 0.5, abstand, "handschuh", material, behalten=behalten)
	g.schneiden(ob, h - d * stulpe, -d)
	g.dicke(ob, 0.002, -1.0)
	return ob


def finger_achsen(K, seite):
	n = "Left" if seite > 0 else "Right"
	out = {}
	for f in ("Index", "Middle", "Ring", "Little", "Thumb"):
		glieder = ["Metacarpal", "Proximal", "Intermediate", "Distal"] if f == "Thumb" else ["Proximal", "Intermediate", "Distal"]
		pts = [K.gelenk(n + f + gl) for gl in glieder if (n + f + gl) in K.knochen]
		pts.append(K.gelenk(n + f + "Distal", ende=True))
		out[f] = pts
	return out


def schwer_haende(K):
	teile = []
	for seite in (1, -1):
		n = "Left" if seite > 0 else "Right"
		teile.append(handschuh(K, seite, "leder_dunkel", 0.003, 0.09))
		fa, l_ober, l_ges = arm_feld(K, seite)
		# Unterarmröhre
		t = g.Teil("unterarm")
		A = 0.016
		von, bis = l_ober + 0.05, l_ges - 0.045
		g.platte(t, fa, von, bis, A, nu=16, nw=48)
		o = t.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teiles = [o]
		r = g.Teil("unterarm_rand")
		for s in (von, bis):
			pts, zu = g.rand_punkte(fa, s, A, n=64)
			g.zug(r, pts, 0.004, "rand", zu=zu)
		# Stulpe (glockenförmig über dem Handgelenk)
		st = g.Teil("stulpe")
		glocke = lambda s, w: 0.016 * g.weich(s, l_ges - 0.06, l_ges + 0.01)
		g.platte(st, fa, l_ges - 0.065, l_ges + 0.012, A + 0.004, nu=10, nw=48, extra=glocke)
		o = st.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teiles.append(o)
		pts, zu = g.rand_punkte(fa, l_ges + 0.012, A + 0.004, n=64, extra=glocke)
		g.zug(r, pts, 0.004, "rand", zu=zu)
		# Handrücken und Fingerschuppen
		achsen = finger_achsen(K, seite)
		hand_bvh = K.bvh([n + x for x in HAND], 0.4)
		h0 = K.gelenk(n + "Hand")
		mitte_finger = K.gelenk(n + "MiddleProximal")
		ha = g.Achse([h0, mitte_finger + (mitte_finger - h0).normalized() * 0.01])
		hf = g.Feld(hand_bvh, ha, ringe=20, seg=48, r_max=0.12, konvex_anteil=1.0, glatt=(2, 2))
		# Handrücken: Richtung finden, in der der Rücken liegt (Handrücken zeigt bei A-Pose nach außen-oben)
		ruecken = _handruecken_winkel(K, seite, ha)
		for k in range(3):
			a0 = 0.0 + 0.032 * k
			pt = g.Teil("handplatte")
			g.platte(pt, hf, a0, a0 + 0.04, 0.007 + 0.002 * k, nu=5, nw=16, w_von=ruecken - 1.1, w_bis=ruecken + 1.1)
			o = pt.objekt(30)
			g.dicke(o, 0.002, -1.0)
			teiles.append(o)
		for fname, pts_f in achsen.items():
			fa2 = g.Feld(K.bvh([n + fname], 0.5), g.Achse(pts_f), ringe=24, seg=24, r_max=0.05, konvex_anteil=1.0, glatt=(1, 1))
			rw = _handruecken_winkel(K, seite, g.Achse(pts_f))
			L = fa2.achse.laenge()
			stueck = 4 if fname != "Thumb" else 3
			for k in range(stueck):
				a0 = L * (0.08 + 0.85 * k / stueck)
				pt = g.Teil("fingerschuppe")
				g.platte(pt, fa2, a0, a0 + L * 0.85 / stueck + 0.004, 0.004, nu=3, nw=8, w_von=rw - 1.2, w_bis=rw + 1.2)
				o = pt.objekt(30)
				g.dicke(o, 0.0015, -1.0)
				teiles.append(o)
		teiles.append(r.objekt())
		teile += teiles
	return g.vereinen(teile, "iron_schwer_haende")


def _handruecken_winkel(K, seite, achse):
	"""Winkel w (im Rahmen der Achse), in den der Handrücken zeigt: Normale des Handrückens
	≈ Kreuzprodukt aus Fingerrichtung und Querrichtung Zeigefinger -> kleiner Finger."""
	n = "Left" if seite > 0 else "Right"
	quer = K.gelenk(n + "LittleProximal") - K.gelenk(n + "IndexProximal")
	lang = K.gelenk(n + "MiddleProximal") - K.gelenk(n + "Hand")
	nr = lang.cross(quer).normalized() * (-1 if seite > 0 else 1)
	c, t, nn, b = achse.rahmen(achse.laenge() * 0.5)
	return math.atan2(nr.dot(b), nr.dot(nn))


# ---------------------------------------------------------------- Beine


def bein_achse(K, seite=1):
	n = "Left" if seite > 0 else "Right"
	h = K.gelenk(n + "UpperLeg")
	k = K.gelenk(n + "LowerLeg")
	f = K.gelenk(n + "Foot")
	return g.Achse([h + Vector((0, 0, 0.06)), h, k, f]), 0.06 + (h - k).length, 0.06 + (h - k).length + (k - f).length


def bein_feld(K, seite=1, konvex=1.0, glatt=(3, 2)):
	return _cache(K, ("bein", seite, konvex, glatt), lambda: _bein_feld(K, seite, konvex, glatt))


def _bein_feld(K, seite=1, konvex=1.0, glatt=(3, 2)):
	achse, l_knie, l_ges = bein_achse(K, seite)
	n = "Left" if seite > 0 else "Right"
	bvh = K.bvh([n + "UpperLeg", n + "LowerLeg"], 0.5)
	return g.Feld(bvh, achse, ringe=90, seg=56, r_max=0.25, konvex_anteil=konvex, glatt=glatt), l_knie, l_ges


def hose(K, material="stoff", abstand=0.006, unten=1.0, name="hose", bund_z=1.02, konvex=0.4, bein_extra=None):
	"""Hose: zwei Beinröhren und ein Becken-Stück. unten: Anteil Knie..Knöchel (1 = bis Knöchel)."""
	teile = []
	f = wams_feld(K)
	t = g.Teil(name)
	g.platte(t, f, 0.86 - ZW, bund_z - ZW, abstand + 0.004, nu=14, nw=96, material_name=material)
	o = t.objekt(60)
	g.dicke(o, 0.004, -1.0)
	teile.append(o)
	for seite in (1, -1):
		fb, l_knie, l_ges = bein_feld(K, seite, konvex)
		bt = g.Teil(name + "_bein")
		ex = (lambda s, w, l_knie=l_knie, l_ges=l_ges: bein_extra(s, w, l_knie, l_ges)) if bein_extra else None
		g.platte(bt, fb, 0.04, l_knie + (l_ges - l_knie) * unten - 0.03, abstand, nu=44, nw=40, material_name=material,
			extra=ex)
		o = bt.objekt(60)
		g.dicke(o, 0.004, -1.0)
		g.verringern(o, 2400)
		teile.append(o)
	return teile


def schwer_beine(K, hose_material="stoff", name="iron_schwer_beine"):
	teile = hose(K, hose_material, 0.006)
	for seite in (1, -1):
		fb, l_knie, l_ges = bein_feld(K, seite)
		r = g.Teil("bein_rand")
		# Diechlinge (Oberschenkel vorne und seitlich)
		A = 0.016
		t = g.Teil("diechling")
		g.platte(t, fb, 0.17, l_knie - 0.06, A, nu=20, nw=40, w_von=-2.0, w_bis=2.0)
		o = t.objekt(30)
		g.dicke(o, 0.003, -1.0)
		teile.append(o)
		pts, _ = g.rand_punkte(fb, 0.17, A, w_von=-2.0, w_bis=2.0, n=40)
		g.zug(r, pts, 0.004, "rand")
		g.nieten_reihe(r, fb, lambda w: 0.19, A, [-1.6, -0.8, 0.0, 0.8, 1.6], 0.005)
		for k in range(2):
			a0 = 0.11 + 0.035 * k
			lt = g.Teil("diechling_lamelle")
			g.platte(lt, fb, a0, a0 + 0.05, A + 0.004 - 0.003 * k, nu=4, nw=30, w_von=-1.7, w_bis=1.7)
			o = lt.objekt(30)
			g.dicke(o, 0.0025, -1.0)
			teile.append(o)
			pts, _ = g.rand_punkte(fb, a0, A + 0.004 - 0.003 * k, w_von=-1.7, w_bis=1.7, n=30)
			g.zug(r, pts, 0.003, "rand")
		# Kniekachel mit Seitenflügel
		kt = g.Teil("knie")
		buckel = lambda s, w: 0.022 * math.exp(-((s - l_knie) / 0.04) ** 2) * math.cos(min(g.wdiff(w, 0), PI / 2)) ** 2
		g.platte(kt, fb, l_knie - 0.075, l_knie + 0.07, A + 0.006, nu=16, nw=36, w_von=-1.9, w_bis=1.9, extra=buckel)
		o = kt.objekt(30)
		g.dicke(o, 0.003, -1.0)
		teile.append(o)
		for s in (l_knie - 0.075, l_knie + 0.07):
			pts, _ = g.rand_punkte(fb, s, A + 0.006, w_von=-1.9, w_bis=1.9, n=36, extra=buckel)
			g.zug(r, pts, 0.004, "rand")
		seite_w = PI / 2 if seite > 0 else 3 * PI / 2   # außen
		g.niete(r, fb.punkt(l_knie, seite_w, A + 0.012), fb.normale(l_knie, seite_w, A + 0.012), 0.012)
		# Beinröhre (Schiene), ganz herum
		st = g.Teil("schiene")
		grat = lambda s, w: 0.006 * math.exp(-(g.wdiff(w, 0) / 0.25) ** 2)
		g.platte(st, fb, l_knie + 0.055, l_ges - 0.07, A - 0.002, nu=36, nw=56, extra=grat)
		o = st.objekt(30)
		g.dicke(o, 0.003, -1.0)
		teile.append(o)
		for s in (l_knie + 0.055, l_ges - 0.07):
			pts, zu = g.rand_punkte(fb, s, A - 0.002, n=64, extra=grat)
			g.zug(r, pts, 0.004, "rand", zu=zu)
		teile.append(r.objekt())
	return g.vereinen(teile, name)


# ---------------------------------------------------------------- Füße


def fuss_achse(K, seite=1):
	"""Gerade Achse von hinter der Ferse bis vor die Zehen, Winkel 0 = oben."""
	n = "Left" if seite > 0 else "Right"
	a = K.gelenk(n + "Foot")
	c = K.gelenk(n + "Toes", ende=True)
	ferse = Vector((a.x, a.y + 0.075, 0.045))
	spitze = Vector((c.x, c.y - 0.04, 0.025))
	return g.Achse([ferse, spitze], vorne=g.OBEN)


def fuss_feld(K, seite):
	return _cache(K, ("fuss", seite), lambda: _fuss_feld(K, seite))


def _fuss_feld(K, seite):
	n = "Left" if seite > 0 else "Right"
	bvh = K.bvh_bereich(lambda x, y, z: (z < 0.11) & (x * seite > 0.04), ("fuss", seite))
	return g.Feld(bvh, fuss_achse(K, seite), ringe=40, seg=48, r_max=0.15,
		konvex_anteil=1.0, glatt=(3, 2))


def stiefel(K, seite, material="leder", abstand=0.006, schaft=0.16, sohle=0.008, weite=0.0, name="stiefel"):
	"""Stiefel: Fußröhre und Schaft vereint (Voxel), geglättet, oben gerade abgeschnitten, Sohle flach.
	weite: zusätzliche Weite am oberen Schaftrand (Stulpe)."""
	n = "Left" if seite > 0 else "Right"
	knoechel = K.gelenk(n + "Foot")
	ff = fuss_feld(K, seite)
	t = g.Teil("fuss")
	g.platte(t, ff, 0.0, ff.achse.laenge(), lambda s, w: abstand + 0.004 * g.weich(s, ff.achse.laenge() * 0.6, ff.achse.laenge()), nu=30, nw=48, kappe_bis=True, kappe_von=True)
	fb, l_knie, l_ges = bein_feld(K, seite, konvex=1.0)
	top = l_ges - schaft - 0.03
	ex = lambda s, w: weite * g.weich(-s, -(l_ges - schaft * 0.4), -top)
	g.platte(t, fb, top, l_ges + 0.02, abstand, nu=20, nw=56, extra=ex, kappe_von=True, kappe_bis=True)
	ob = t.objekt()
	# Deckel auf beiden Röhren für ein geschlossenes Volumen
	g.anwenden(ob, "REMESH", mode="VOXEL", voxel_size=0.005)
	g.anwenden(ob, "SMOOTH", factor=0.5, iterations=2)
	g.schneiden(ob, knoechel + Vector((0, 0, schaft)), Vector((0, 0, 1)))
	for v in ob.data.vertices:
		if v.co.z < sohle:
			v.co.z = -0.004 if v.co.z < 0.0035 else v.co.z
	g.material_setzen(ob, material)
	g.verringern(ob, 2500)
	g.glatt(ob, 70)
	g.dicke(ob, 0.003, -1.0)
	# Sohle als eigene Platte
	return ob


def schwer_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(stiefel(K, seite, "leder_dunkel", 0.009, 0.12))
		ff = fuss_feld(K, seite)
		fa = ff.achse
		L = fa.laenge()
		r = g.Teil("schuh_rand")
		# Spannplatten: vom Knöchel über den Rist bis zur Kappe
		stuecke = 6
		for k in range(stuecke):
			a0 = 0.04 + (L - 0.08) * k / stuecke
			a1 = a0 + (L - 0.08) / stuecke + 0.008
			pt = g.Teil("sabaton")
			ab = 0.014 + 0.0015 * k
			g.platte(pt, ff, a0, a1, ab, nu=4, nw=24, w_von=-1.45, w_bis=1.45)
			o = pt.objekt(30)
			g.dicke(o, 0.0025, -1.0)
			teile.append(o)
			pts, _ = g.rand_punkte(ff, a0, ab, w_von=-1.45, w_bis=1.45, n=24)
			g.zug(r, pts, 0.0025, "rand")
		# Zehenkappe
		kp = g.Teil("kappe")
		a0 = 0.04 + (L - 0.08)
		g.platte(kp, ff, a0 - 0.002, L, 0.014, nu=10, nw=32, w_von=-1.8, w_bis=1.8)
		o = kp.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teiles = [o]
		# Knöchelschutz (Ring über dem Stiefel)
		fb, l_knie, l_ges = bein_feld(K, seite)
		kr = g.Teil("knoechel")
		g.platte(kr, fb, l_ges - 0.10, l_ges - 0.045, 0.011, nu=6, nw=56)
		o = kr.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teiles.append(o)
		pts, zu = g.rand_punkte(fb, l_ges - 0.10, 0.011, n=56)
		g.zug(r, pts, 0.003, "rand", zu=zu)
		teiles.append(r.objekt())
		teile += teiles
	return g.vereinen(teile, "iron_schwer_fuesse")


# ================================================================ MITTEL (Kette und Leder)


def mittel_kopf(K):
	f = kopf_feld(K)
	teile = []
	# Kettenhaube: Kopf, Seiten, Hals, Kinn; Gesicht frei
	A = 0.012
	t = g.Teil("kettenhaube")
	g.platte(t, f, 0.0, 1.25, A, nu=24, nw=96, material_name="kette")
	g.platte(t, f, 1.25, 2.42, A, nu=26, nw=60, w_von=0.85, w_bis=2 * PI - 0.85, material_name="kette")
	g.platte(t, f, 2.08, 2.42, A, nu=8, nw=24, w_von=-0.87, w_bis=0.87, material_name="kette")
	o = t.objekt(60)
	g.dicke(o, 0.003, -1.0)
	teile.append(o)
	# Kettenkragen über die Schultern
	fr = rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	kt = g.Teil("kettenkragen")
	flare = lambda s, w: 0.02 * g.weich(-s, -0.66, -0.56)
	kragen_u = tabelle([(0, 0.56), (0.9, 0.6), (PI / 2, 0.58), (2.3, 0.6), (PI, 0.57)])
	g.platte(kt, fr, kragen_u, 0.78, 0.014, nu=16, nw=96, extra=flare, material_name="kette")
	o = kt.objekt(60)
	g.dicke(o, 0.003, -1.0)
	teiles = [o]
	r = g.Teil("kragen_rand")
	pts, zu = g.rand_punkte(fr, kragen_u, 0.014, n=120, extra=flare)
	g.zug(r, pts, 0.003, "leder", zu=zu, flach=0.5)
	# Lederrand am Gesicht
	pts = [f.punkt(s, w, A + 0.002) for s, w in
		[(1.25, 0.85 + (2 * PI - 1.7) * 0 )]]
	gesicht = []
	for k in range(25):
		w = -0.86 + 1.72 * k / 24
		gesicht.append(f.punkt(2.08, w, A + 0.001))
	for k in range(30):
		s = 2.08 - (2.08 - 1.25) * k / 29
		gesicht.insert(0, f.punkt(s, -0.86, A + 0.001))
		gesicht.append(f.punkt(s, 0.86, A + 0.001))
	g.zug(r, gesicht, 0.004, "leder", flach=0.6)
	# Spitzhelm mit Nasal
	H = 0.03
	spitze = lambda s, w: 0.05 * max(0.0, 1 - s / 0.75) ** 2
	ht = g.Teil("spitzhelm")
	g.platte(ht, f, 0.0, 1.2, H, nu=28, nw=72, extra=spitze)
	o = ht.objekt(30)
	g.dicke(o, 0.003, -1.0)
	teiles.append(o)
	pts, zu = g.rand_punkte(f, 1.2, H, n=96, extra=spitze)
	g.zug(r, pts, 0.008, "rand", zu=zu, flach=0.4)
	nasal = [f.punkt(1.18 + 0.4 * k / 12, 0.0, H + 0.004 + 0.002 * k / 12) for k in range(13)]
	g.zug(r, nasal, 0.011, "platte", flach=0.25, aussen=lambda p: (p - f.c).normalized())
	for k in range(4):
		w = k * PI / 2
		bogen = [f.punkt(1.18 * (1 - j / 14), w, H + spitze(1.18 * (1 - j / 14), w) + 0.001) for j in range(15)]
		g.zug(r, bogen, 0.006, "rand", flach=0.35, aussen=lambda p: (p - f.c).normalized())
	for k in range(16):
		w = k * 2 * PI / 16
		g.niete(r, f.punkt(1.15, w, H + 0.004), f.normale(1.15, w, H), 0.004)
	teiles.append(r.objekt())
	return g.vereinen(teile + teiles, "iron_mittel_kopf")


def guertel(K, z=1.0, breite=0.045, abstand=0.03, material="leder", schnalle=True, feld=None):
	f = feld or wams_feld(K)
	t = g.Teil("guertel")
	s = z - ZW
	g.platte(t, f, s - breite / 2, s + breite / 2, abstand, nu=3, nw=96, material_name=material)
	o = t.objekt(40)
	g.dicke(o, 0.004, -1.0)
	teile = [o]
	if schnalle:
		r = g.Teil("schnalle")
		p0 = f.punkt(s, 0.0, abstand + 0.006)
		n0 = f.normale(s, 0.0, abstand)
		ring = []
		for k in range(17):
			a = 2 * PI * k / 16
			ring.append(p0 + Vector((math.cos(a) * 0.026, 0, math.sin(a) * 0.022)))
		g.zug(r, ring[:-1], 0.0035, "rand", zu=True)
		g.zug(r, [p0 + Vector((0, 0, -0.022)), p0 + Vector((0, -0.002, 0.022))], 0.0025, "rand")
		teile.append(r.objekt())
	return teile


def mittel_brust(K):
	teile = []
	unter, _ = wams(K, "stoff", 0.006, unten_z=0.70, kragen_z=1.52, aermel_bis=1.0, steppung=0.003, weite=0.035,
		aermel_abstand=0.004)
	teile += unter
	kette, _ = wams(K, "kette", 0.014, unten_z=0.62, kragen_z=1.49, aermel_bis=0.52, weite=0.06, name="kettenhemd",
		aermel_abstand=0.011)
	teile += kette
	teile += guertel(K, 1.0, 0.05, 0.03)
	# Lederschultern mit Nieten
	for seite in (1, -1):
		f = schulter_feld(K, seite)
		aussen = PI / 2 if seite > 0 else 3 * PI / 2
		bis = lambda w: 0.95 + 0.55 * (1 - (g.wdiff(w, aussen) / PI) ** 2)
		t = g.Teil("lederschulter")
		g.platte(t, f, 0.0, bis, 0.03, nu=20, nw=72, material_name="leder")
		o = t.objekt(40)
		g.dicke(o, 0.006, -1.0)
		teile.append(o)
		r = g.Teil("schulter_nieten")
		pts, zu = g.rand_punkte(f, bis, 0.03, n=120)
		g.zug(r, pts, 0.004, "leder_dunkel", zu=zu, flach=0.6)
		for k in range(3):
			g.nieten_reihe(r, f, lambda w, k=k: bis(w) - 0.1 - 0.17 * k, 0.03,
				[aussen + (j - 3) * (0.42 - 0.08 * k) for j in range(7)], 0.0045)
		teile.append(r.objekt())
	return g.vereinen(teile, "iron_mittel_brust")


def armschiene_leder(K, seite, abstand=0.01, platte=True):
	fa, l_ober, l_ges = arm_feld(K, seite)
	von, bis = l_ober + 0.07, l_ges - 0.02
	t = g.Teil("armschiene")
	g.platte(t, fa, von, bis, abstand, nu=16, nw=48, material_name="leder")
	o = t.objekt(40)
	g.dicke(o, 0.004, -1.0)
	teile = [o]
	r = g.Teil("armschiene_naht")
	for s in (von, bis):
		pts, zu = g.rand_punkte(fa, s, abstand, n=48)
		g.zug(r, pts, 0.0035, "leder_dunkel", zu=zu, flach=0.6)
	# Schnürung innen (Richtung Körper)
	innen = PI / 2 if seite > 0 else 3 * PI / 2
	for k in range(6):
		s = von + 0.02 + (bis - von - 0.04) * k / 5
		a = fa.punkt(s, innen - 0.25, abstand + 0.002)
		b = fa.punkt(s + 0.025, innen + 0.25, abstand + 0.002)
		g.zug(r, [a, b], 0.0018, "leder_dunkel")
	if platte:
		aussen = PI / 2 if seite < 0 else 3 * PI / 2
		pt = g.Teil("armplatte")
		g.platte(pt, fa, von + 0.015, bis - 0.015, abstand + 0.005, nu=10, nw=10, w_von=aussen - 0.55, w_bis=aussen + 0.55)
		o = pt.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teile.append(o)
		for s in (von + 0.03, bis - 0.03):
			g.nieten_reihe(r, fa, s, abstand + 0.006, [aussen - 0.4, aussen + 0.4], 0.004)
	teile.append(r.objekt())
	return teile


def mittel_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(handschuh(K, seite, "leder", 0.003, 0.05))
		teile += armschiene_leder(K, seite, 0.011, True)
		# Eisenplatte auf dem Handrücken
		n = "Left" if seite > 0 else "Right"
		h0 = K.gelenk(n + "Hand")
		mf = K.gelenk(n + "MiddleProximal")
		ha = g.Achse([h0, mf + (mf - h0).normalized() * 0.01])
		hf = g.Feld(K.bvh([n + x for x in HAND], 0.4), ha, ringe=20, seg=48, r_max=0.12, konvex_anteil=1.0, glatt=(2, 2))
		rw = _handruecken_winkel(K, seite, ha)
		pt = g.Teil("handplatte")
		g.platte(pt, hf, 0.012, ha.laenge() - 0.005, 0.008, nu=6, nw=14, w_von=rw - 1.0, w_bis=rw + 1.0)
		o = pt.objekt(30)
		g.dicke(o, 0.002, -1.0)
		teile.append(o)
	return g.vereinen(teile, "iron_mittel_haende")


def mittel_beine(K):
	teile = hose(K, "leder_dunkel", 0.006)
	for seite in (1, -1):
		fb, l_knie, l_ges = bein_feld(K, seite)
		r = g.Teil("bein_teile")
		# Lederschutz auf dem Oberschenkel (vorne, außen)
		t = g.Teil("oberschenkelleder")
		g.platte(t, fb, 0.14, l_knie - 0.07, 0.013, nu=14, nw=28, w_von=-1.5, w_bis=1.5, material_name="leder")
		o = t.objekt(40)
		g.dicke(o, 0.005, -1.0)
		teile.append(o)
		for k in range(4):
			s = 0.17 + (l_knie - 0.27) * k / 3
			g.nieten_reihe(r, fb, s, 0.014, [-1.2, -0.6, 0.0, 0.6, 1.2], 0.004)
		pts, _ = g.rand_punkte(fb, 0.14, 0.013, w_von=-1.5, w_bis=1.5, n=28)
		g.zug(r, pts, 0.004, "leder_dunkel", flach=0.6)
		# Eiserne Kniekachel
		kt = g.Teil("knie")
		buckel = lambda s, w: 0.02 * math.exp(-((s - l_knie) / 0.035) ** 2) * math.cos(min(g.wdiff(w, 0), PI / 2)) ** 2
		g.platte(kt, fb, l_knie - 0.06, l_knie + 0.055, 0.016, nu=14, nw=28, w_von=-1.4, w_bis=1.4, extra=buckel)
		o = kt.objekt(30)
		g.dicke(o, 0.003, -1.0)
		teile.append(o)
		for s in (l_knie - 0.06, l_knie + 0.055):
			pts, _ = g.rand_punkte(fb, s, 0.016, w_von=-1.4, w_bis=1.4, n=28, extra=buckel)
			g.zug(r, pts, 0.0035, "rand")
		# Riemen hinter dem Knie
		for s in (l_knie - 0.035, l_knie + 0.035):
			pts, _ = g.rand_punkte(fb, s, 0.009, w_von=1.4, w_bis=2 * PI - 1.4, n=24)
			g.zug(r, pts, 0.006, "leder_dunkel", flach=0.35, aussen=lambda p: Vector((0, 1, 0)))
		teile.append(r.objekt())
	return g.vereinen(teile, "iron_mittel_beine")


def mittel_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(stiefel(K, seite, "leder", 0.009, 0.30))
		ff = fuss_feld(K, seite)
		L = ff.achse.laenge()
		pt = g.Teil("kappe")
		g.platte(pt, ff, L - 0.07, L, 0.016, nu=8, nw=24, w_von=-1.6, w_bis=1.6)
		o = pt.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teile.append(o)
		# Schienbeinplatte vorne
		fb, l_knie, l_ges = bein_feld(K, seite)
		st = g.Teil("schienbein")
		grat = lambda s, w: 0.005 * math.exp(-(g.wdiff(w, 0) / 0.2) ** 2)
		g.platte(st, fb, l_ges - 0.27, l_ges - 0.08, 0.019, nu=12, nw=14, w_von=-0.8, w_bis=0.8, extra=grat)
		o = st.objekt(30)
		g.dicke(o, 0.0025, -1.0)
		teile.append(o)
		r = g.Teil("riemen")
		for s in (l_ges - 0.24, l_ges - 0.11):
			pts, zu = g.rand_punkte(fb, s, 0.019, w_von=0.8, w_bis=2 * PI - 0.8, n=40)
			g.zug(r, pts, 0.007, "leder_dunkel", flach=0.35)
			g.nieten_reihe(r, fb, s, 0.02, [-0.6, 0.6], 0.0045)
		teile.append(r.objekt())
	return g.vereinen(teile, "iron_mittel_fuesse")


# ================================================================ LEICHT (Stoff und Leder)


def leicht_kopf(K):
	"""Gugel: Kapuze mit Schulterkragen und Zipfel, Gesicht frei."""
	f = kopf_feld(K, huelle=14)
	A = 0.022
	zipfel = lambda s, w: 0.05 * math.exp(-(g.wdiff(w, PI) / 0.5) ** 2) * math.exp(-((s - 0.75) / 0.35) ** 2)
	weit = lambda s, w: A + zipfel(s, w) + 0.012 * g.weich(s, 1.6, 2.4)
	t = g.Teil("gugel")
	g.platte(t, f, 0.0, 1.05, weit, nu=24, nw=96, material_name="stoff")
	g.platte(t, f, 1.05, 2.45, weit, nu=28, nw=60, w_von=0.95, w_bis=2 * PI - 0.95, material_name="stoff")
	g.platte(t, f, 2.3, 2.45, weit, nu=4, nw=24, w_von=-0.97, w_bis=0.97, material_name="stoff")
	o = t.objekt(60)
	g.dicke(o, 0.004, -1.0)
	teile = [o]
	# Schulterkragen
	fr = rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	kt = g.Teil("kragen")
	flare = lambda s, w: 0.025 + 0.03 * g.weich(-s, -0.68, -0.48)
	kragen_u = tabelle([(0, 0.44), (0.9, 0.5), (PI / 2, 0.52), (2.3, 0.5), (PI, 0.46)])
	g.platte(kt, fr, kragen_u, 0.79, 0.0, nu=20, nw=96, extra=flare, material_name="stoff")
	o = kt.objekt(60)
	g.dicke(o, 0.004, -1.0)
	teile.append(o)
	r = g.Teil("saum")
	pts, zu = g.rand_punkte(fr, kragen_u, 0.0, n=120, extra=lambda s, w: flare(s, w) + 0.002)
	g.zug(r, pts, 0.004, "stoff_akzent", zu=zu, flach=0.5)
	gesicht = []
	for k in range(25):
		w = -0.96 + 1.92 * k / 24
		gesicht.append(f.punkt(2.3, w, weit(2.3, w)))
	for k in range(36):
		s = 2.3 - (2.3 - 1.05) * k / 35
		gesicht.insert(0, f.punkt(s, -0.95, weit(s, -0.95)))
		gesicht.append(f.punkt(s, 0.95, weit(s, 0.95)))
	g.zug(r, gesicht, 0.006, "stoff_akzent", flach=0.7)
	teile.append(r.objekt())
	return g.vereinen(teile, "iron_leicht_kopf")


def leicht_brust(K):
	teile = []
	hemd, _ = wams(K, "futter", 0.006, unten_z=0.68, kragen_z=1.53, aermel_bis=1.0, steppung=0.0025, weite=0.05,
		aermel_abstand=0.005)
	teile += hemd
	# Lederweste ohne Ärmel
	f = rumpf_feld(K, glatt=(4, 3), konvex=0.85)
	oben = tabelle([(0, 0.62), (0.35, 0.66), (0.7, 0.69), (1.15, 0.53), (1.57, 0.5), (2.0, 0.53),
		(2.4, 0.69), (2.8, 0.7), (PI, 0.69)])
	unten = tabelle([(0, 0.04), (PI / 2, 0.08), (PI, 0.06)])
	vorne_offen = lambda w: g.wdiff(w, 0) > 0.06
	t = g.Teil("weste")
	weite = lambda s, w: 0.01 * g.weich(-s, -0.18, -0.02)
	g.platte(t, f, unten, oben, lambda s, w: 0.02 + weite(s, w), nu=40, nw=96, w_von=0.07, w_bis=2 * PI - 0.07,
		material_name="leder")
	o = t.objekt(50)
	g.dicke(o, 0.004, -1.0)
	teile.append(o)
	r = g.Teil("weste_naht")
	for fn in (oben, unten):
		pts, _ = g.rand_punkte(f, fn, 0.021, w_von=0.07, w_bis=2 * PI - 0.07, n=120, extra=weite)
		g.zug(r, pts, 0.003, "leder_dunkel", flach=0.6)
	# Schnürung vorne
	for k in range(7):
		s = 0.12 + 0.065 * k
		a = f.punkt(s, -0.07, 0.022)
		b = f.punkt(s + 0.03, 0.07, 0.022)
		c = f.punkt(s, 0.07, 0.022)
		d = f.punkt(s + 0.03, -0.07, 0.022)
		g.zug(r, [a, b], 0.0018, "leder_dunkel")
		g.zug(r, [c, d], 0.0018, "leder_dunkel")
	teile.append(r.objekt())
	teile += guertel(K, 0.96, 0.04, 0.032)
	return g.vereinen(teile, "iron_leicht_brust")


def leicht_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(handschuh(K, seite, "leder", 0.0028, 0.05))
		fa, l_ober, l_ges = arm_feld(K, seite, konvex=0.8)
		st = g.Teil("stulpe")
		glocke = lambda s, w: 0.016 * g.weich(-s, -(l_ges - 0.02), -(l_ges - 0.10))
		g.platte(st, fa, l_ges - 0.11, l_ges - 0.015, lambda s, w: 0.009 + glocke(s, w), nu=10, nw=48, material_name="leder")
		o = st.objekt(50)
		g.dicke(o, 0.003, -1.0)
		teile.append(o)
		r = g.Teil("stulpe_naht")
		pts, zu = g.rand_punkte(fa, l_ges - 0.11, 0.009, n=48, extra=glocke)
		g.zug(r, pts, 0.003, "leder_dunkel", zu=zu, flach=0.6)
		teile.append(r.objekt())
	return g.vereinen(teile, "iron_leicht_haende")


def leicht_beine(K):
	teile = hose(K, "stoff", 0.006, name="hose")
	for seite in (1, -1):
		fb, l_knie, l_ges = bein_feld(K, seite, konvex=0.6)
		# Wickelgamaschen (Lederbänder um das Schienbein)
		r = g.Teil("wickel")
		von, bis = l_knie + 0.06, l_ges - 0.05
		n = 9
		for k in range(n):
			s = von + (bis - von) * k / (n - 1)
			pts, zu = g.rand_punkte(fb, lambda w, s=s: s + 0.012 * math.sin(w), 0.012, n=48)
			g.zug(r, pts, 0.011, "leder", zu=zu, flach=0.3)
		# Knieflicken
		kt = g.Teil("knieflicken")
		g.platte(kt, fb, l_knie - 0.06, l_knie + 0.05, 0.009, nu=8, nw=16, w_von=-0.9, w_bis=0.9, material_name="leder")
		o = kt.objekt(50)
		g.dicke(o, 0.003, -1.0)
		teile.append(o)
		pts, _ = g.rand_punkte(fb, l_knie - 0.06, 0.0095, w_von=-0.9, w_bis=0.9, n=16)
		g.zug(r, pts, 0.002, "leder_dunkel")
		teile.append(r.objekt())
	return g.vereinen(teile, "iron_leicht_beine")


def leicht_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(stiefel(K, seite, "leder", 0.008, 0.20, weite=0.012))
		fb, l_knie, l_ges = bein_feld(K, seite)
		# Umschlag oben
		n = "Left" if seite > 0 else "Right"
		knoechel_z = K.gelenk(n + "Foot").z
		s_oben = l_ges - 0.2 - 0.0
		u = g.Teil("umschlag")
		g.platte(u, fb, s_oben + 0.005, s_oben + 0.05, 0.024, nu=5, nw=56, material_name="leder")
		o = u.objekt(50)
		g.dicke(o, 0.004, -1.0)
		teile.append(o)
		r = g.Teil("riemen")
		pts, zu = g.rand_punkte(fb, l_ges - 0.06, 0.013, n=48)
		g.zug(r, pts, 0.006, "leder_dunkel", zu=zu, flach=0.35)
		teile.append(r.objekt())
	return g.vereinen(teile, "iron_leicht_fuesse")
