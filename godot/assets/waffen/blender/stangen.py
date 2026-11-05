"""Module der Stangenwaffen (Axt, Hammer, Speer) in den 6 Tier-Stilen.
Maße (z entlang des Schafts, Hand am Ursprung):
  Stiel (Axt/Hammer) von -0,3 bis 0,8, Kopf um z = 0,72
  Speerschaft von -0,7 bis 1,5, Spitze ab 1,5
  Schaftende: Oberkante bei z = 0, hängt nach unten (Godot setzt es ans Schaftende)
"""
import math
from mathutils import Vector, Matrix
from geo import *
import schwert
from schwert import spitze, linear_spitz

S0, S1 = -0.3, 0.8   # Stiel
KZ = 0.72            # Kopfmitte
SR = 0.019           # Stielradius
P0, P1 = -0.7, 1.5   # Speerschaft
PR = 0.016


# ================================================================ Stiele


def stiel(t, tier, form, z0=S0, z1=S1, r=SR):
	"""Stiel bzw. Schaft im Stil des Tiers. Unten ein Griffbereich."""
	g1 = z0 + 0.32 * (z1 - z0) / 1.1  # obere Kante der Griffwicklung (nur kurze Stiele)
	lang = z1 - z0 > 1.5
	if lang:
		g1 = z0 + 0.25
	oval = 0.85
	if tier == 1:
		drehkoerper(t, [(r * 0.95, z0), (r, (z0 + z1) / 2), (r * 0.92, z1)], "holz", n=10)
		wicklung(t, z0 + 0.02, g1, r * 1.08, windungen=max(6, round((g1 - z0) / 0.025)))
		if form == 2:  # eiserne Schienen unter dem Kopf
			for s in (1, -1):
				quader(t, (0, s * r * 0.95, z1 - 0.12), (r * 0.8, 0.003, 0.22), "beschlag")
	elif tier == 2:
		drehkoerper(t, [(r, z0), (r, z1)], "holz", n=12)
		if form == 1:
			wicklung(t, z0 + 0.02, g1, r * 1.06, material="beschlag", windungen=max(16, round((g1 - z0) / 0.009)), tiefe=0.0012, n=10)
		else:
			wicklung(t, z0 + 0.02, g1, r * 1.08)
			for z in [z1 - 0.2, z1 - 0.32, (g1 + z1) / 2]:
				ring(t, z, r * 1.08, 0.008, wulst=0.25)
		for z in (z0 + 0.02, g1):
			ring(t, z, r * 1.12, 0.012, wulst=0.3)
	elif tier == 3:
		n, ph = (8, math.pi / 8) if form == 1 else (4, math.pi / 4)
		rr = r if form == 1 else r * 1.1
		drehkoerper(t, [(rr, z0), (rr, z1)], "holz" if form == 1 else "beschlag", n=n, phase=ph)
		drehkoerper(t, [(rr * 1.06, z0 + 0.02), (rr * 1.06, g1)], "leder", n=n, phase=ph)
		schritt = 0.18 if not lang else 0.3
		z = g1
		while z < z1 - 0.05:
			drehkoerper(t, [(rr * 1.12, z - 0.006), (rr * 1.12, z + 0.006)], "beschlag", n=n, phase=ph)
			z += schritt
	elif tier == 4:
		if form == 1:  # knorriges Holz mit Fellwicklung
			import random
			rng = random.Random(5)
			k_max = 12 if not lang else 20
			profil = [(r * (0.92 + rng.uniform(0, 0.16)), z0 + (z1 - z0) * k / k_max) for k in range(k_max + 1)]
			drehkoerper(t, profil, "holz", n=7)
			wicklung(t, z0 + 0.02, g1, r * 1.12, windungen=5, tiefe=0.003, n=9)
			for z in (z0 + 0.03, g1, z1 - 0.15):
				ring(t, z, r * 1.2, 0.01, material="dunkel", n=9, wulst=0.05)
		else:  # Eissäule aus Segmenten
			n = max(4, round((z1 - z0) / 0.16))
			h = (z1 - z0) / n
			for i in range(n):
				rohling(t, (0, 0, z0 + h * (i + 0.5)), (h * 1.04, r * 2.1, r * 2.2), "eis", saat=60 + i, rauh=0.12, n=6, schritte=3, achse="z")
			wicklung(t, z0 + 0.02, g1, r * 1.18, windungen=5, tiefe=0.003, n=9)
	elif tier == 5:
		drehkoerper(t, [(r, z0), (r, z1)], "stoff", n=12)  # helles, geweihtes Holz
		wicklung(t, z0 + 0.02, g1, r * 1.08)
		if form == 1:  # goldene Spirale
			l = z1 - g1
			w = l / 0.12
			m = int(w * 14)
			pts = [Vector((math.cos(a) * r * 1.04, math.sin(a) * r * 1.04, g1 + l * i / m)) for i, a in enumerate([w * 2 * math.pi * i / m for i in range(m + 1)])]
			strang(t, pts, 0.005, 0.003, "beschlag", n=6)
		else:  # Goldbänder mit kleinen Federn unter dem Kopf
			for z in (g1, (g1 + z1) / 2, z1 - 0.18):
				ring(t, z, r * 1.1, 0.012, wulst=0.3)
			for s in (1, -1):
				b = Vector((s * r, 0, z1 - 0.2))
				feder(t, b, b + Vector((s * 0.03, 0, -0.08)), 0.012, 0.004, bauch=0.004 * s)
		for z in (z0 + 0.02, g1):
			ring(t, z, r * 1.12, 0.012, wulst=0.3)
	elif tier == 6:
		if form == 1:  # schwarz mit Dornenringen
			drehkoerper(t, [(r, z0), (r, z1)], "beschlag", n=6)
			wicklung(t, z0 + 0.02, g1, r * 1.06, windungen=max(9, round((g1 - z0) / 0.016)), tiefe=0.002)
			z = g1
			while z < z1 - 0.05:
				drehkoerper(t, [(r * 1.1, z - 0.006), (r * 1.18, z), (r * 1.1, z + 0.006)], "beschlag", n=6)
				for k in range(3):
					a = 2 * math.pi * k / 3 + z * 30
					rv = Vector((math.cos(a), math.sin(a), 0))
					stachel(t, Vector((0, 0, z)) + rv * r, Vector((0, 0, z - 0.012)) + rv * r * 2.0, 0.004)
				z += 0.2 if not lang else 0.35
		else:  # verdrillter Schaft
			k_max = int((z1 - z0) / 0.01)
			schnitte = []
			for k in range(k_max + 1):
				z = z0 + (z1 - z0) * k / k_max
				a = z * 18
				rr = [r * (1.2 if i % 2 == 0 else 0.8) for i in range(6)]
				schnitte.append((z, [(math.cos(a + math.pi * i / 3) * rr[i], math.sin(a + math.pi * i / 3) * rr[i]) for i in range(6)]))
			loft(t, schnitte, "beschlag")
			wicklung(t, z0 + 0.02, g1, r * 1.12, windungen=max(9, round((g1 - z0) / 0.016)), tiefe=0.002)


def stiel_modul(tier):
	return lambda t, form: stiel(t, tier, form)


def speerschaft_modul(tier):
	return lambda t, form: stiel(t, tier, form, P0, P1, PR)


# ================================================================ Schaftenden


def schaftende_modul(tier):
	"""Schaftenden im Stil der Knäufe des Tiers, Oberkante auf z = 0."""
	f = schwert.KNAEUFE[tier - 1]
	def bauen(t, form):
		n0 = anzahl(t)
		f(t, form)
		for v in neue_verts(t, n0):
			v.co = Vector((v.co.x * 1.15, v.co.y * 1.15, (v.co.z - schwert.KN) * 1.1))
		drehkoerper(t, [(SR * 1.1, -0.004), (SR * 1.15, 0.0), (SR * 1.1, 0.03)], "beschlag", n=12)
	return bauen


# ================================================================ Axtköpfe


def _blatt(t, x0, x1, oben, unten, dicke, material="klinge", schritte=14, rauh=0.0, saat=1, seite=1):
	"""Axtblatt von x0 (am Stiel) nach x1 (Schneide). oben/unten/dicke: Funktionen von u (0..1) -> z bzw. Dicke.
	seite=-1 spiegelt nach -X."""
	import random
	rng = random.Random(saat)
	schnitte = []
	for k in range(schritte + 1):
		u = k / schritte
		x = (x0 + (x1 - x0) * u) * seite
		zt, zb, d = oben(u), unten(u), dicke(u) / 2
		f = min(d, (zt - zb) * 0.3)
		pts = [(-zb, 0), (-(zb + f), d), (-(zt - f), d), (-zt, 0), (-(zt - f), -d), (-(zb + f), -d)]
		if rauh:
			pts = [(a * (1 + rng.uniform(-rauh, rauh) * 0.05), b * (1 + rng.uniform(-rauh, rauh))) for a, b in pts]
		m = Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, "Y")
		schnitte.append((m, pts))
	if seite < 0:
		schnitte = [(m, list(reversed(p))) for m, p in schnitte]
	loft(t, schnitte, material)


def _tuelle(t, z=KZ, h=0.13, r=SR * 1.45, material="beschlag", n=10):
	"""Auge bzw. Hülse um den Stiel."""
	drehkoerper(t, [(r * 0.9, z - h / 2), (r, z - h / 2 + 0.01), (r, z + h / 2 - 0.01), (r * 0.9, z + h / 2)], material, n=n)


def _dick(d0, d1=0.002):
	return lambda u: d0 + (d1 - d0) * u ** 0.7


def axtkopf(t, tier, form):
	mat = "eis" if tier == 4 else "klinge"
	doppel = form == 3
	seiten = (1, -1) if doppel else (1,)
	if tier == 4:
		rohling(t, (0, 0, KZ), (0.07, 0.05, 0.13), "eis", saat=7 + form, rauh=0.2, achse="z")
	else:
		_tuelle(t, n=10 if tier != 3 else 4)
	for s in seiten:
		if tier == 1:
			if form == 1:  # Bartaxt
				_blatt(t, 0.02, 0.17, lambda u: KZ + 0.04 + 0.02 * u, lambda u: KZ - 0.03 - 0.13 * u ** 2.2, _dick(0.022), mat, seite=s)
			else:  # Breitaxt
				_blatt(t, 0.02, 0.16, lambda u: KZ + 0.035 + 0.07 * u ** 2, lambda u: KZ - 0.035 - 0.07 * u ** 2, _dick(0.022), mat, seite=s)
		elif tier == 2:
			_blatt(t, 0.02, 0.19, lambda u: KZ + 0.035 + 0.1 * u ** 2.5, lambda u: KZ - 0.035 - 0.12 * u ** 2.5, _dick(0.02), mat, schritte=18, seite=s)
			for z, r0 in ((KZ + 0.06, 1), (KZ - 0.06, -1)):
				strang(t, spirale((s * 0.06, 0.012, z), 0.018, 0.004, 1.1, n=14, start=math.pi if s > 0 else 0, richtung=-s * r0, ebene="xz"),
					   0.004, 0.003, "beschlag", n=5)
				strang(t, spirale((s * 0.06, -0.012, z), 0.018, 0.004, 1.1, n=14, start=math.pi if s > 0 else 0, richtung=-s * r0, ebene="xz"),
					   0.004, 0.003, "beschlag", n=5)
			if form == 2 and not doppel:  # Schnörkeldorn hinten
				strang(t, [Vector((-0.02, 0, KZ))] + spirale((-0.06, 0, KZ + 0.02), 0.02, 0.005, 1.0, n=14, start=-math.pi / 2, richtung=-1),
					   lambda u: 0.02 * (1 - 0.6 * u), 0.012, "beschlag", n=6)
			edelstein(t, Vector((0, 0.03, KZ)), 0.009, "stein", achse=Vector((0, 1, 0)))
			edelstein(t, Vector((0, -0.03, KZ)), 0.009, "stein", achse=Vector((0, -1, 0)))
		elif tier == 3:
			if form == 1:  # rechteckiges Hackblatt
				_blatt(t, 0.02, 0.17, lambda u: KZ + 0.05, lambda u: KZ - 0.05 - 0.06 * u, _dick(0.026, 0.004), mat, schritte=2, seite=s)
			else:  # Trapez
				_blatt(t, 0.02, 0.17, lambda u: KZ + 0.035 + 0.06 * u, lambda u: KZ - 0.035 - 0.06 * u, _dick(0.026, 0.004), mat, schritte=2, seite=s)
		elif tier == 4:
			if form == 1:  # geschlagene Steinaxt
				_blatt(t, 0.025, 0.17, lambda u: KZ + 0.04 + 0.04 * u, lambda u: KZ - 0.045 - 0.06 * u, _dick(0.04, 0.006), mat, schritte=5, rauh=0.5, saat=3, seite=s)
			else:  # Kristallkeil
				_blatt(t, 0.025, 0.19, lambda u: KZ + 0.03 + 0.08 * u, lambda u: KZ - 0.03 - 0.02 * u, _dick(0.035, 0.004), mat, schritte=4, rauh=0.4, saat=9, seite=s)
				kristall(t, (s * 0.03, 0, KZ + 0.04), (s * 0.4, 0, 1), 0.08, 0.01, "eis")
		elif tier == 5:
			if form == 1:  # Flügelblatt: Federn bilden die Schneide
				_blatt(t, 0.02, 0.09, lambda u: KZ + 0.035 + 0.02 * u, lambda u: KZ - 0.035 - 0.02 * u, _dick(0.02, 0.012), mat, schritte=3, seite=s)
				for i in range(7):
					w = math.radians(66 - 22 * i)
					b = Vector((s * 0.07, 0, KZ))
					feder(t, b, b + Vector((s * math.cos(w) * 0.13, 0, math.sin(w) * 0.13)), 0.03, 0.008, mat if i % 2 else "beschlag",
						  bauch=0.01 * s * (1 if w > 0 else -1))
			else:  # runder Halbmond mit Sonnenscheibe
				_blatt(t, 0.02, 0.17, lambda u: KZ + 0.035 + 0.11 * math.sin(u * math.pi / 2) ** 3, lambda u: KZ - 0.035 - 0.11 * math.sin(u * math.pi / 2) ** 3,
					   _dick(0.022), mat, schritte=16, seite=s)
				scheibe(t, (s * 0.045, 0, KZ), 0.028, 0.03, strahlen=10, strahl_laenge=0.3)
		elif tier == 6:
			if form == 1:  # gezackte Schneide mit Haken
				def oben(u): return KZ + 0.04 + 0.08 * u ** 2 + 0.02 * ((u * 5) % 1.0) * (u > 0.3)
				def unten(u): return KZ - 0.04 - 0.14 * u ** 1.5 - 0.03 * ((u * 6 + 0.5) % 1.0) * (u > 0.3)
				_blatt(t, 0.02, 0.18, oben, unten, _dick(0.024, 0.003), mat, schritte=40, seite=s)
			else:  # Sichel mit Dorn hinten
				_blatt(t, 0.02, 0.15, lambda u: KZ + 0.03 + 0.16 * u ** 3, lambda u: KZ - 0.03 - 0.09 * u ** 2, _dick(0.024, 0.003), mat, schritte=16, seite=s)
				if not doppel:
					stachel(t, (-0.02, 0, KZ), (-0.14, 0, KZ - 0.04), 0.016, kruemmung=(0, 0, 0.03))
			stachel(t, (0, 0, KZ + 0.06), (0, 0, KZ + 0.16), 0.012) if s == 1 else None
			strang(t, [Vector((s * 0.04, 0.012, KZ - 0.02)), Vector((s * 0.13, 0.012, KZ - 0.005))], 0.005, 0.002, "leucht", n=4)
			strang(t, [Vector((s * 0.04, -0.012, KZ - 0.02)), Vector((s * 0.13, -0.012, KZ - 0.005))], 0.005, 0.002, "leucht", n=4)
	if tier == 1 and doppel is False and form == 1:
		quader(t, (-0.03, 0, KZ), (0.03, 0.03, 0.05), "klinge", fase=0.006)  # stumpfer Nacken


# ================================================================ Hammerköpfe


def hammerkopf(t, tier, form):
	if tier == 1:
		if form == 1:  # Vierkantblock
			quader(t, (0, 0, KZ), (0.17, 0.06, 0.07), "klinge", fase=0.01)
		elif form == 2:  # Block mit Dorn hinten
			quader(t, (0.04, 0, KZ), (0.09, 0.06, 0.07), "klinge", fase=0.01)
			stachel(t, (-0.01, 0, KZ), (-0.14, 0, KZ - 0.03), 0.022, kruemmung=(0, 0, 0.015))
		else:  # Rundkopf
			_quer_zylinder(t, 0.17, 0.042, "klinge")
		_tuelle(t, r=SR * 1.3)
	elif tier == 2:
		_quer_zylinder(t, 0.16, 0.04, "klinge", n=8)
		for s in (1, -1):
			ring_x(t, s * 0.055, 0.044, 0.01)
		if form == 1:  # Flansche mit Stein
			for k in range(4):
				a = math.pi / 2 * k + math.pi / 4
				strang(t, [Vector((0, math.cos(a) * 0.04, KZ + math.sin(a) * 0.04)), Vector((0, math.cos(a) * 0.065, KZ + math.sin(a) * 0.065))], 0.03, 0.006, "beschlag", n=4, quer=Vector((1, 0, 0)))
		elif form == 2:  # Schnörkel oben
			for s in (1, -1):
				strang(t, spirale((s * 0.03, 0, KZ + 0.06), 0.018, 0.004, 1.1, n=14, start=-math.pi / 2, richtung=s), 0.008, 0.01, "beschlag", n=6)
		else:  # Rosetten an den Schlagflächen
			for s in (1, -1):
				scheibe_x(t, s * 0.082, 0.032, 0.008, strahlen=8)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.04, KZ)), 0.01, "stein", achse=Vector((0, s, 0)))
	elif tier == 3:
		if form == 1:  # großer Würfel
			quader(t, (0, 0, KZ), (0.12, 0.09, 0.1), "klinge", fase=0.008)
		elif form == 2:  # langer Balken
			quader(t, (0, 0, KZ), (0.22, 0.06, 0.06), "klinge", fase=0.006)
		else:  # Kreuz aus Blöcken
			quader(t, (0, 0, KZ), (0.2, 0.05, 0.05), "klinge", fase=0.005)
			quader(t, (0, 0, KZ), (0.06, 0.09, 0.09), "klinge", fase=0.006)
		quader(t, (0, 0, KZ), (0.048, 0.048, 0.14), "beschlag", fase=0.006)
	elif tier == 4:
		if form == 1:  # roher Eisblock
			rohling(t, (0, 0, KZ), (0.2, 0.08, 0.09), "eis", saat=12, rauh=0.25, schritte=5)
		elif form == 2:  # Kristallbündel
			rohling(t, (0, 0, KZ), (0.08, 0.06, 0.07), "eis", saat=13)
			for s in (1, -1):
				for a in (-20, 0, 20):
					w = math.radians(a)
					kristall(t, (s * 0.02, 0, KZ), (s * math.cos(w), 0.2 * math.sin(w * 3), math.sin(w)), 0.11, 0.016, "eis", spitze_anteil=0.15)
		else:  # Steinschlägel
			rohling(t, (0, 0, KZ), (0.24, 0.11, 0.11), "eis", saat=14, rauh=0.15, schritte=6, n=7)
		wicklung(t, KZ - 0.07, KZ + 0.07, SR * 1.3, windungen=4, tiefe=0.003, n=9)
	elif tier == 5:
		_quer_zylinder(t, 0.16, 0.042, "klinge", n=16, rund=True)
		if form == 1:  # Flügel an den Seiten
			for s in (1, -1):
				for i in range(3):
					w = math.radians(70 + 20 * i)
					b = Vector((s * 0.03, 0, KZ + 0.03))
					feder(t, b, b + Vector((s * math.cos(w) * 0.09, 0, math.sin(w) * 0.09)), 0.016, 0.005)
		elif form == 2:  # Sonnenscheiben als Schlagflächen
			for s in (1, -1):
				scheibe_x(t, s * 0.085, 0.04, 0.012, strahlen=12)
		else:  # Goldbänder
			for x in (-0.06, -0.02, 0.02, 0.06):
				ring_x(t, x, 0.045, 0.01)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.042, KZ)), 0.011, "stein", achse=Vector((0, s, 0)))
	elif tier == 6:
		quader(t, (0, 0, KZ), (0.15, 0.065, 0.075), "klinge", fase=0.012)
		if form == 1:  # Dornen auf den Flächen
			for s in (1, -1):
				for dy, dz in ((0.018, 0.02), (-0.018, 0.02), (0.018, -0.02), (-0.018, -0.02)):
					stachel(t, (s * 0.07, dy, KZ + dz), (s * 0.11, dy * 1.4, KZ + dz * 1.4), 0.008)
		elif form == 2:  # langer Dorn hinten, Hörner oben
			stachel(t, (-0.07, 0, KZ), (-0.22, 0, KZ - 0.06), 0.022, kruemmung=(0, 0, 0.03))
			for s in (1, -1):
				stachel(t, (s * 0.03, 0, KZ + 0.035), (s * 0.08, 0, KZ + 0.12), 0.012, kruemmung=(s * 0.02, 0, 0))
		else:  # Zackenkamm oben
			for i in range(5):
				x = -0.06 + 0.03 * i
				stachel(t, (x, 0, KZ + 0.035), (x * 1.3, 0, KZ + 0.09 + 0.02 * (i % 2)), 0.012)
		for s in (1, -1):
			strang(t, [Vector((-0.06, s * 0.0335, KZ)), Vector((0.06, s * 0.0335, KZ))], 0.006, 0.002, "leucht", n=4, quer=Vector((0, 1, 0)))


def _quer_zylinder(t, laenge, r, material, n=12, rund=False):
	"""Zylinder quer zum Stiel (entlang X) um den Kopfmittelpunkt."""
	m = Matrix.Translation((0, 0, KZ)) @ Matrix.Rotation(math.radians(90), 4, "Y")
	if rund:
		profil = [(0.0, -laenge / 2)] + [(r * math.sin(a), -laenge / 2 + r * (1 - math.cos(a)) * 0.6) for a in (0.5, 1.0, 1.57)] + \
				 [(r * math.sin(a), laenge / 2 - r * (1 - math.cos(a)) * 0.6) for a in (1.57, 1.0, 0.5)] + [(0.0, laenge / 2)]
	else:
		profil = [(r * 0.85, -laenge / 2), (r, -laenge / 2 + 0.008), (r, laenge / 2 - 0.008), (r * 0.85, laenge / 2)]
	schnitte = []
	oben = unten = None
	for rr, z in profil:
		if rr <= 1e-5:
			p = m @ Vector((0, 0, z))
			if not schnitte:
				unten = p
			else:
				oben = p
			continue
		schnitte.append((m @ Matrix.Translation((0, 0, z)), kreis(rr, n, phase=math.pi / n)))
	loft(t, schnitte, material, spitze_oben=oben, spitze_unten=unten)


def ring_x(t, x, r, h, material="beschlag", n=14):
	m = Matrix.Translation((x, 0, KZ)) @ Matrix.Rotation(math.radians(90), 4, "Y")
	loft(t, [(m @ Matrix.Translation((0, 0, -h / 2)), kreis(r, n)), (m @ Matrix.Translation((0, 0, 0)), kreis(r * 1.12, n)),
			 (m @ Matrix.Translation((0, 0, h / 2)), kreis(r, n))], material)


def scheibe_x(t, x, r, d, material="beschlag", strahlen=0, n=24):
	"""Scheibe, deren Fläche entlang X zeigt (Schlagfläche)."""
	m = Matrix.Translation((x, 0, KZ)) @ Matrix.Rotation(math.radians(90), 4, "Y")
	def umriss(f):
		pts = []
		for k in range(n):
			a = 2 * math.pi * k / n
			rr = r * (1 + 0.3 * (0.5 + 0.5 * math.cos(a * strahlen)) ** 3) if strahlen else r
			pts.append((math.cos(a) * rr * f, math.sin(a) * rr * f))
		return pts
	loft(t, [(m @ Matrix.Translation((0, 0, -d / 2)), umriss(0.9)), (m, umriss(1.0)), (m @ Matrix.Translation((0, 0, d / 2)), umriss(0.85))], material)


# ================================================================ Speerspitzen


def speerspitze(t, tier, form):
	"""Speerspitze: Tülle plus Klinge im Stil der Schwertklingen des Tiers (verkleinert)."""
	if tier == 4:
		rohling(t, (0, 0, P1 + 0.03), (0.08, 0.04, 0.042), "eis", saat=50 + form, achse="z")
	else:
		drehkoerper(t, [(PR * 1.1, P1 - 0.06), (PR * 1.3, P1 - 0.05), (PR * 1.25, P1 + 0.03), (PR * 0.9, P1 + 0.06)], "beschlag" if tier != 3 else "klinge",
					n=10 if tier != 3 else 4, phase=math.pi / 4 if tier == 3 else 0)
	n0 = anzahl(t)
	schwert.KLINGEN[tier - 1](t, form)
	for v in neue_verts(t, n0):
		d = v.co - Vector((0, 0, schwert.KL))
		v.co = Vector((0, 0, P1 + 0.05)) + Vector((d.x * 1.05, d.y * 1.0, d.z * 0.42))
	if tier == 1 and form == 1:  # Flügel (Knebel) unter der Klinge
		for s in (1, -1):
			stachel(t, (0, 0, P1 - 0.01), (s * 0.045, 0, P1 - 0.005), 0.007)


def je_tier(bauer, n):
	return {tier: (n, (lambda tr: (lambda t, form: bauer(t, tr, form)))(tier)) for tier in range(1, 7)}


ARTEN = {
	"stiel": {tier: (2, stiel_modul(tier)) for tier in range(1, 7)},
	"speerschaft": {tier: (1, speerschaft_modul(tier)) for tier in range(1, 7)},
	"schaftende": {tier: (2, schaftende_modul(tier)) for tier in range(1, 7)},
	"axtkopf": je_tier(axtkopf, 3),
	"hammerkopf": je_tier(hammerkopf, 3),
	"speerspitze": je_tier(speerspitze, 3),
}
