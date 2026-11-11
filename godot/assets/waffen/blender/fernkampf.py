"""Module der Fernkampfwaffen (Bogen, Armbrust, Muskete) und die Geschosse (Pfeil, Bolzen) in den 6 Tier-Stilen.

Bogen, Armbrust und Muskete werden im "natürlichen" Rahmen gebaut (oben = Z, Schussrichtung = -Y, Hand am Ursprung)
und mit schild.umrechnen ins Waffen-Koordinatensystem gebracht (Godot: oben +Y, vorn -Z).
Feste Punkte, damit alle Module zusammenpassen:
  Bogen:    Wurfarm-Enden bei (0, 0,16, ±0,68), Griff von z -0,1 bis 0,1, Sehne dazwischen bei y = 0,16
  Armbrust: Schaft von y +0,2 (Kolben) bis -0,46, Bogen vorne bei y -0,42, Enden bei (±0,4, -0,33, 0,03)
  Muskete:  Schaft von y +0,32 bis -0,62, Lauf von y -0,02 bis -1,02 auf Höhe z 0,035, Schloss rechts bei y -0,02
Pfeil und Bolzen liegen im Klingen-Rahmen (Spitze nach +Z, Mitte am Ursprung).
"""
import math, random
from mathutils import Vector, Matrix
from geo import *
from schild import umrechnen

SPITZE_Y, SPITZE_Z = 0.16, 0.68   # Wurfarm-Enden
HOLZ = {1: "holz", 2: "holz", 3: "klinge", 4: "eis", 5: "stoff", 6: "beschlag"}


# ================================================================ Bogen


def _arm_bahn(form_kurve, s, n=16):
	"""Bahn eines Wurfarms vom Griff (z = s*0,09) zur Spitze; form_kurve(u) -> y, mit y(1) = SPITZE_Y."""
	return [Vector((0, form_kurve(i / n), s * (0.09 + (SPITZE_Z - 0.09) * i / n))) for i in range(n + 1)]


KURVEN = {
	"lang": lambda u: SPITZE_Y * u * u,
	"recurve": lambda u: 0.2475 * u * u - 1.4 * max(0.0, u - 0.75) ** 2,  # Enden biegen leicht nach vorn
	"reflex": lambda u: SPITZE_Y * u - 0.07 * math.sin(math.pi * u),
	"mond": lambda u: SPITZE_Y * (1 - math.cos(u * math.pi / 2)) * 1.0 + 0.04 * math.sin(math.pi * u),
}


def wurfarme(t, tier, form):
	mat = HOLZ[tier]
	for s in (1, -1):
		if tier == 1:
			k = ["lang", "recurve", "reflex"][form - 1]
			strang(t, _arm_bahn(KURVEN[k], s), lambda u: 0.034 - 0.018 * u, lambda u: 0.022 - 0.01 * u, mat, n=8)
			_nocke(t, s, "holz" if form != 3 else "dunkel")
		elif tier == 2:
			k = ["recurve", "lang", "reflex"][form - 1]
			bahn = _arm_bahn(KURVEN[k], s)
			strang(t, bahn, lambda u: 0.034 - 0.016 * u, lambda u: 0.02 - 0.008 * u, mat, n=8)
			for u in (0.3, 0.6):
				p = bahn[int(u * 16)]
				ring_um(t, p, bahn[int(u * 16) + 1] - p, 0.02, 0.008)
			_nocke(t, s, "beschlag", gross=True)
			if form != 2:  # Schnörkel an den Enden
				p = bahn[-3]
				strang(t, [Vector((0, p.y - 0.01 * i, p.z + s * 0.003 * i)) for i in range(1)] +
					   [Vector((0, p.y - 0.02 + math.cos(a) * 0.015, p.z + s * (0.02 + math.sin(a) * 0.015))) for a in [math.pi * i / 8 for i in range(14)]],
					   0.005, 0.004, "beschlag", n=5, quer=Vector((1, 0, 0)))
		elif tier == 3:  # gerade Segmente, eckig
			if form == 1:
				bahn = [Vector((0, 0, s * 0.09)), Vector((0, 0.03, s * 0.36)), Vector((0, SPITZE_Y, s * SPITZE_Z))]
			elif form == 2:
				bahn = [Vector((0, 0, s * 0.09)), Vector((0, 0.0, s * 0.3)), Vector((0, 0.09, s * 0.5)), Vector((0, SPITZE_Y, s * SPITZE_Z))]
			else:
				bahn = [Vector((0, 0, s * 0.09)), Vector((0, SPITZE_Y, s * SPITZE_Z))]
			bahn = [bahn[i].lerp(bahn[i + 1], k / 6) for i in range(len(bahn) - 1) for k in range(6)] + [bahn[-1]]
			strang(t, bahn, lambda u: 0.04 - 0.02 * u, lambda u: 0.016 - 0.006 * u, mat, n=4, eckig=True)
			quader(t, (0, SPITZE_Y, s * (SPITZE_Z - 0.01)), (0.03, 0.025, 0.04), "beschlag")
		elif tier == 4:
			k = ["lang", "reflex", "recurve"][form - 1]
			bahn = _arm_bahn(KURVEN[k], s, 8)
			rng = random.Random(form * 7 + s)
			bahn = [p + Vector((rng.uniform(-0.004, 0.004), rng.uniform(-0.006, 0.006), 0)) for p in bahn]
			strang(t, bahn, lambda u: 0.04 - 0.02 * u, lambda u: 0.026 - 0.01 * u, mat, n=5)
			kristall(t, bahn[-2], (0, -0.4, s), 0.07, 0.012, "eis")
			if form == 2:  # knotig wie Geweih
				for i in (2, 4, 6):
					kristall(t, bahn[i], (0, -1, s * 0.6), 0.04, 0.008, "eis")
		elif tier == 5:
			k = ["mond", "recurve", "lang"][form - 1]
			bahn = _arm_bahn(KURVEN[k], s)
			strang(t, bahn, lambda u: 0.034 - 0.016 * u, lambda u: 0.022 - 0.01 * u, mat, n=10)
			_nocke(t, s, "beschlag", gross=True)
			if form == 1:  # Federn auf der Vorderseite: der Bogen wird zum Flügel
				for i in range(2, 15, 2):
					p = bahn[i]
					feder(t, p, p + Vector((0, -0.06 - 0.004 * i, s * 0.03)), 0.022, 0.005, quer=Vector((1, 0, 0)))
			else:
				for i in (4, 8, 12):
					ring_um(t, bahn[i], bahn[i + 1] - bahn[i], 0.02, 0.01)
		elif tier == 6:
			k = ["recurve", "reflex", "lang"][form - 1]
			bahn = _arm_bahn(KURVEN[k], s)
			strang(t, bahn, lambda u: 0.036 - 0.02 * u, lambda u: 0.024 - 0.012 * u, mat, n=6)
			if form == 1:  # Dornen nach vorn
				for i in (3, 6, 9, 12):
					p = bahn[i]
					stachel(t, p, p + Vector((0, -0.05, s * 0.025)), 0.007)
			elif form == 2:  # Horn: dicker, gerippt
				for i in range(2, 16, 2):
					ring_um(t, bahn[i], bahn[i + 1] - bahn[i], 0.024 - 0.0008 * i, 0.006, "beschlag")
			else:  # Klingen an der Vorderkante
				pts = [p + Vector((0, -0.02, 0)) for p in bahn[3:14]]
				strang(t, pts, lambda u: 0.006, lambda u: 0.03 * math.sin(math.pi * u), "klinge", n=4, quer=Vector((0, 1, 0)), eckig=True)
			stachel(t, bahn[-1], bahn[-1] + Vector((0, -0.02, s * 0.06)), 0.008)


def _nocke(t, s, material, gross=False):
	"""Kappe an der Spitze des Wurfarms, in der die Sehne sitzt."""
	r = 0.011 if not gross else 0.014
	drehkoerper(t, [(0, -r * 1.5), (r, -r), (r * 0.9, r * 0.5), (0, r * 1.6)], material, n=8, versatz=Vector((0, SPITZE_Y, s * (SPITZE_Z - 0.01))))


def ring_um(t, p, richtung, r, h, material="beschlag", n=10):
	"""Ring um eine Bahn an Punkt p."""
	d = richtung.normalized()
	rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
	m = Matrix.Translation(p) @ rot
	loft(t, [(m @ Matrix.Translation((0, 0, -h / 2)), kreis(r, n)), (m, kreis(r * 1.12, n)), (m @ Matrix.Translation((0, 0, h / 2)), kreis(r, n))], material)


def bogengriff(t, tier, form):
	mat = HOLZ[tier]
	if tier == 3:
		quader(t, (0, 0.005, 0), (0.034, 0.04, 0.2), mat, fase=0.008)
		quader(t, (0, 0.007, 0), (0.038, 0.042, 0.1), "leder", fase=0.008)
		return
	drehkoerper(t, [(0.016, -0.11), (0.02, -0.09), (0.022, 0.0), (0.02, 0.09), (0.016, 0.11)], mat, n=10)
	if tier == 4:
		wicklung(t, -0.06, 0.06, 0.025, windungen=4, tiefe=0.003, n=9)
		for z in (-0.06, 0.06):
			ring(t, z, 0.026, 0.008, material="dunkel", n=9, wulst=0.05)
	else:
		wicklung(t, -0.055, 0.055, 0.0235, windungen=8)
		mz = {1: "dunkel", 2: "beschlag", 5: "beschlag", 6: "beschlag"}[tier]
		for z in (-0.06, 0.06):
			ring(t, z, 0.024, 0.008, material=mz, wulst=0.25)
		if tier == 2:
			edelstein(t, Vector((0, -0.022, 0.08)), 0.008, "stein", achse=Vector((0, -1, 0)))
		if tier == 5:
			scheibe(t, (0, -0.02, 0.085), 0.016, 0.01, strahlen=8)
		if tier == 6:
			for z in (-0.06, 0.06):
				stachel(t, (0, -0.02, z), (0, -0.05, z * 1.2), 0.006)
	# Pfeilauflage
	quader(t, (0.018, -0.005, 0.07), (0.01, 0.02, 0.012), "leder")


def sehne(t, tier, form):
	"""Sehne zwischen den Wurfarm-Enden (vom Bogen und, gedreht und verkürzt, von der Armbrust)."""
	a, b = Vector((0, SPITZE_Y, -SPITZE_Z + 0.01)), Vector((0, SPITZE_Y, SPITZE_Z - 0.01))
	mat = {1: "sehne", 2: "sehne", 3: "beschlag", 4: "sehne", 5: "beschlag", 6: "dunkel"}[tier]
	strang(t, [a, b], 0.004, 0.004, mat, n=5)
	if tier in (2, 5):  # umwickelte Mitte
		strang(t, [Vector((0, SPITZE_Y, -0.06)), Vector((0, SPITZE_Y, 0.06))], 0.0065, 0.0065, "beschlag" if tier == 5 else "stoff", n=6)
	elif tier == 4:  # Perlen aus Eis
		for z in (-0.4, 0.4):
			rohling(t, (0, SPITZE_Y, z), (0.02, 0.014, 0.014), "eis", saat=int(z * 10 + 5), achse="z")
	elif tier == 6:  # glühender zweiter Strang
		strang(t, [a + Vector((0.003, 0, 0)), b + Vector((0.003, 0, 0))], 0.002, 0.002, "leucht", n=4)


# ================================================================ Armbrust


def armbrustbogen(t, tier, form):
	"""Querliegender Bogen vorn am Schaft: ein Wurfarm-Paar, gedreht und verkleinert."""
	n0 = anzahl(t)
	wurfarme(t, tier, form)
	s = 0.4 / (SPITZE_Z - 0.0)
	for v in neue_verts(t, n0):
		x, y, z = v.co
		v.co = Vector((z * s * 1.0, -0.42 + y * 0.56, 0.03 - x))
	# Halterung am Schaft
	m = "beschlag" if tier != 4 else "eis"
	quader(t, (0, -0.42, 0.03), (0.08, 0.05, 0.05), m, fase=0.008)


def armbrustschaft(t, tier, form):
	mat = {1: "holz", 2: "holz", 3: "holz", 4: "holz", 5: "stoff", 6: "beschlag"}[tier]
	# Schaft als Loft entlang -Y: Querschnitte (Breite x, Höhe z)
	def schnitt(b, h, z0=0.0):
		f = min(b, h) * 0.25
		return [(b, z0 - h + f), (b, z0 + h - f), (b - f, z0 + h), (-b + f, z0 + h), (-b, z0 + h - f), (-b, z0 - h + f), (-b + f, z0 - h), (b - f, z0 - h)]
	profil = [(0.2, 0.026, 0.05, -0.03), (0.12, 0.02, 0.035, -0.015), (0.04, 0.019, 0.03, 0.0), (-0.1, 0.022, 0.028, 0.01), (-0.46, 0.022, 0.022, 0.015)]
	if form == 2:  # Kolben mit Wange, schlanker vorne
		profil = [(0.22, 0.03, 0.06, -0.04), (0.14, 0.024, 0.04, -0.02), (0.04, 0.018, 0.026, 0.0), (-0.12, 0.02, 0.024, 0.012), (-0.46, 0.018, 0.02, 0.016)]
	schnitte = [(Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"), [(a, c) for a, c in schnitt(b, h, z0)]) for y, b, h, z0 in profil]
	loft(t, schnitte, mat if tier != 4 else "holz")
	# Rinne für den Bolzen und Nuss
	quader(t, (0, -0.2, 0.04), (0.012, 0.5, 0.006), "beschlag")
	drehkoerper(t, [(0.012, -0.008), (0.012, 0.008)], "beschlag", n=8, versatz=Vector((0, -0.12, 0.042)))
	# Abzug
	strang(t, [Vector((0, -0.02, -0.01)), Vector((0, 0.0, -0.06)), Vector((0, 0.03, -0.09))], 0.008, 0.004, "beschlag", n=4)
	if tier == 2:
		for y in (-0.3, 0.1):
			quader(t, (0, y, 0.0), (0.05, 0.02, 0.06), "beschlag", fase=0.005)
		edelstein(t, Vector((0.024, 0.15, -0.03)), 0.01, "stein", achse=Vector((1, 0, 0)))
		edelstein(t, Vector((-0.024, 0.15, -0.03)), 0.01, "stein", achse=Vector((-1, 0, 0)))
	elif tier == 3:
		for y in (-0.35, -0.2, 0.1):
			quader(t, (0, y, 0.005), (0.05, 0.015, 0.058), "beschlag")
	elif tier == 4:
		for y in (-0.38, -0.05, 0.16):
			rohling(t, (0, y, 0.0), (0.06, 0.06, 0.08), "eis", saat=int(y * 100) + 200, rauh=0.2)
	elif tier == 5:
		for s in (1, -1):
			for i in range(3):
				b = Vector((s * 0.02, 0.16, -0.02))
				feder(t, b, b + Vector((s * 0.04, 0.06 + 0.02 * i, -0.02 - 0.03 * i)), 0.02, 0.005, quer=Vector((1, 0, 0)))
		for y in (-0.3, 0.05):
			quader(t, (0, y, 0.0), (0.05, 0.015, 0.06), "beschlag", fase=0.006)
	elif tier == 6:
		for y in (-0.36, -0.2, 0.0, 0.15):
			stachel(t, (0, y, -0.02), (0, y + 0.03, -0.07), 0.008)
		strang(t, [Vector((0.023, -0.4, 0.02)), Vector((0.023, 0.1, 0.0))], 0.006, 0.002, "leucht", n=4, quer=Vector((1, 0, 0)))
		strang(t, [Vector((-0.023, -0.4, 0.02)), Vector((-0.023, 0.1, 0.0))], 0.006, 0.002, "leucht", n=4, quer=Vector((1, 0, 0)))


# ================================================================ Muskete


def musketenschaft(t, tier, form):
	mat = {1: "holz", 2: "holz", 3: "holz", 4: "holz", 5: "stoff", 6: "beschlag"}[tier]
	def schnitt(b, h, z0=0.0):
		f = min(b, h) * 0.35
		return [(b, z0 - h + f), (b, z0 + h - f), (b - f, z0 + h), (-b + f, z0 + h), (-b, z0 + h - f), (-b, z0 - h + f), (-b + f, z0 - h), (b - f, z0 - h)]
	if form == 1:  # klassischer Kolben
		profil = [(0.32, 0.02, 0.07, -0.08), (0.22, 0.019, 0.05, -0.06), (0.08, 0.016, 0.03, -0.02), (0.0, 0.017, 0.028, 0.0),
				  (-0.1, 0.02, 0.022, 0.02), (-0.62, 0.016, 0.016, 0.022)]
	else:  # Pistolengriff
		profil = [(0.3, 0.022, 0.06, -0.04), (0.18, 0.02, 0.035, -0.02), (0.06, 0.018, 0.026, 0.0), (0.0, 0.02, 0.026, 0.01),
				  (-0.1, 0.02, 0.022, 0.02), (-0.62, 0.016, 0.016, 0.022)]
		strang(t, [Vector((0, 0.04, -0.01)), Vector((0, 0.06, -0.08)), Vector((0, 0.08, -0.12))], 0.034, 0.03, mat, n=8)
	schnitte = [(Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"), schnitt(b, h, z0)) for y, b, h, z0 in profil]
	loft(t, schnitte, mat)

	def bei(y):
		"""Breite, Höhe und Mitte (z) des Schafts an Stelle y."""
		for (ya, ba, ha, za), (yb, bb, hb, zb) in zip(profil, profil[1:]):
			if yb <= y <= ya:
				u = (ya - y) / (ya - yb)
				return ba + (bb - ba) * u, ha + (hb - ha) * u, za + (zb - za) * u
		return profil[-1][1:]
	# Abzugsbügel
	strang(t, [Vector((0, -0.06, -0.02)) + Vector((0, 0.05 * (1 - math.cos(a)), -0.03 * math.sin(a))) for a in [math.pi * i / 10 for i in range(11)]], 0.006, 0.006, "beschlag", n=5)
	strang(t, [Vector((0, -0.03, -0.02)), Vector((0, -0.025, -0.045))], 0.006, 0.003, "beschlag", n=4)
	# Kolbenkappe
	y_ende = profil[0][0]
	b, h, zm = bei(y_ende)
	quader(t, (0, y_ende + 0.002, zm), (2 * b + 0.002, 0.008, 2 * h + 0.002), "beschlag")
	if tier == 2:
		for y in (0.15, 0.25):
			b, h, zm = bei(y)
			quader(t, (0, y, zm), (2 * b + 0.004, 0.006, 2 * h + 0.004), "beschlag")
		b, h, zm = bei(0.2)
		edelstein(t, Vector((b + 0.001, 0.2, zm)), 0.012, "stein", achse=Vector((1, 0, 0)))
		edelstein(t, Vector((-b - 0.001, 0.2, zm)), 0.012, "stein", achse=Vector((-1, 0, 0)))
	elif tier == 3:
		for y in (-0.5, -0.3, 0.2):
			b, h, zm = bei(y)
			quader(t, (0, y, zm + (0.01 if y < 0 else 0)), (2 * b + 0.006, 0.014, 2 * h + 0.006 + (0.02 if y < 0 else 0)), "beschlag")
	elif tier == 4:
		for y in (-0.55, 0.25):
			b, h, zm = bei(y)
			rohling(t, (0, y, zm), (0.05, 2 * b + 0.016, 2 * h + 0.016), "eis", saat=int(y * 100) + 300, rauh=0.2, achse="y")
	elif tier == 5:
		_, h, zm = bei(0.26)
		for s in (1, -1):
			for i in range(3):
				b = Vector((s * 0.02, 0.26, zm + h * 0.3))
				feder(t, b, b + Vector((s * 0.03, 0.02 + 0.02 * i, 0.04 - 0.04 * i)), 0.022, 0.005, quer=Vector((1, 0, 0)))
		for y in (-0.5, -0.2):
			ring_um(t, Vector((0, y, 0.022)), Vector((0, 1, 0)), 0.02, 0.012)
	elif tier == 6:
		for y in (-0.4, -0.2, 0.1, 0.25):
			_, h, zm = bei(y)
			stachel(t, (0, y, zm - h + 0.004), (0, y + 0.03, zm - h - 0.045), 0.008)


def musketenlauf(t, tier, form):
	z = 0.035
	y0, y1 = -0.02, -1.02
	ach = lambda y: Matrix.Translation((0, y, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
	if tier == 3:
		n, ph = (6, 0.0) if form == 1 else (4, math.pi / 4)
		loft(t, [(ach(y0), kreis(0.018, n, phase=ph)), (ach(y1), kreis(0.016, n, phase=ph))], "klinge")
		for y in (-0.2, -0.5, -0.8, -1.0):
			loft(t, [(ach(y + 0.008), kreis(0.021, n, phase=ph)), (ach(y - 0.008), kreis(0.021, n, phase=ph))], "beschlag")
		return
	if tier == 4:
		for i in range(5):
			ya, yb = y0 + (y1 - y0) * i / 5, y0 + (y1 - y0) * (i + 1) / 5
			rohling(t, (0, (ya + yb) / 2, z), (abs(yb - ya) * 1.03, 0.04, 0.042), "eis", saat=400 + i * 3 + form, rauh=0.12, achse="y")
		loft(t, [(ach(y1 + 0.03), kreis(0.012, 6)), (ach(y1 - 0.005), kreis(0.012, 6))], "dunkel")
		return
	mat = {1: "klinge", 2: "klinge", 5: "klinge", 6: "klinge"}[tier]
	profil = [(y0, 0.019), (-0.3, 0.018), (y1 + 0.06, 0.016), (y1 + 0.03, 0.017)]
	if tier == 1 and form == 2 or tier == 2 and form == 1:  # Trichtermündung
		profil += [(y1 + 0.01, 0.022), (y1, 0.026)]
	elif tier == 6:
		profil += [(y1, 0.02)]
	else:
		profil += [(y1, 0.019)]
	loft(t, [(ach(y), kreis(r, 12, phase=math.pi / 12 if tier == 1 and form == 1 else 0)) for y, r in profil], mat)
	loft(t, [(ach(y1 + 0.001), kreis(0.011, 10)), (ach(y1 + 0.05), kreis(0.011, 10))], "dunkel", kappe_unten=False)  # Mündung innen
	if tier == 2:
		for y in (-0.15, -0.45, -0.75):
			ring_um(t, Vector((0, y, z)), Vector((0, 1, 0)), 0.02, 0.012)
		if form == 2:
			pts = [Vector((math.cos(a) * 0.0195, -0.1 - 0.85 * i / 60, z + math.sin(a) * 0.0195)) for i, a in enumerate([i * 0.6 for i in range(61)])]
			strang(t, pts, 0.003, 0.002, "beschlag", n=4)
	elif tier == 5:
		for y in (-0.2, -0.6):
			ring_um(t, Vector((0, y, z)), Vector((0, 1, 0)), 0.021, 0.014)
		for s in (1, -1):  # Flügelflossen an der Mündung
			for i in range(3):
				b = Vector((s * 0.015, y1 + 0.08 + 0.03 * i, z))
				feder(t, b, b + Vector((s * 0.05, 0.05, 0.01 * i)), 0.018, 0.004, quer=Vector((0, 0, 1)))
		if form == 2:
			scheibe(t, (0, -0.06, z + 0.022), 0.014, 0.008, strahlen=8)
	elif tier == 6:
		for y in (-0.25, -0.55, -0.85):
			for k in range(3):
				a = 2 * math.pi * k / 3 + y * 5
				r = Vector((math.cos(a), 0, math.sin(a)))
				stachel(t, Vector((0, y, z)) + r * 0.016, Vector((0, y + 0.02, z)) + r * 0.04, 0.005)
		for k in range(4 if form == 1 else 6):
			a = 2 * math.pi * k / (4 if form == 1 else 6)
			r = Vector((math.cos(a), 0, math.sin(a)))
			stachel(t, Vector((0, y1 + 0.01, z)) + r * 0.016, Vector((0, y1 - 0.04, z)) + r * 0.03, 0.006)
		strang(t, [Vector((0, -0.1, z + 0.019)), Vector((0, -0.9, z + 0.017))], 0.004, 0.002, "leucht", n=4, quer=Vector((0, 0, 1)))
	if tier == 1:
		for y in (-0.3, -0.7):
			ring_um(t, Vector((0, y, z)), Vector((0, 1, 0)), 0.019, 0.01, "beschlag")


def schloss(t, tier, form):
	"""Steinschloss rechts am Schaft: Platte, Hahn, Pfanne."""
	x = 0.022
	mat = {1: "beschlag", 2: "beschlag", 3: "beschlag", 4: "eis", 5: "beschlag", 6: "beschlag"}[tier]
	if tier == 3:
		quader(t, (x, -0.0, 0.01), (0.006, 0.11, 0.03), mat)
		quader(t, (x + 0.008, 0.03, 0.04), (0.008, 0.012, 0.05), mat)
	elif tier == 4:
		rohling(t, (x + 0.004, 0.0, 0.01), (0.11, 0.012, 0.035), "eis", saat=500, rauh=0.2)
		kristall(t, (x + 0.008, 0.03, 0.02), (0, -0.5, 1), 0.05, 0.007, "eis")
	else:
		pts = [(0.055, -0.012), (0.05, 0.012), (0.0, 0.016), (-0.05, 0.012), (-0.055, -0.01), (0.0, -0.014)]
		m = Matrix.Translation((x, 0, 0.012)) @ Matrix.Rotation(math.radians(90), 4, "Y")
		loft(t, [(m, [(-zz, yy) for yy, zz in pts]), (m @ Matrix.Translation((0, 0, 0.005)), [(-zz, yy) for yy, zz in pts])], mat)
		# Hahn
		hahn = [Vector((x + 0.008, 0.035, 0.005)), Vector((x + 0.008, 0.04, 0.03)), Vector((x + 0.008, 0.025, 0.05)), Vector((x + 0.008, 0.008, 0.052))]
		strang(t, hahn, 0.008, 0.005, mat, n=4, quer=Vector((1, 0, 0)))
		quader(t, (x + 0.006, -0.012, 0.03), (0.01, 0.012, 0.02), mat)  # Batterie
		quader(t, (x + 0.01, -0.0, 0.022), (0.012, 0.016, 0.006), mat)  # Pfanne
		if tier == 2:
			strang(t, [Vector((x + 0.004, -0.04, 0.012)), Vector((x + 0.004, -0.02, 0.016))], 0.004, 0.002, "beschlag", n=4)
			edelstein(t, Vector((x + 0.006, -0.035, 0.012)), 0.006, "stein", achse=Vector((1, 0, 0)))
		elif tier == 5:
			feder(t, Vector((x + 0.008, 0.04, 0.035)), Vector((x + 0.008, 0.08, 0.06)), 0.014, 0.004, quer=Vector((1, 0, 0)))
		elif tier == 6:
			stachel(t, (x + 0.008, 0.025, 0.05), (x + 0.008, 0.01, 0.085), 0.005)
			edelstein(t, Vector((x + 0.006, -0.035, 0.012)), 0.006, "stein", achse=Vector((1, 0, 0)), n=4)


# ================================================================ Geschosse


def pfeil(t, tier, form, laenge=0.7, bolzen=False):
	"""Pfeil bzw. Bolzen im Klingen-Rahmen: Spitze bei +Z, Mitte am Ursprung."""
	h = laenge / 2
	r = 0.0045 if not bolzen else 0.007
	schaft = {1: "holz", 2: "holz", 3: "klinge", 4: "holz", 5: "stoff", 6: "beschlag"}[tier]
	drehkoerper(t, [(r, -h), (r, h - 0.05)], schaft, n=6)
	kopf = "eis" if tier == 4 else "klinge"
	z0 = h - 0.055
	if tier == 1:
		drehkoerper(t, [(r * 1.3, z0), (r * 1.3, z0 + 0.02)], "klinge", n=6)
		strang(t, [Vector((0, 0, z0 + 0.015)), Vector((0, 0, h + 0.03))], lambda u: 0.024 * (1 - u ** 1.5) + 0.002, 0.003, kopf, n=4, eckig=True)
	elif tier == 2:
		drehkoerper(t, [(r * 1.4, z0), (r * 1.5, z0 + 0.01), (r * 1.3, z0 + 0.02)], "beschlag", n=8)
		strang(t, [Vector((0, 0, z0 + 0.015)), Vector((0, 0, h + 0.04))], lambda u: 0.022 * math.sin(math.pi * (0.25 + 0.75 * u)) + 0.001, 0.004, kopf, n=6)
	elif tier == 3:
		strang(t, [Vector((0, 0, z0)), Vector((0, 0, h + 0.04))], lambda u: 0.012 * (1 - u), lambda u: 0.012 * (1 - u), kopf, n=4, eckig=True)
	elif tier == 4:
		kristall(t, (0, 0, z0), (0, 0, 1), 0.09, 0.008, "eis", spitze_anteil=0.5)
	elif tier == 5:
		drehkoerper(t, [(r * 1.4, z0), (r * 1.6, z0 + 0.012), (r * 1.3, z0 + 0.02)], "beschlag", n=8)
		strang(t, [Vector((0, 0, z0 + 0.015)), Vector((0, 0, h + 0.035))], lambda u: 0.02 * math.sin(math.pi * (0.4 + 0.6 * u)) + 0.001, 0.004, kopf, n=8)
	elif tier == 6:
		strang(t, [Vector((0, 0, z0 + 0.01)), Vector((0, 0, h + 0.04))], lambda u: 0.022 * (1 - u) + 0.001, 0.004, kopf, n=4, eckig=True)
		for s in (1, -1):
			stachel(t, (s * 0.008, 0, z0 + 0.02), (s * 0.018, 0, z0 - 0.01), 0.003)
	# Befiederung: drei Fahnen
	fmat = {1: "stoff", 2: "stoff", 3: "beschlag", 4: "eis", 5: "stoff", 6: "beschlag"}[tier]
	lf = 0.12 if not bolzen else 0.07
	for k in range(3):
		a = 2 * math.pi * k / 3
		d = Vector((math.cos(a), math.sin(a), 0))
		pts = [Vector((0, 0, -h + 0.02 + lf * i / 6)) + d * (r + 0.001) for i in range(7)]
		wf = (lambda u: 0.022 * math.sin(math.pi * min(u * 1.1, 1.0)) ** 0.7 + 0.002) if tier != 3 else (lambda u: 0.02)
		strang(t, pts, wf, 0.001, fmat, n=4, quer=Vector((-math.sin(a), math.cos(a), 0)))
	drehkoerper(t, [(r * 1.1, -h - 0.004), (r * 1.1, -h + 0.012)], "beschlag" if tier != 1 else "holz", n=6)


ARTEN = {
	"wurfarme": {tier: (3, umrechnen((lambda tr: lambda t, form: wurfarme(t, tr, form))(tier))) for tier in range(1, 7)},
	"bogengriff": {tier: (1, umrechnen((lambda tr: lambda t, form: bogengriff(t, tr, form))(tier))) for tier in range(1, 7)},
	"sehne": {tier: (1, umrechnen((lambda tr: lambda t, form: sehne(t, tr, form))(tier))) for tier in range(1, 7)},
	"armbrustbogen": {tier: (2, umrechnen((lambda tr: lambda t, form: armbrustbogen(t, tr, form))(tier))) for tier in range(1, 7)},
	"armbrustschaft": {tier: (2, umrechnen((lambda tr: lambda t, form: armbrustschaft(t, tr, form))(tier))) for tier in range(1, 7)},
	"musketenschaft": {tier: (2, umrechnen((lambda tr: lambda t, form: musketenschaft(t, tr, form))(tier))) for tier in range(1, 7)},
	"musketenlauf": {tier: (2, umrechnen((lambda tr: lambda t, form: musketenlauf(t, tr, form))(tier))) for tier in range(1, 7)},
	"schloss": {tier: (1, umrechnen((lambda tr: lambda t, form: schloss(t, tr, form))(tier))) for tier in range(1, 7)},
	"pfeil": {tier: (1, (lambda tr: lambda t, form: pfeil(t, tr, form))(tier)) for tier in range(1, 7)},
	"bolzen": {tier: (1, (lambda tr: lambda t, form: pfeil(t, tr, form, 0.42, True))(tier)) for tier in range(1, 7)},
}
