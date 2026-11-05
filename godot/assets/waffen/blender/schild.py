"""Module des Schilds (Schildkörper, Schildbuckel) in den 6 Tier-Stilen.
Gebaut im "natürlichen" Rahmen: Breite X, Höhe Z, Vorderseite zeigt nach -Y, Griff (Hand) am Ursprung hinter der Mitte.
Am Ende wird auf das Waffen-Koordinatensystem umgerechnet, sodass in Godot oben = +Y und vorn = -Z ist.
Die Vorderseite trägt das Material "wappen": dort kommt später die Bemalung der Fraktion hin.
"""
import math, random
from mathutils import Vector, Matrix
from geo import *

D = 0.025      # Dicke des Schildkörpers
Y0 = -0.06     # Rückseite des Schilds (vor der Hand)


def _rund(r, n=32):
	return [(math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r) for i in range(n)]


def _oval(rx, rz, n=32):
	return [(math.cos(2 * math.pi * i / n) * rx, math.sin(2 * math.pi * i / n) * rz) for i in range(n)]


def _heater(b=0.3, h=0.38, n=28):
	"""Dreieckschild: gerade Oberkante, runde Seiten zur Spitze unten."""
	pts = []
	for i in range(n + 1):
		u = i / n  # rechte Seite von oben nach unten
		a = u * math.pi / 2
		pts.append((b * math.cos(a) ** 0.7 * (1 - 0.0 * u), h * 0.45 - (h * 1.45) * math.sin(a) ** 1.3))
	links = [(-x, z) for x, z in reversed(pts[1:-1])]
	return [(-b, h * 0.45), (b, h * 0.45)] + pts[1:] + links


def _drachen(b=0.24, h=0.48, n=28):
	"""Normannischer Drachenschild: runde Oberkante, lange Spitze unten."""
	pts = []
	for i in range(n + 1):
		a = math.pi * i / n  # oben, Halbkreis von rechts nach links
		pts.append((math.cos(a) * b, h * 0.45 + math.sin(a) * b * 0.6))
	for i in range(1, n):
		u = i / n
		x = -b * (1 - u) ** 1.2
		pts.append((x, h * 0.45 - (h * 1.55) * u))
	pts.append((0, -h * 1.1))
	for i in range(n - 1, 0, -1):
		u = i / n
		pts.append((b * (1 - u) ** 1.2, h * 0.45 - (h * 1.55) * u))
	return pts


def _rechteck(b, h, fase=0.03):
	return [(b, -h + fase), (b, h - fase), (b - fase, h), (-b + fase, h), (-b, h - fase), (-b, -h + fase), (-b + fase, -h), (b - fase, -h)]


def _vieleck(r, n, phase=0.0, rz=None):
	rz = rz or r
	return [(math.cos(phase + 2 * math.pi * i / n) * r, math.sin(phase + 2 * math.pi * i / n) * rz) for i in range(n)]


def _feinteilen(pts, schritt=0.03):
	"""Lange Kanten unterteilen, damit die Wölbung sauber wird."""
	aus = []
	for i, a in enumerate(pts):
		b = pts[(i + 1) % len(pts)]
		l = math.hypot(b[0] - a[0], b[1] - a[1])
		n = max(1, int(l / schritt))
		for k in range(n):
			aus.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
	return aus


def platte(t, umriss, woelbung=0.04, dicke=D, front="wappen", seite="holz", ringe=6, rauh=0.0, saat=1):
	"""Schildkörper aus einem Umriss: flache Rückseite, gewölbte Vorderseite."""
	rng = random.Random(saat)
	umriss = _feinteilen(umriss)
	n = len(umriss)
	j = [1 + (rng.uniform(-rauh, rauh) if rauh else 0) for _ in range(n)]
	hinten = [t.vert((x * j[i], Y0, z * j[i])) for i, (x, z) in enumerate(umriss)]
	vorne_ringe = []
	for k in range(ringe):
		f = 1 - k / ringe
		y = Y0 - dicke - woelbung * (1 - f * f)
		vorne_ringe.append([t.vert((x * f * j[i], y + (rng.uniform(-rauh, rauh) * 0.02 if rauh and k else 0), z * f * j[i])) for i, (x, z) in enumerate(umriss)])
	mitte = t.vert((0, Y0 - dicke - woelbung, 0))
	# Rand (Seitenfläche)
	for i in range(n):
		k = (i + 1) % n
		t.flaeche([hinten[i], hinten[k], vorne_ringe[0][k], vorne_ringe[0][i]], seite)
	for a, b in zip(vorne_ringe, vorne_ringe[1:]):
		for i in range(n):
			k = (i + 1) % n
			t.flaeche([a[i], a[k], b[k], b[i]], front)
	for i in range(n):
		t.flaeche([vorne_ringe[-1][i], vorne_ringe[-1][(i + 1) % n], mitte], front)
	t.flaeche(list(reversed(hinten)), seite)
	return umriss


def rand(t, umriss, breite=0.02, dicke=0.012, material="beschlag", y_extra=0.0):
	"""Metallrand um den Schild."""
	pts = [Vector((x, Y0 - D / 2 - y_extra, z)) for x, z in _feinteilen(umriss, 0.02)]
	pts.append(pts[0])
	strang(t, pts, dicke, breite, material, n=6, quer=Vector((0, 1, 0)), kappen=False)


def griff_hinten(t):
	"""Griff und Armriemen hinter dem Schild."""
	strang(t, [Vector((-0.07, Y0, 0.0)), Vector((-0.06, Y0 + 0.04, 0.0)), Vector((0.06, Y0 + 0.04, 0.0)), Vector((0.07, Y0, 0.0))], 0.03, 0.012, "leder", n=6, quer=Vector((0, 0, 1)))
	strang(t, [Vector((-0.12, Y0, -0.12)), Vector((-0.1, Y0 + 0.05, -0.12)), Vector((0.1, Y0 + 0.05, -0.12)), Vector((0.12, Y0, -0.12))], 0.04, 0.006, "leder", n=4, quer=Vector((0, 0, 1)))


def _vorne(umriss_z=0.0):
	return Y0 - D


# ================================================================ Schildkörper


def koerper(t, tier, form):
	griff_hinten(t)
	if tier == 1:
		u = [_rund(0.33), _drachen(), _heater()][form - 1]
		platte(t, u, 0.05 if form == 1 else 0.035)
		rand(t, u)
		if form == 1:  # Nieten um den Rand
			for i in range(12):
				a = 2 * math.pi * i / 12
				drehkoerper(t, [(0.008, 0), (0.006, 0.004), (0, 0.006)], "beschlag", n=6, versatz=Vector((math.cos(a) * 0.29, 0, math.sin(a) * 0.29)))
	elif tier == 2:
		u = [_rund(0.33), _heater(), _drachen()][form - 1]
		platte(t, u, 0.045)
		rand(t, u, 0.026, 0.016)
		# Schnörkel auf der Vorderseite
		sx, r_sp = (0.16, 0.07) if form != 3 else (0.08, 0.045)
		for s in (1, -1):
			for z, r0 in ((0.12, 1), (-0.12, -1)):
				pts = [Vector((p.x, _vorne() - 0.05, p.z)) for p in spirale((s * sx, 0, z), r_sp, 0.01, 1.4, n=30, start=0 if s > 0 else math.pi, richtung=s * r0)]
				strang(t, pts, 0.008, 0.006, "beschlag", n=5, quer=Vector((0, 1, 0)))
	elif tier == 3:
		u = [_rechteck(0.26, 0.4), _vieleck(0.36, 6, math.pi / 2, 0.4), _rechteck(0.3, 0.33, 0.06)][form - 1]
		platte(t, u, 0.015, seite="beschlag", ringe=3)
		rand(t, u, 0.028, 0.018)
		for z in (-0.2, 0.2):  # gerade Querbänder
			quader(t, (0, _vorne() - 0.016, z), (0.5 if form != 2 else 0.55, 0.008, 0.04), "beschlag")
	elif tier == 4:
		u = [_rund(0.32, 9), _vieleck(0.32, 7, 0.3, 0.38), _drachen(0.26, 0.42, 6)][form - 1]
		platte(t, u, 0.04, dicke=0.04, front="eis", seite="eis", ringe=3, rauh=0.035, saat=form)
		if form == 2:
			for a in (40, 150, 260):
				w = math.radians(a)
				kristall(t, (math.cos(w) * 0.2, _vorne() - 0.02, math.sin(w) * 0.2), (math.cos(w) * 0.6, -0.5, math.sin(w) * 0.6), 0.12, 0.02, "eis")
	elif tier == 5:
		u = [_rund(0.31), _heater(0.28, 0.36), _oval(0.27, 0.36)][form - 1]
		platte(t, u, 0.06)
		rand(t, u, 0.024, 0.02)
		if form == 1:  # Federkranz
			for i in range(16):
				a = 2 * math.pi * i / 16
				b = Vector((math.cos(a) * 0.29, Y0 - 0.01, math.sin(a) * 0.29))
				feder(t, b, b + Vector((math.cos(a + 0.4) * 0.11, 0, math.sin(a + 0.4) * 0.11)), 0.035, 0.006, quer=Vector((0, 1, 0)))
		elif form == 2:  # Flügel oben
			for s in (1, -1):
				for i in range(5):
					w = math.radians(10 + 18 * i)
					b = Vector((s * 0.2, Y0 - 0.01, 0.12))
					feder(t, b, b + Vector((s * math.cos(w) * (0.22 - 0.025 * i), 0, math.sin(w) * (0.22 - 0.025 * i))), 0.04, 0.007, quer=Vector((0, 1, 0)))
		else:  # Sonnenstrahlen auf der Fläche
			for i in range(12):
				a = 2 * math.pi * i / 12
				strang(t, [Vector((math.cos(a) * 0.1, _vorne() - 0.055, math.sin(a) * 0.1)), Vector((math.cos(a) * 0.24, _vorne() - 0.035, math.sin(a) * 0.3))],
					   lambda v: 0.03 * (1 - v), 0.006, "beschlag", n=4, quer=Vector((0, 1, 0)))
	elif tier == 6:
		if form == 1:  # runder Schild mit Dornenkranz
			u = _vieleck(0.32, 10)
			platte(t, u, 0.04, seite="beschlag")
			rand(t, u, 0.022, 0.016)
			for i in range(10):
				a = 2 * math.pi * i / 10
				stachel(t, (math.cos(a) * 0.3, Y0 - 0.015, math.sin(a) * 0.3), (math.cos(a) * 0.42, Y0 - 0.04, math.sin(a) * 0.42), 0.022)
		elif form == 2:  # zackiger Drachenschild
			u = [(x * (1 + 0.12 * ((i % 4) == 0)), z) for i, (x, z) in enumerate(_drachen(0.26, 0.46, 16))]
			platte(t, u, 0.03, seite="beschlag")
			rand(t, u, 0.022, 0.016)
		else:  # Fratze mit Hörnern
			u = [(0.28, 0.3), (0.12, 0.36), (0, 0.3), (-0.12, 0.36), (-0.28, 0.3), (-0.3, 0.0), (-0.18, -0.3), (0, -0.42), (0.18, -0.3), (0.3, 0.0)]
			platte(t, u, 0.04, seite="beschlag")
			rand(t, u, 0.022, 0.016)
			for s in (1, -1):
				stachel(t, (s * 0.24, Y0 - 0.02, 0.3), (s * 0.4, Y0 - 0.08, 0.55), 0.03, kruemmung=(s * 0.06, 0, -0.05))
		for s in (1, -1):  # glühende Risse
			strang(t, [Vector((s * 0.05, _vorne() - 0.04, 0.05)), Vector((s * 0.15, _vorne() - 0.03, -0.05)), Vector((s * 0.12, _vorne() - 0.02, -0.2))], 0.008, 0.004, "leucht", n=4)


# ================================================================ Schildbuckel


def buckel(t, tier, form):
	y = Y0 - D - 0.04  # vorderste Stelle der Wölbung (ungefähr)
	m = Matrix.Translation((0, y + 0.01, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")  # Achse nach -Y (vorn)
	def dreh(profil, material="beschlag", n=16):
		schnitte, spitze = [], None
		for r, h in profil:
			if r <= 1e-5:
				spitze = m @ Vector((0, 0, h))
				continue
			schnitte.append((m @ Matrix.Translation((0, 0, h)), kreis(r, n)))
		loft(t, schnitte, material, spitze_oben=spitze)
	if tier == 1:
		if form == 1:
			dreh([(0.09, 0.0), (0.09, 0.01), (0.07, 0.03), (0.04, 0.05), (0.0, 0.055)])
		else:
			dreh([(0.08, 0.0), (0.08, 0.01), (0.03, 0.06), (0.0, 0.09)])
	elif tier == 2:
		dreh([(0.1, 0.0), (0.1, 0.012), (0.075, 0.035), (0.04, 0.055), (0.0, 0.06)], n=20)
		if form == 1:
			for i in range(8):
				a = 2 * math.pi * i / 8
				edelstein(t, Vector((math.cos(a) * 0.085, y - 0.015, math.sin(a) * 0.085)), 0.008, "stein", achse=Vector((0, -1, 0)))
		else:
			scheibe(t, (0, y - 0.05, 0), 0.03, 0.012, strahlen=8, strahl_laenge=0.4)
		edelstein(t, Vector((0, y - 0.06, 0)), 0.014, "stein", achse=Vector((0, -1, 0)))
	elif tier == 3:
		if form == 1:
			dreh([(0.1, 0.0), (0.1, 0.012), (0.0, 0.07)], n=4)
		else:
			dreh([(0.09, 0.0), (0.09, 0.03), (0.05, 0.04), (0.0, 0.04)], n=6)
	elif tier == 4:
		if form == 1:
			kristall(t, (0, y + 0.02, 0), (0, -1, 0), 0.12, 0.035, "eis", spitze_anteil=0.35)
		else:
			rohling(t, (0, y - 0.01, 0), (0.12, 0.08, 0.13), "eis", saat=77, rauh=0.25)
	elif tier == 5:
		if form == 1:
			scheibe(t, (0, y - 0.02, 0), 0.07, 0.03, strahlen=16, strahl_laenge=0.35)
			dreh([(0.05, 0.02), (0.035, 0.05), (0.0, 0.06)], n=20)
		else:
			dreh([(0.08, 0.0), (0.08, 0.012), (0.06, 0.035), (0.0, 0.05)], n=20)
			for s in (1, -1):
				for i in range(3):
					w = math.radians(20 + 25 * i)
					b = Vector((s * 0.06, y - 0.02, 0))
					feder(t, b, b + Vector((s * math.cos(w) * 0.1, 0, math.sin(w) * 0.1)), 0.02, 0.006, quer=Vector((0, 1, 0)))
		edelstein(t, Vector((0, y - 0.06, 0)), 0.016, "stein", achse=Vector((0, -1, 0)))
	elif tier == 6:
		if form == 1:
			dreh([(0.08, 0.0), (0.08, 0.012), (0.02, 0.08), (0.0, 0.16)], n=6)
		else:
			edelstein(t, Vector((0, y - 0.03, 0)), 0.04, "stein", achse=Vector((0, -1, 0)), n=6)
			for i in range(4):
				a = 2 * math.pi * i / 4 + math.pi / 4
				r = Vector((math.cos(a), 0, math.sin(a)))
				stachel(t, Vector((0, y, 0)) + r * 0.06, Vector((0, y - 0.1, 0)) + r * 0.02, 0.012, kruemmung=r * 0.04)


def umrechnen(bauen):
	"""Natürlicher Rahmen (Höhe Z, vorn -Y) -> Waffenrahmen: Godot oben = +Y, vorn = -Z."""
	def f(t, form):
		n0 = anzahl(t)
		bauen(t, form)
		for v in neue_verts(t, n0):
			x, y, z = v.co
			v.co = Vector((x, -z, -y))
	return f


ARTEN = {
	"schildkoerper": {tier: (3, umrechnen((lambda tr: lambda t, form: koerper(t, tr, form))(tier))) for tier in range(1, 7)},
	"schildbuckel": {tier: (2, umrechnen((lambda tr: lambda t, form: buckel(t, tr, form))(tier))) for tier in range(1, 7)},
}
