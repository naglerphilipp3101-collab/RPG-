"""Module der Magiewaffen in den 6 Tier-Stilen: 4 Stäbe (Feuer, Eis, Blitz, Leben). Der Leerenhandschuh steht in handschuh.py.

Stab (Klingen-Rahmen, z entlang des Schafts, Hand am Ursprung):
  Stabschaft von -0,75 bis 0,8, Kopf sitzt oben ab z = 0,78, Fokus (Kristall) mittig bei z = FZ
  Schaftende kommt wie beim Speer von unten dran (Godot)
Der Fokus ist eine geteilte Modulart (Stäbe und Leerenhandschuh) und leuchtet in der Farbe des Elements ("kristall").
Leuchtende Akzente der Köpfe ("leucht") bekommen ebenfalls die Elementfarbe.
Jeder Kopf verbindet das Motiv des Elements (Flammen, Eissplitter, Zickzack, Ranken) mit dem Stil des Tiers.
"""
import math, random
from mathutils import Vector, Matrix
from geo import *
import schwert, stangen

FZ, FR = 0.97, 0.042   # Fokus: Mitte und Radius
SZ0, SZ1 = -0.75, 0.8  # Stabschaft
KZ = 0.84              # Ansatz der Zinken über dem Kragen
METALL = {1: "beschlag", 2: "beschlag", 3: "beschlag", 4: "eis", 5: "beschlag", 6: "beschlag"}


# ================================================================ Bausteine


def kragen(t, tier, z0=0.78, z1=0.86, r=0.024):
	"""Übergang vom Schaft zum Kopf im Stil des Tiers."""
	zm = (z0 + z1) / 2
	if tier == 1:
		drehkoerper(t, [(r * 0.8, z0), (r, z0 + 0.01), (r, z1 - 0.01), (r * 0.75, z1)], "beschlag", n=10)
		wicklung(t, z0 + 0.012, z1 - 0.012, r * 1.04, windungen=3, n=10)
	elif tier == 2:
		drehkoerper(t, [(r * 0.75, z0), (r * 1.15, z0 + 0.012), (r * 0.9, zm), (r * 1.25, z1 - 0.01), (r * 0.8, z1)], "beschlag", n=16)
		for k in range(4):
			a = math.pi / 2 * k + math.pi / 4
			edelstein(t, Vector((math.cos(a) * r * 0.95, math.sin(a) * r * 0.95, zm)), 0.007, "stein",
					  achse=Vector((math.cos(a), math.sin(a), 0)))
	elif tier == 3:
		drehkoerper(t, [(r * 0.85, z0), (r * 1.1, z0 + 0.006), (r * 1.1, z1 - 0.006), (r * 0.9, z1)], "beschlag", n=4, phase=math.pi / 4)
		drehkoerper(t, [(r * 1.25, zm - 0.006), (r * 1.25, zm + 0.006)], "beschlag", n=4, phase=math.pi / 4)
	elif tier == 4:
		rohling(t, (0, 0, zm), (z1 - z0 + 0.02, r * 2.4, r * 2.4), "eis", saat=41, rauh=0.25, n=7, achse="z")
	elif tier == 5:
		drehkoerper(t, [(r * 0.8, z0), (r * 1.2, z0 + 0.015), (r * 1.25, zm), (r * 1.1, z1 - 0.008), (r * 0.85, z1)], "beschlag", n=16)
		for s in (1, -1):  # kleine Flügel am Kragen
			for i in range(3):
				b = Vector((s * r * 0.9, 0, zm - 0.01 + 0.008 * i))
				feder(t, b, b + Vector((s * (0.06 - 0.012 * i), 0, -0.03 + 0.028 * i)), 0.016, 0.004, quer=Vector((0, 1, 0)))
	elif tier == 6:
		drehkoerper(t, [(r * 0.8, z0), (r * 1.2, z0 + 0.012), (r * 0.95, zm), (r * 1.2, z1 - 0.008), (r * 0.8, z1)], "beschlag", n=6)
		for k in range(4):
			a = math.pi / 2 * k
			d = Vector((math.cos(a), math.sin(a), 0))
			stachel(t, d * r + Vector((0, 0, z0 + 0.015)), d * (r + 0.03) + Vector((0, 0, z0 - 0.03)), 0.006)
		ring(t, zm, r * 1.0, 0.004, material="leucht", n=6, wulst=0.15)


def zinke(t, tier, pts, breite=0.011, dicke=0.008, spitz=True, saat=0):
	"""Eine Zinke des Kopfs entlang pts im Stil des Tiers (hält den Fokus)."""
	pts = [Vector(p) for p in pts]
	ende = 0.0 if spitz else 0.6
	bw = lambda u: breite * (1 - (1 - ende) * u ** 1.5) if u < 0.999 or not spitz else 0.0
	dw = lambda u: dicke * (1 - 0.5 * u) if u < 0.999 or not spitz else 0.0
	mat = METALL[tier]
	if tier == 1:
		strang(t, pts, lambda u: bw(u) * 1.15, lambda u: dw(u) * 1.15, mat, n=6)
	elif tier == 2:
		strang(t, pts, bw, dw, mat, n=8)
		# Schnörkel an der Spitze, nach außen eingerollt
		p, q = pts[-1], pts[-2]
		aussen = Vector((p.x, p.y, 0))
		if aussen.length > 1e-4:
			aussen.normalize()
			mitte = p + aussen * 0.012
			kurve = [mitte + (aussen * math.cos(a) + Vector((0, 0, 1)) * math.sin(a)) * (0.012 - 0.008 * i / 10)
					 for i, a in enumerate([math.pi + 2 * math.pi * i / 10 for i in range(11)])]
			strang(t, [p] + kurve, 0.004, 0.003, "beschlag", n=5)
	elif tier == 3:  # gerade Stücke, kantig
		knoten = [pts[0], pts[len(pts) // 3], pts[2 * len(pts) // 3], pts[-1]]
		gerade = [knoten[i].lerp(knoten[i + 1], k / 4) for i in range(3) for k in range(4)] + [knoten[-1]]
		strang(t, gerade, bw, lambda u: dw(u) * 1.1, mat, n=4, eckig=True)
	elif tier == 4:
		rng = random.Random(saat + 77)
		roh = [p + Vector((rng.uniform(-0.003, 0.003), rng.uniform(-0.003, 0.003), 0)) for p in pts]
		strang(t, roh, lambda u: bw(u) * 1.25, lambda u: dw(u) * 1.25, mat, n=5)
	elif tier == 5:
		strang(t, pts, bw, dw, mat, n=8)
		i = len(pts) // 2
		ring_bei(t, pts[i], pts[i + 1] - pts[i], breite * 0.55, 0.006)
	elif tier == 6:
		strang(t, pts, bw, dw, mat, n=4, eckig=True)
		for i in (len(pts) // 3, 2 * len(pts) // 3):
			p = pts[i]
			aussen = Vector((p.x, p.y, 0))
			if aussen.length > 1e-4:
				aussen.normalize()
				stachel(t, p, p + aussen * 0.028 + Vector((0, 0, -0.012)), 0.004)


def ring_bei(t, p, richtung, r, h, material="beschlag", n=10):
	"""Ring um eine Zinke an Punkt p."""
	d = richtung.normalized()
	rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
	m = Matrix.Translation(p) @ rot
	loft(t, [(m @ Matrix.Translation((0, 0, -h / 2)), kreis(r, n)), (m, kreis(r * 1.25, n)), (m @ Matrix.Translation((0, 0, h / 2)), kreis(r, n))], material)


def bahn(fn, n=14):
	"""Punkte einer Zinke aus fn(u) -> (Winkel, Radius, Höhe)."""
	out = []
	for i in range(n + 1):
		a, r, z = fn(i / n)
		out.append(Vector((math.cos(a) * r, math.sin(a) * r, z)))
	return out


# ================================================================ Köpfe der Stäbe


def feuerkopf(t, tier, form):
	"""Flammen: gewellte Zinken, die oben nach außen züngeln; dazwischen leuchtende Flammenzungen."""
	kragen(t, tier)
	n = 3 if form == 1 else 5
	hoehe = 0.24 if form == 1 else 0.2
	for k in range(n):
		a0 = 2 * math.pi * k / n
		def f(u, a0=a0):
			r = 0.022 + 0.052 * math.sin(math.pi * u * 0.82) + (0.025 * (u - 0.8) / 0.2 if u > 0.8 else 0)
			return a0 + 0.38 * math.sin(2 * math.pi * u * (1 if form == 1 else 1.4)), r, KZ + hoehe * u
		zinke(t, tier, bahn(f), breite=0.016 if form == 1 else 0.012, dicke=0.008, saat=k)
		# Flammenzunge zwischen den Zinken
		am = a0 + math.pi / n
		d = Vector((math.cos(am), math.sin(am), 0))
		stachel(t, d * 0.02 + Vector((0, 0, KZ)), d * 0.045 + Vector((0, 0, KZ + 0.075)), 0.008, material="leucht", n=5,
				kruemmung=d * 0.01)
	if form == 2:
		ring(t, KZ + 0.012, 0.03, 0.006, material="leucht", n=12, wulst=0.2)


def eiskopf(t, tier, form):
	"""Eissplitter: Kristalle stehen schräg nach außen um den Fokus; kurze Klauen halten ihn von unten."""
	kragen(t, tier)
	splitter = "eis" if tier == 4 else "kristall"
	n = 4 if form == 1 else 6
	for k in range(n):
		a = 2 * math.pi * k / n + (math.pi / n if form == 2 else 0)
		d = Vector((math.cos(a), math.sin(a), 0))
		lang = (0.17 if form == 1 else 0.13) * (1.0 if k % 2 == 0 or form == 1 else 0.75)
		basis = d * 0.03 + Vector((0, 0, KZ + 0.005))
		richtung = d * 0.42 + Vector((0, 0, 1))
		if k % 2 == 1 and tier != 4:  # jeder zweite Splitter ist eine Klinge aus dem Metall des Tiers
			eckig = tier in (3, 6)
			strang(t, [basis + richtung.normalized() * lang * i / 6 for i in range(7)],
				   lambda u: 0.024 * (1 - u ** (1.0 if eckig else 2.0)) if u < 0.999 else 0.0,
				   lambda u: 0.007 * (1 - u) if u < 0.999 else 0.0, METALL[tier], n=4 if eckig else 6,
				   quer=Vector((-d.y, d.x, 0)).cross(richtung).normalized(), eckig=eckig)
			if tier == 6:
				for i in (2, 4):
					p = basis + richtung.normalized() * lang * i / 6
					stachel(t, p, p + d * 0.022 + Vector((0, 0, -0.01)), 0.004)
			elif tier == 2:
				ring_bei(t, basis + richtung.normalized() * 0.02, richtung, 0.012, 0.008)
				edelstein(t, basis + richtung.normalized() * 0.035 + d * 0.008, 0.005, "stein", achse=d)
			continue
		kristall(t, basis, richtung, lang, 0.011 if form == 1 else 0.009, splitter, n=6, spitze_anteil=0.35, drehung=a)
	# Klauen unter dem Fokus
	for k in range(3):
		a0 = 2 * math.pi * k / 3 + math.pi / 6
		zinke(t, tier, bahn(lambda u, a0=a0: (a0, 0.02 + 0.03 * math.sin(math.pi * u * 0.6), KZ + 0.11 * u), 8),
			  breite=0.009, dicke=0.006, saat=k)
	if form == 2:  # Spitze über dem Fokus
		kristall(t, (0, 0, FZ + FR + 0.012), (0, 0, 1), 0.08, 0.01, splitter, n=6, spitze_anteil=0.5)
		for k in range(3):
			a = 2 * math.pi * k / 3
			d = Vector((math.cos(a), math.sin(a), 0))
			zinke(t, tier, [d * 0.055 + Vector((0, 0, FZ - 0.01)), d * 0.04 + Vector((0, 0, FZ + 0.04)), d * 0.012 + Vector((0, 0, FZ + 0.055))],
				  breite=0.006, dicke=0.005, spitz=False, saat=k + 5)


def blitzkopf(t, tier, form):
	"""Blitz: Zickzack-Zinken wie eine Gabel; Form 2 mit leuchtenden Ringen wie eine Spule."""
	kragen(t, tier)
	n = 2 if form == 1 else 4
	knoten = [(0.0, 0.022, 0.0), (0.22, 0.062, 0.06), (-0.12, 0.05, 0.11), (0.2, 0.072, 0.17), (0.0, 0.058, 0.25)]
	if form == 2:
		knoten = [(0.0, 0.022, 0.0), (0.18, 0.06, 0.07), (-0.14, 0.064, 0.14), (0.0, 0.03, 0.22)]
	for k in range(n):
		a0 = 2 * math.pi * k / n
		pts = []
		for (wa, ra, za), (wb, rb, zb) in zip(knoten, knoten[1:]):
			for i in range(4):
				s = i / 4
				w, r, z = wa + (wb - wa) * s, ra + (rb - ra) * s, za + (zb - za) * s
				pts.append(Vector((math.cos(a0 + w) * r, math.sin(a0 + w) * r, KZ + z)))
		w, r, z = knoten[-1]
		pts.append(Vector((math.cos(a0 + w) * r, math.sin(a0 + w) * r, KZ + z)))
		if tier in (1, 2, 5):  # Zickzack bleibt scharf, auch bei runden Stilen
			strang(t, pts, lambda u: 0.013 * (1 - 0.6 * u), lambda u: 0.008 * (1 - 0.4 * u), METALL[tier], n=4, eckig=True)
			if tier == 2:
				edelstein(t, pts[4], 0.006, "stein", achse=Vector((pts[4].x, pts[4].y, 0)))
			if tier == 5:
				ring_bei(t, pts[8], pts[9] - pts[8], 0.006, 0.006)
		else:
			zinke(t, tier, pts, breite=0.013, dicke=0.008, saat=k)
	if form == 2:
		for z, r in ((FZ - 0.02, 0.07), (FZ + 0.03, 0.06)):
			ring(t, z, r, 0.004, material="leucht", n=16, wulst=0.3)
	else:
		# leuchtender Funke zwischen den Gabelspitzen
		strang(t, [Vector((0.058, 0, KZ + 0.25)), Vector((0.02, 0.01, KZ + 0.23)), Vector((-0.02, -0.01, KZ + 0.25)), Vector((-0.058, 0, KZ + 0.25))],
			   0.004, 0.004, "leucht", n=4)


def lebenskopf(t, tier, form):
	"""Leben: Ranken winden sich um den Fokus; Form 1 geschlossen wie eine Knospe, Form 2 offen mit Blättern."""
	kragen(t, tier)
	n = 3 if form == 1 else 4
	for k in range(n):
		a0 = 2 * math.pi * k / n
		if form == 1:
			f = lambda u, a0=a0: (a0 + 1.3 * u, 0.012 + 0.058 * math.sin(math.pi * u) ** 0.8, KZ + 0.25 * u)
		else:
			f = lambda u, a0=a0: (a0 + 0.9 * u, 0.022 + 0.07 * u ** 0.7, KZ + 0.22 * u)
		pts = bahn(f, 16)
		zinke(t, tier, pts, breite=0.012, dicke=0.009, spitz=form == 2, saat=k)
		# Blätter
		for i in ((5, 11) if form == 1 else (4, 9, 14)):
			p = pts[i]
			aussen = Vector((p.x, p.y, 0)).normalized()
			blatt_mat = METALL[tier]  # Blätter aus dem Metall des Tiers, nur der Fokus leuchtet
			feder(t, p, p + aussen * 0.04 + Vector((0, 0, 0.018)), 0.018, 0.003, blatt_mat, quer=Vector((0, 0, 1)).cross(aussen))
	if form == 1:  # Knospe schließt sich oben
		drehkoerper(t, [(0.0, KZ + 0.235), (0.012, KZ + 0.25), (0.0, KZ + 0.275)], METALL[tier], n=8)


# ================================================================ Schaft und Fokus


def stabschaft(t, tier, form):
	stangen.stiel(t, tier, form, SZ0, SZ1, 0.017)
	wicklung(t, -0.1, 0.15, 0.017 * 1.12, windungen=10)


def fokus(t, tier, form):
	"""Kristall im Kopf; nimmt die Farbe des Elements an."""
	m = "kristall"
	z = FZ
	if tier == 1:
		if form == 1:
			drehkoerper(t, [(0, z - FR), (FR * 0.7, z - FR * 0.7), (FR, z), (FR * 0.7, z + FR * 0.7), (0, z + FR)], m, n=12)
		else:
			rohling(t, (0, 0, z), (FR * 2.1, FR * 1.8, FR * 1.8), m, saat=11, rauh=0.2, n=7, achse="z")
	elif tier == 2:
		if form == 1:
			edelstein(t, Vector((0, 0, z + FR * 0.2)), FR * 1.05, m, achse="z", n=10)
		else:
			drehkoerper(t, [(0, z - FR), (FR * 0.7, z - FR * 0.7), (FR, z), (FR * 0.7, z + FR * 0.7), (0, z + FR)], m, n=14)
			ring(t, z, FR * 1.01, 0.007, n=16, wulst=0.15)
	elif tier == 3:
		if form == 1:  # Oktaeder
			drehkoerper(t, [(0, z - FR * 1.2), (FR, z), (0, z + FR * 1.2)], m, n=4)
		else:  # sechskantiges Prisma mit zwei Spitzen
			drehkoerper(t, [(0, z - FR * 1.5), (FR * 0.7, z - FR * 0.7), (FR * 0.7, z + FR * 0.7), (0, z + FR * 1.5)], m, n=6)
	elif tier == 4:
		if form == 1:  # Kristallbüschel
			for k, (dx, dy, dz, l) in enumerate([(0, 0, 1, 1.0), (0.6, 0.2, 0.8, 0.7), (-0.5, 0.4, 0.8, 0.75), (0.1, -0.7, 0.7, 0.65), (-0.3, -0.3, -0.6, 0.6)]):
				d = Vector((dx, dy, dz)).normalized()
				kristall(t, Vector((0, 0, z)) - d * FR * 0.5, d, FR * 2 * l, FR * 0.42, m, n=6, spitze_anteil=0.4, drehung=k)
		else:
			rohling(t, (0, 0, z), (FR * 2.3, FR * 1.9, FR * 1.9), m, saat=23, rauh=0.32, n=6, achse="z")
	elif tier == 5:
		if form == 1:
			drehkoerper(t, [(0, z - FR), (FR * 0.7, z - FR * 0.7), (FR, z), (FR * 0.7, z + FR * 0.7), (0, z + FR)], m, n=14)
			ring(t, z, FR * 1.02, 0.005, n=16, wulst=0.2)
			# Strahlenkranz hinter dem Kristall
			scheibe(t, (0, 0, z), FR * 1.15, 0.004, n=32, strahlen=12, strahl_laenge=0.35, wulst=0.7)
		else:  # Tropfen
			drehkoerper(t, [(0, z - FR * 1.1), (FR * 0.85, z - FR * 0.5), (FR * 0.75, z + FR * 0.4), (0, z + FR * 1.6)], m, n=14)
	elif tier == 6:
		if form == 1:  # Stern aus Splittern
			drehkoerper(t, [(0, z - FR * 0.6), (FR * 0.6, z), (0, z + FR * 0.6)], m, n=6)
			for k, d in enumerate([(1, 0, 0.3), (-1, 0, 0.3), (0, 1, 0.3), (0, -1, 0.3), (0.5, 0.5, 1), (-0.5, -0.5, 1), (0.6, -0.5, -0.8), (-0.6, 0.5, -0.8)]):
				d = Vector(d).normalized()
				kristall(t, Vector((0, 0, z)), d, FR * 1.25, FR * 0.22, m, n=4, spitze_anteil=0.6, drehung=k)
		else:  # langer, schmaler Diamant
			drehkoerper(t, [(0, z - FR * 1.7), (FR * 0.75, z - FR * 0.2), (FR * 0.6, z + FR * 0.3), (0, z + FR * 1.9)], m, n=5)


def _tiers(fn, n):
	return {tier: (n, (lambda tr: lambda t, form: fn(t, tr, form))(tier)) for tier in range(1, 7)}


ARTEN = {
	"feuerkopf": _tiers(feuerkopf, 2),
	"eiskopf": _tiers(eiskopf, 2),
	"blitzkopf": _tiers(blitzkopf, 2),
	"lebenskopf": _tiers(lebenskopf, 2),
	"stabschaft": _tiers(stabschaft, 2),
	"fokus": _tiers(fokus, 2),
}
