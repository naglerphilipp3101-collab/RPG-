"""Leerenhandschuh (ersetzt die Leerenkugel, Philipp 10.11.): ein Panzerhandschuh für Nahkampf-Magier.

Module:
  handschuh   Hauptmodul: Stulpe, Hand mit Fingern und Daumen, Knöchelschutz, Fassung für den Fokus
  magieklinge Klinge aus Magie, die per Fähigkeit aus der Faust wächst (Elementfarbe, leuchtend), gebaut im
              Klingen-Rahmen (Länge +Z, Ansatz bei z = 0); Godot setzt sie vor die Knöchel (waffen_modell.gd)
  fokus       geteilt mit den Stäben, sitzt verkleinert auf dem Handrücken

Bauraum des Handschuhs (Blender, wie die Klingen): die Faust umschließt die Griffachse Z (Daumenseite +Z,
wie beim Schwertgriff), der Unterarm zeigt nach -X, der Handrücken nach -Y, die Knöchel nach +X.
Hauptfarbe ("klinge") tragen Knöchelschutz und Stulpenplatten, Akzentfarbe ("akzent") Zierlinien und Steine,
Finger, Handrücken und Fassung bleiben in der Grundfarbe des Materials ("beschlag").
"""
import math, random
from mathutils import Vector, Matrix
from geo import *
import schwert

W = -0.072            # Handgelenk
AY = -0.03            # Unterarmachse (y)
FOKUS = Vector((-0.022, -0.06, 0.0))   # Fassung auf dem Handrücken (Unterkante)


def quer_x(x, y=AY, z=0.0):
	"""Rahmen für Querschnitte entlang X: lokales x -> Welt z, lokales y -> Welt y."""
	return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(-90), 4, "Y")


def ellipse(rz, ry, n, phase=0.0, rauh=0.0, rng=None):
	pts = []
	for k in range(n):
		a = phase + 2 * math.pi * k / n
		j = 1 + (rng.uniform(-rauh, rauh) if rng else 0.0)
		pts.append((math.cos(a) * rz * j, math.sin(a) * ry * j))
	return pts


# ================================================================ Stulpe


def stulpe(t, tier, form):
	"""Unterarmschutz aus überlappenden Platten (Lamellen), vom Handgelenk nach hinten weiter werdend."""
	ende = -0.235 if form == 1 else -0.2
	weite = 0.012 if form == 1 else 0.02
	n = {1: 14, 2: 18, 3: 8, 4: 9, 5: 18, 6: 6}[tier]
	phase = {3: math.pi / 8, 6: math.pi / 6}.get(tier, 0.0)
	rng = random.Random(tier * 10 + form)
	baender = 3 if tier in (1, 3, 6) else 2
	grenzen = [W + 0.004 + (ende - W) * i / baender for i in range(baender + 1)]
	for i in range(baender):
		x0, x1 = grenzen[i], grenzen[i + 1]
		schnitte = []
		for k in range(5):
			u = k / 4
			x = x0 + (x1 - x0) * u
			g = (x - W) / (ende - W)                     # 0 am Handgelenk, 1 am Ende
			rz, ry = 0.044 + weite * g, 0.037 + weite * 0.8 * g
			s = 1.0 + 0.06 * u                            # jede Lamelle läuft hinten etwas auf
			if k == 4:
				s *= 0.97
			schnitte.append((quer_x(x), ellipse(rz * s, ry * s, n, phase, 0.05 if tier == 4 else 0.0, rng)))
		loft(t, schnitte, "klinge")
		# Kante am hinteren Rand jeder Lamelle
		g = (x1 - W) / (ende - W)
		rz, ry = (0.044 + weite * g) * 1.07, (0.037 + weite * 0.8 * g) * 1.07
		kante = "akzent" if tier in (2, 5, 6) else "beschlag"
		loft(t, [(quer_x(x1 + 0.006), ellipse(rz * 0.97, ry * 0.97, n, phase)),
				 (quer_x(x1 + 0.003), ellipse(rz * 1.02, ry * 1.02, n, phase)),
				 (quer_x(x1 - 0.002), ellipse(rz * 0.98, ry * 0.98, n, phase))], kante, kappe_unten=False, kappe_oben=False)
	# Futter in der Öffnung hinten
	loft(t, [(quer_x(ende + 0.004), ellipse((0.044 + weite) * 0.94, (0.037 + weite * 0.8) * 0.94, n, phase)),
			 (quer_x(ende + 0.012), ellipse((0.044 + weite) * 0.9, (0.037 + weite * 0.8) * 0.9, n, phase))], "leder")
	# Zierde je Tier auf der Außenseite (-Y)
	mitte = (W + ende) / 2
	ry_m = 0.037 + weite * 0.4
	if tier == 1:  # Lederriemen mit Schnalle
		xr = W - 0.03
		loft(t, [(quer_x(xr - 0.007), ellipse(0.0465, 0.0395, 14)), (quer_x(xr + 0.007), ellipse(0.0465, 0.0395, 14))], "leder")
		quader(t, (xr, AY - 0.041, 0.0), (0.018, 0.005, 0.016), "beschlag", fase=0.002)
		if form == 2:
			for z in (-0.02, 0.0, 0.02):  # Nieten
				n0 = anzahl(t)
				drehkoerper(t, [(0.0045, 0.0), (0.004, 0.002), (0, 0.004)], "beschlag", n=6)
				_auf_achse(t, Vector((mitte - 0.02, AY - ry_m - 0.001, z)), Vector((0, -1, 0)), n0)
	elif tier == 2:  # Schnörkelband und Steine
		for k, x in enumerate((W - 0.035, mitte, ende + 0.03)):
			edelstein(t, Vector((x, AY - (0.037 + weite * 0.8 * (x - W) / (ende - W)) * 1.05 - 0.002, 0.0)), 0.007, "akzent",
					  achse=Vector((0, -1, 0)))
		for s in (1, -1):
			pts = [Vector((W - 0.02 - 0.12 * u, AY - 0.04 - 0.008 * u, s * (0.018 + 0.012 * math.sin(math.pi * u * 2)))) for u in [i / 12 for i in range(13)]]
			strang(t, pts, 0.004, 0.003, "akzent", n=5)
	elif tier == 3:  # gerader Grat
		pts = [Vector((W - 0.01 + (ende - W + 0.02) * u, AY - (0.037 + weite * 0.8 * u) * 1.08 - 0.002, 0.0)) for u in (0, 0.5, 1)]
		strang(t, pts, 0.006, 0.008, "beschlag", n=4, eckig=True)
		if form == 2:
			for s in (1, -1):
				pts = [Vector((W - 0.02 + (ende - W + 0.03) * u, AY - 0.03, s * (0.046 + weite * u) * 1.05)) for u in (0, 1)]
				strang(t, pts, 0.005, 0.005, "akzent", n=4, eckig=True)
	elif tier == 4:  # Eisbrocken auf dem Unterarm
		for k, x in enumerate((W - 0.04, mitte - 0.01, ende + 0.035)):
			rohling(t, (x, AY - 0.045 - 0.004 * k, 0.012 * (-1) ** k), (0.034, 0.02, 0.028), "eis", saat=k + 5 * form, rauh=0.3, n=6)
	elif tier == 5:  # Flügel an der Außenseite der Stulpe
		for s in (1, -1):
			for i in range(4):
				b = Vector((ende + 0.04 + 0.025 * i, AY - 0.02, s * (0.05 + weite * 0.8)))
				e = b + Vector((-0.07 + 0.012 * i, -0.012, s * (0.02 + 0.008 * i)))
				feder(t, b, e, 0.02, 0.004, "akzent" if i == 0 else "beschlag", quer=Vector((0, 1, 0)))
	elif tier == 6:  # Dornen auf dem Grat und glimmende Linie
		for k in range(4 if form == 1 else 3):
			x = W - 0.03 - k * (ende - W - 0.03) / 3.5
			g = (x - W) / (ende - W)
			b = Vector((x, AY - (0.037 + weite * 0.8 * g) * 1.0, 0.0))
			stachel(t, b, b + Vector((-0.025, -0.035 + 0.004 * k, 0)), 0.007)
		for s in (1, -1):  # glimmende Zickzack-Linie, liegt auf den Lamellen
			pts = []
			for i in range(9):
				u = i / 8
				x = W - 0.004 + (ende - W + 0.008) * u
				a = math.radians(-58 + 7 * (i % 2))
				rz, ry = (0.044 + weite * u) * 1.075, (0.037 + weite * 0.8 * u) * 1.075
				pts.append(Vector((x, AY + math.sin(a) * ry, s * math.cos(a) * rz)))
			strang(t, pts, 0.004, 0.003, "leucht", n=4, eckig=True)


# ================================================================ Hand


def hand(t, tier, form):
	"""Handrücken, Innenhand, Finger und Daumen."""
	eckig = tier in (3, 6)
	n = 4 if eckig else 8
	# Handkörper (Leder) mit Platte darüber
	schnitte = []
	for k, x in enumerate((W - 0.006, W + 0.03, -0.005, 0.022, 0.03)):
		b = 0.043 + 0.006 * min(1.0, k / 3)
		schnitte.append((quer_x(x, -0.031), ellipse(b if k < 4 else b * 0.9, 0.017 if k < 4 else 0.015, 12)))
	loft(t, schnitte, "leder")
	# Handrückenplatte (gewölbt), zwei Lamellen
	for i, (x0, x1) in enumerate(((W - 0.002, -0.022), (-0.026, 0.02))):
		pl = []
		for k in range(3):
			x = x0 + (x1 - x0) * k / 2
			bz = 0.04 + 0.003 * (i + k / 2)
			pl.append((quer_x(x, -0.04 - 0.002 * i), _platte(bz, 0.006, 0.011, 9, eckig)))
		loft(t, pl, "beschlag")
	# Finger: Bögen um die Griffachse, mit Gliederplatten
	finger = [(0.031, 0.026, 0.0185), (0.0105, 0.027, 0.019), (-0.0095, 0.026, 0.0185), (-0.029, 0.023, 0.016)]
	mitte = Vector((0.006, -0.006))
	glieder = [(-75, 20), (28, 92), (100, 165)]
	for zf, r, b in finger:
		pts = [Vector((mitte.x + math.cos(math.radians(a)) * r, mitte.y + math.sin(math.radians(a)) * r, zf)) for a in range(-95, 171, 15)]
		strang(t, pts, b * 0.9, b * 0.85, "leder", n=8, quer=Vector((0, 0, 1)))
		for gi, (a0, a1) in enumerate(glieder):
			gp = [Vector((mitte.x + math.cos(math.radians(a)) * (r + 0.0015), mitte.y + math.sin(math.radians(a)) * (r + 0.0015), zf))
				  for a in range(a0, a1 + 1, max(5, (a1 - a0) // 4))]
			strang(t, gp, b, b * 0.75, "beschlag", n=n, quer=Vector((0, 0, 1)), eckig=eckig)
		if tier == 6:  # Klauen an den Fingerspitzen
			a = math.radians(168)
			p = Vector((mitte.x + math.cos(a) * r, mitte.y + math.sin(a) * r, zf))
			tang = Vector((-math.sin(a), math.cos(a), 0))
			stachel(t, p, p + tang * 0.018 + Vector((-0.004, 0, 0)), 0.006)
	# Daumen über Zeige- und Mittelfinger
	dp = [Vector(p) for p in [(-0.05, -0.034, 0.03), (-0.036, -0.02, 0.046), (-0.016, -0.0, 0.052), (0.004, 0.016, 0.05), (0.02, 0.022, 0.043)]]
	strang(t, dp, 0.019, 0.017, "leder", n=8, quer=Vector((0, 0, 1)))
	for a, b in ((0, 2), (2, 4)):
		strang(t, [dp[a].lerp(dp[b], k / 3) + Vector((0, 0, 0.0015)) for k in range(4)], 0.021, 0.014, "beschlag", n=n,
			   quer=Vector((0, 0, 1)), eckig=eckig)


def _platte(bz, dicke, woelbung, n, eckig):
	"""Gewölbter Querschnitt einer Platte (Breite bz zu jeder Seite) für quer_x."""
	oben, unten = [], []
	for k in range(n):
		u = k / (n - 1)
		z = -bz + 2 * bz * u
		w = (1 - (2 * u - 1) ** 2) if not eckig else (1 - abs(2 * u - 1))
		oben.append((z, -woelbung * w - dicke))
		unten.append((z * 0.98, -woelbung * w))
	return unten + list(reversed(oben))


# ================================================================ Knöchelschutz und Fassung


def knoechel(t, tier, form):
	"""Schlagfläche über den Knöcheln (Hauptfarbe)."""
	kx, ky = 0.026, -0.04
	if tier == 4:
		rohling(t, (kx, ky, 0.0), (0.092, 0.022, 0.026), "eis", saat=31 + form, rauh=0.22, n=6, achse="z")
		return
	eckig = tier in (3, 6)
	nq = 4 if eckig else 10
	schnitte = []
	for k in range(7):
		u = k / 6
		z = -0.05 + 0.1 * u
		f = (math.sin(math.pi * (0.12 + 0.76 * u))) ** 0.3
		w, h = 0.024 * f, 0.016 * f
		pts = ellipse(w / 2, h / 2, nq, math.pi / 4 if eckig else 0.0)
		schnitte.append((z, [(x + kx, y + ky) for x, y in pts]))
	loft(t, schnitte, "klinge")
	zs = [-0.031, -0.01, 0.011, 0.032]
	if tier == 1:
		if form == 2:
			for z in zs:
				n0 = anzahl(t)
				drehkoerper(t, [(0.0065, 0), (0.005, 0.006), (0, 0.009)], "beschlag", n=8)
				_auf_achse(t, Vector((kx + 0.01, ky - 0.004, z)), Vector((1, -0.4, 0)), n0)
	elif tier == 2:
		for z in (-0.042, 0.042):
			edelstein(t, Vector((kx + 0.008, ky - 0.006, z)), 0.006, "akzent", achse=Vector((1, -0.6, 0)))
		strang(t, [Vector((kx + 0.012, ky - 0.004, -0.045 + 0.09 * u)) for u in (0, 0.5, 1)], 0.004, 0.004, "akzent", n=6)
	elif tier == 3:
		for z in zs:
			n0 = anzahl(t)
			drehkoerper(t, [(0.006, 0), (0, 0.009)], "klinge", n=4, phase=math.pi / 4)
			_auf_achse(t, Vector((kx + 0.011, ky - 0.003, z)), Vector((1, -0.3, 0)), n0)
	elif tier == 5:
		scheibe(t, (kx + 0.004, ky - 0.012, 0.0), 0.013, 0.004, "akzent", n=20, strahlen=8, strahl_laenge=0.4)
	elif tier == 6:
		for i, z in enumerate(zs):
			b = Vector((kx + 0.008, ky - 0.002, z))
			stachel(t, b, b + Vector((0.03 + 0.006 * (i % 2), -0.006, 0)), 0.006 if form == 1 else 0.0075)


def _auf_achse(t, ziel, richtung, n0):
	"""Dreht die seit n0 gebauten Punkte (Drehkörper mit Achse Z, Fuß bei 0) in 'richtung' und setzt sie auf 'ziel'."""
	vs = list(neue_verts(t, n0))
	rot = Vector(richtung).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
	transformieren(t, vs, Matrix.Translation(ziel) @ rot)


def fassung(t, tier, form):
	"""Schale auf dem Handrücken, in der der Fokus sitzt."""
	n = {3: 4, 6: 6}.get(tier, 14)
	profil = [(0.008, 0.0), (0.02, 0.004), (0.026, 0.01), (0.024, 0.014)]
	if tier == 4:
		rohling(t, (FOKUS.x, FOKUS.y - 0.004, 0.0), (0.05, 0.012, 0.044), "eis", saat=60 + form, rauh=0.3, n=7)
		return
	n0 = anzahl(t)
	drehkoerper(t, profil, "beschlag", n=n, phase=math.pi / 4 if tier == 3 else 0.0)
	_auf_achse(t, FOKUS, Vector((0, -1, 0)), n0)
	# Krallen, die den Fokus halten
	krallen = 4 if form == 1 else 3
	for k in range(krallen):
		a = 2 * math.pi * k / krallen + math.pi / 4
		d = Vector((math.cos(a), 0, math.sin(a)))
		b = FOKUS + d * 0.022 + Vector((0, -0.012, 0))
		if tier == 6:
			stachel(t, b, b + d * 0.004 + Vector((0, -0.03, 0)) - d * 0.012, 0.004)
		elif tier == 5:
			feder(t, b, b + Vector((0, -0.026, 0)) - d * 0.008, 0.009, 0.003, "akzent", quer=d)
		else:
			pts = [b, b + Vector((0, -0.012, 0)) + d * 0.002, b + Vector((0, -0.024, 0)) - d * 0.006]
			strang(t, pts, lambda u: 0.007 * (1 - 0.5 * u), 0.004, "akzent" if tier == 2 else "beschlag", n=4 if tier == 3 else 6,
				   quer=d, eckig=(tier == 3))


# ================================================================ Module


def handschuh(t, tier, form):
	stulpe(t, tier, form)
	hand(t, tier, form)
	knoechel(t, tier, form)
	fassung(t, tier, form)


def magieklinge(t, tier, form):
	"""Klinge aus reiner Magie (wie eine Leerenklinge), die per Fähigkeit aus der Faust wächst; ganz im Material "magie",
	das in der Elementfarbe leuchtet. Form nach der Klinge des Tiers, breiter und länger; Ansatz bei z = 0 (vor den Knöcheln)."""
	n0 = anzahl(t)
	f0 = len(t.bm.faces)
	schwert.KLINGEN[tier - 1](t, form)
	for v in neue_verts(t, n0):
		v.co = Vector((v.co.x * 1.15, v.co.y * 0.7, (v.co.z - schwert.KL) * 0.62 - 0.03))
	t.bm.faces.ensure_lookup_table()
	magie = t.slot("magie")
	for f in t.bm.faces[f0:]:
		f.material_index = magie


def _tiers(fn, n):
	return {tier: (n, (lambda tr: lambda t, form: fn(t, tr, form))(tier)) for tier in range(1, 7)}


ARTEN = {
	"handschuh": _tiers(handschuh, 2),
	"magieklinge": _tiers(magieklinge, 3),
}
