"""Module des Einhandschwerts, je Tier eigener Stil.
Maße: Griff von -0,07 bis 0,075, Parierstange bei 0,09, Klinge ab 0,112, Knauf unter -0,076.

Stile (Philipp, 05.11.2026):
  1 Iron       schlicht, wie echte mittelalterliche Waffen
  2 Palladium  wertvoll, Schnörkel und Verzierungen
  3 Mithril    robust und starr: alles gerade, kantig, keine Krümmungen
  4 Glacialore wie aus Stein geschlagen statt geschmiedet (Eis-Kristall)
  5 Sungold    heiliger Stahl: Flügel, Federn, goldene Akzente, runde, schützende Formen
  6 Darksteel  Dämonenmetall: kantig, zackig, spitz, schwarz und dunkelrot
"""
import math
from mathutils import Vector
from geo import *

KL = 0.112  # Klingenansatz
PZ = 0.09   # Parierstange
G0, G1 = -0.07, 0.075  # Griff
KN = -0.076  # Oberkante Knauf

# Härte der Kanten je Tier (Grad): Mithril/Glacialore/Darksteel kantig, Sungold weich
GLATT = {1: 35, 2: 40, 3: 12, 4: 8, 5: 50, 6: 22}


def spitze(u, anteil):
	"""Breitenfaktor, der im letzten 'anteil' der Klinge rund zur Spitze ausläuft."""
	if u <= 1 - anteil:
		return 1.0
	return math.cos((u - (1 - anteil)) / anteil * math.pi / 2) ** 0.8


def linear_spitz(u, ab):
	"""Gerade zulaufende Spitze ab 'ab'."""
	return 1.0 if u <= ab else max(0.0, (1 - u) / (1 - ab))


def huelse(t, breite=0.05, material="beschlag"):
	quader(t, (0, 0, 0.108), (breite, 0.014, 0.018), material, fase=0.004)


# ================================================================ Klingen


def klinge_t1(t, form):
	if form == 1:  # Langklinge
		klinge(t, KL, 0.78, 0.052, 0.009, hohlkehle=0.45, kehl_laenge=0.72)
	elif form == 2:  # Breitklinge, kurze Spitze
		klinge(t, KL, 0.74, 0.062, 0.010, hohlkehle=0.4, kehl_laenge=0.8,
			   breite_fn=lambda u: (1 - 0.12 * u) * spitze(u, 0.11))
	elif form == 3:  # Falchion: eine gerade Rückenseite, vorn breiter, Spitze zum Rücken hin
		klinge(t, KL, 0.72, 0.05, 0.009, hohlkehle=0.25, kehl_laenge=0.5, schritte=24, spitze_x=-0.025,
			   breite_fn=lambda u: (1.0, (1 + 0.6 * u) * spitze(u, 0.22) * 2 - 1.0))


def klinge_t2(t, form):
	if form == 1:  # Doppelte Hohlkehle, abgesetzte Fehlschärfe
		bf = lambda u: (0.7 if u < 0.05 else (1 - 0.22 * u)) * spitze(u, 0.17)
		klinge(t, KL, 0.8, 0.054, 0.009, hohlkehle=0.5, kehl_laenge=0.65, kehlen=[(0.32, 0.16)], breite_fn=bf, schritte=26)
		for z in (0.125, 0.14):
			quader(t, (0, 0, z), (0.04, 0.012, 0.005), "beschlag", fase=0.002)
	elif form == 2:  # Flamberge: gewellte Schneiden
		bf = lambda u: (1 - 0.25 * u) * (1 + (0.13 * math.sin(u * 2 * math.pi * 6.5) if 0.12 < u < 0.85 else 0)) * spitze(u, 0.15)
		klinge(t, KL, 0.8, 0.05, 0.009, hohlkehle=0.4, kehl_laenge=0.75, breite_fn=bf, schritte=80)


def klinge_t3(t, form):
	if form == 1:  # Keilklinge: parallele Schneiden, gerade abgeschrägte Spitze, Sechskant
		klinge(t, KL, 0.76, 0.056, 0.012, schnitt=lambda w, d: sechskant(w, d, 0.45), schritte=8,
			   breite_fn=lambda u: (1.0, 1.0 if u < 0.84 else 1 - 2 * (u - 0.84) / 0.16), spitze_x=-0.028,
			   dicke_fn=lambda u: 1 - 0.3 * u)
	elif form == 2:  # Dornklinge: Rautenquerschnitt, gerade verjüngt
		klinge(t, KL, 0.82, 0.046, 0.013, schnitt=lambda w, d: [(w, 0), (0, d), (-w, 0), (0, -d)], schritte=4,
			   breite_fn=lambda u: (1 - 0.45 * u) * linear_spitz(u, 0.8), dicke_fn=lambda u: 1 - 0.35 * u)


def klinge_t4(t, form):
	if form == 1:  # Splitterklinge: aus Eiskristall geschlagen
		klinge(t, KL - 0.004, 0.74, 0.06, 0.016, material="eis", hohlkehle=0, n_halb=4, schritte=9, rauh=0.14, saat=4,
			   breite_fn=lambda u: (1 - 0.35 * u) * linear_spitz(u, 0.72), spitze_x=0.004)
	elif form == 2:  # Breiter Keil, schief abgeschlagen
		klinge(t, KL - 0.004, 0.66, 0.078, 0.019, material="eis", hohlkehle=0, n_halb=4, schritte=7, rauh=0.18, saat=11,
			   breite_fn=lambda u: (1.0 - 0.1 * u, (1 - 0.2 * u) * linear_spitz(u, 0.55) * 2 - 1.0 + 0.1 * u), spitze_x=-0.03)


def klinge_t5(t, form):
	if form == 1:  # Breite Blattklinge, runde Spitze, goldene Einlage
		bf = lambda u: (0.95 + 0.15 * math.sin(u * math.pi * 0.8)) * spitze(u, 0.3)
		klinge(t, KL, 0.74, 0.064, 0.010, hohlkehle=0.45, kehl_laenge=0.6, breite_fn=bf, schritte=24)
		rune_streifen(t, 0.14, 0.5, 0.012, 0.0033, material="beschlag")
	elif form == 2:  # Ausgestellter Ansatz wie Schwingen, lange Klinge
		bf = lambda u: (1.35 - 0.35 * min(u / 0.12, 1) ** 0.5 - 0.1 * u) * spitze(u, 0.2)
		klinge(t, KL, 0.8, 0.05, 0.009, hohlkehle=0.4, kehl_laenge=0.7, breite_fn=bf, schritte=26)
		rune_streifen(t, 0.13, 0.6, 0.008, 0.0031, material="beschlag")


def klinge_t6(t, form):
	if form == 1:  # Gezackte Klinge mit Widerhaken
		def bf(u):
			zl = ((u * 9) % 1.0) if 0.08 < u < 0.7 else 0.0
			zr = ((u * 9 + 0.5) % 1.0) if 0.08 < u < 0.7 else 0.0
			b = (1 - 0.3 * u) * linear_spitz(u, 0.8)
			return (b * (1 + 0.3 * zl), b * (1 + 0.3 * zr))
		klinge(t, KL, 0.78, 0.05, 0.011, hohlkehle=0, n_halb=5, breite_fn=bf, schritte=90,
			   schnitt=lambda w, d: [(w, 0), (w * 0.4, d), (-w * 0.4, d), (-w, 0), (-w * 0.4, -d), (w * 0.4, -d)])
		rune_streifen(t, 0.13, 0.66, 0.006, 0.0058, material="leucht")
	elif form == 2:  # Zackenstufen auf einer Seite, Haken vor der Spitze
		def bf(u):
			stufe = 1 + 0.55 * max(0.0, 1 - ((u * 5) % 1.0) / 0.35) if 0.1 < u < 0.75 else 1.0
			haken = 1 + 0.9 * max(0.0, 1 - abs(u - 0.82) / 0.06)
			return ((1 - 0.2 * u) * linear_spitz(u, 0.88) * haken, (1 - 0.3 * u) * stufe * linear_spitz(u, 0.88))
		klinge(t, KL, 0.74, 0.056, 0.011, hohlkehle=0, breite_fn=bf, schritte=110, n_halb=5,
			   schnitt=lambda w, d: [(w, 0), (w * 0.4, d), (-w * 0.4, d), (-w, 0), (-w * 0.4, -d), (w * 0.4, -d)])
		rune_streifen(t, 0.13, 0.62, 0.005, 0.0058, material="leucht")


# ================================================================ Parierstangen


def parier_t1(t, form):
	huelse(t)
	parierstange(t, PZ, 0.21, 0.022, 0.03, form="gerade" if form == 1 else "geschwungen")


def parier_t2(t, form):
	huelse(t)
	if form == 1:  # Voluten: Enden rollen sich zur Klinge hin ein
		for s in (1, -1):
			strang(t, [Vector((0, 0, PZ))] + spirale((s * 0.085, 0, PZ + 0.016), 0.016, 0.004, 1.15, n=22, start=-math.pi / 2, richtung=s),
				   lambda u: 0.02 * (1 - 0.55 * u), lambda u: 0.024 * (1 - 0.5 * u), "beschlag", n=8)
		scheibe(t, (0, 0, PZ), 0.016, 0.03, n=16)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.016, PZ)), 0.008, "stein", achse=Vector((0, s, 0)))
	elif form == 2:  # Kreuz mit Kleeblatt-Enden und Zungen auf der Klinge
		strang(t, [Vector((-0.1, 0, PZ)), Vector((0, 0, PZ - 0.004)), Vector((0.1, 0, PZ))],
			   lambda u: 0.016 + 0.01 * abs(1 - 2 * u), 0.026, "beschlag", n=8)
		for s in (1, -1):
			for a in (-50, 0, 50):
				r = math.radians(a)
				c = Vector((s * (0.11 + 0.012 * math.cos(r)), 0, PZ + 0.012 * math.sin(r)))
				drehkoerper(t, [(0, -0.011), (0.009, -0.006), (0.01, 0), (0.009, 0.006), (0, 0.011)], "beschlag", n=10, versatz=c)
			# Zunge (Langet) auf jeder Klingenseite
			strang(t, [Vector((0, s * 0.0075, 0.1)), Vector((0, s * 0.0075, 0.13)), Vector((0, s * 0.006, 0.16))],
				   lambda u: 0.022 * (1 - u), 0.003, "beschlag", n=6, quer=Vector((0, 1, 0)))
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.014, PZ - 0.002)), 0.007, "stein", achse=Vector((0, s, 0)))


def parier_t3(t, form):
	huelse(t, 0.056)
	if form == 1:  # Gerader Balken
		quader(t, (0, 0, PZ), (0.22, 0.03, 0.026), "beschlag", fase=0.006)
	elif form == 2:  # Balken mit Blöcken an den Enden und in der Mitte
		quader(t, (0, 0, PZ), (0.2, 0.022, 0.018), "beschlag", fase=0.004)
		quader(t, (0, 0, PZ), (0.05, 0.036, 0.032), "beschlag", fase=0.006)
		for s in (1, -1):
			quader(t, (s * 0.105, 0, PZ), (0.03, 0.03, 0.03), "beschlag", fase=0.006)


def parier_t4(t, form):
	if form == 1:  # Kristallsplitter, die aus einem Kern wachsen
		rohling(t, (0, 0, PZ + 0.004), (0.07, 0.034, 0.03), "eis", saat=3)
		for s, a, l, r in [(1, 8, 0.1, 0.011), (-1, 12, 0.09, 0.01), (1, 40, 0.06, 0.008), (-1, 45, 0.055, 0.007), (1, -25, 0.04, 0.007)]:
			w = math.radians(a)
			kristall(t, (s * 0.02, 0, PZ), (s * math.cos(w), 0, math.sin(w)), l, r, "eis", drehung=a * 0.05)
	elif form == 2:  # Roher Block, schief geschlagen
		rohling(t, (0, 0, PZ), (0.2, 0.04, 0.034), "eis", saat=8, rauh=0.3, schritte=6)


def parier_t5(t, form):
	huelse(t)
	if form == 1:  # Flügel aus Federn
		for s in (1, -1):
			for i in range(5):
				w = math.radians(4 + 17 * i)
				l = 0.115 - 0.014 * i
				b = Vector((s * 0.012, 0, PZ - 0.004 + 0.003 * i))
				feder(t, b, b + Vector((s * math.cos(w) * l, 0, math.sin(w) * l)), 0.016, 0.006 - 0.0004 * i,
					  bauch=-0.006 * s, quer=Vector((0, 1, 0)))
		scheibe(t, (0, 0, PZ + 0.002), 0.02, 0.03, n=20)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.016, PZ + 0.002)), 0.009, "stein", achse=Vector((0, s, 0)))
	elif form == 2:  # Halbmond mit Sonnenscheibe: rund und schützend
		pts = [Vector((math.sin(a) * 0.1, 0, PZ + 0.04 - math.cos(a) * 0.05)) for a in [math.radians(-80 + 160 * i / 16) for i in range(17)]]
		strang(t, pts, lambda u: 0.012 + 0.016 * math.sin(math.pi * u), 0.02, "beschlag", n=10)
		for s in (1, -1):
			drehkoerper(t, [(0, -0.012), (0.01, -0.007), (0.012, 0), (0.01, 0.007), (0, 0.012)], "beschlag", n=12,
						versatz=pts[0 if s < 0 else -1])
		scheibe(t, (0, 0, PZ - 0.004), 0.024, 0.026, n=24, strahlen=12, strahl_laenge=0.25)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.014, PZ - 0.004)), 0.01, "stein", achse=Vector((0, s, 0)))


def parier_t6(t, form):
	huelse(t, 0.056, "beschlag")
	if form == 1:  # Stacheln nach vorn
		quader(t, (0, 0, PZ), (0.12, 0.026, 0.02), "beschlag", fase=0.006)
		for s in (1, -1):
			stachel(t, (s * 0.05, 0, PZ), (s * 0.13, 0, PZ + 0.07), 0.013, kruemmung=(s * 0.012, 0, -0.01))
			stachel(t, (s * 0.04, 0, PZ - 0.004), (s * 0.08, 0, PZ - 0.04), 0.008)
		stachel(t, (0, 0, PZ - 0.004), (0, 0, PZ - 0.035), 0.009)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.014, PZ)), 0.007, "stein", achse=Vector((0, s, 0)), n=4)
	elif form == 2:  # Hörner, die nach außen und vorn schwingen
		quader(t, (0, 0, PZ), (0.07, 0.03, 0.026), "beschlag", fase=0.008)
		for s in (1, -1):
			pts = [Vector((s * (0.025 + 0.09 * math.sin(a)), 0, PZ - 0.01 + 0.07 * (1 - math.cos(a)) - 0.02 * math.sin(2 * a)))
				   for a in [math.radians(95 * i / 12) for i in range(13)]]
			strang(t, pts, lambda u: 0.026 * (1 - u) ** 0.8, lambda u: 0.022 * (1 - u) ** 0.8, "beschlag", n=6)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.016, PZ)), 0.008, "stein", achse=Vector((0, s, 0)), n=4)


# ================================================================ Griffe


def griff_t1(t, form):
	if form == 1:
		wicklung(t, G0, G1, 0.0155)
	else:  # Holz mit Rillen
		profil = [(0.0158 if k % 3 else 0.0143, G0 + (G1 - G0) * k / 12) for k in range(13)]
		drehkoerper(t, profil, "holz", n=12)
	ring(t, G0, 0.017, 0.012)
	ring(t, G1, 0.017, 0.012)


def griff_t2(t, form):
	if form == 1:  # Drahtwicklung
		wicklung(t, G0, G1, 0.0148, material="beschlag", windungen=16, tiefe=0.0012, n=10)
	else:  # Leder mit drei Zierringen
		wicklung(t, G0, G1, 0.0155)
		for z in (-0.025, 0.0025, 0.03):
			ring(t, z, 0.0162, 0.006, wulst=0.25)
	ring(t, G0, 0.0175, 0.014, wulst=0.25)
	ring(t, G1, 0.0175, 0.014, wulst=0.25)


def griff_t3(t, form):
	# Achteckig, gerade, mit Metallbändern
	drehkoerper(t, [(0.0158, G0), (0.0158, G1)], "leder", n=8, phase=math.pi / 8)
	for z in (G0, -0.012, 0.035, G1):
		drehkoerper(t, [(0.0172, z - 0.005), (0.0172, z + 0.005)], "beschlag", n=8, phase=math.pi / 8)


def griff_t4(t, form):
	# Fellwicklung mit Lederriemen
	wicklung(t, G0, G1, 0.017, windungen=5, tiefe=0.003, n=9)
	for z in (G0 + 0.006, 0.0, G1 - 0.006):
		ring(t, z, 0.0185, 0.008, material="dunkel", n=9, wulst=0.05)


def griff_t5(t, form):
	# Helles Leder mit goldenen Ringen
	wicklung(t, G0, G1, 0.0155)
	for z in (G0, -0.0, G1):
		ring(t, z, 0.0172, 0.01, wulst=0.3)


def griff_t6(t, form):
	# Schwarz gewickelt, Ringe mit Dornen
	wicklung(t, G0, G1, 0.0152, windungen=9, tiefe=0.002)
	for z in (G0 + 0.004, 0.0, G1 - 0.004):
		drehkoerper(t, [(0.0168, z - 0.005), (0.0175, z), (0.0168, z + 0.005)], "beschlag", n=6)
		for k in range(3):
			a = 2 * math.pi * k / 3 + (0.5 if z == 0 else 0)
			r = Vector((math.cos(a), math.sin(a), 0))
			stachel(t, Vector((0, 0, z)) + r * 0.016, Vector((0, 0, z - 0.008)) + r * 0.028, 0.0035)


# ================================================================ Knäufe


def knauf_t1(t, form):
	knauf(t, KN, 0.026, form="scheibe" if form == 1 else "tropfen")


def knauf_t2(t, form):
	if form == 1:  # Facettierter Flaschenknauf
		drehkoerper(t, [(0, KN - 0.07), (0.009, KN - 0.068), (0.016, KN - 0.058), (0.02, KN - 0.045), (0.024, KN - 0.03),
						(0.017, KN - 0.018), (0.012, KN - 0.012), (0.016, KN - 0.006), (0.011, KN)], "beschlag", n=8, phase=math.pi / 8)
	else:  # Ring mit Stein
		drehkoerper(t, [(0.008, KN - 0.008), (0.012, KN - 0.004), (0.011, KN)], "beschlag", n=10)
		pts = [Vector((math.sin(a) * 0.026, 0, KN - 0.034 + math.cos(a) * 0.026)) for a in [2 * math.pi * i / 24 for i in range(25)]]
		strang(t, pts, 0.008, 0.016, "beschlag", n=8, kappen=False)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.002, KN - 0.034)), 0.017, "stein", achse=Vector((0, s, 0)))


def knauf_t3(t, form):
	if form == 1:  # Block
		quader(t, (0, 0, KN - 0.018), (0.04, 0.03, 0.036), "beschlag", fase=0.007)
	else:  # Achteckiges Prisma mit gerader Spitze
		drehkoerper(t, [(0, KN - 0.05), (0.014, KN - 0.042), (0.022, KN - 0.03), (0.022, KN - 0.01), (0.014, KN)],
					"beschlag", n=8, phase=math.pi / 8)


def knauf_t4(t, form):
	if form == 1:  # Kristallbrocken
		rohling(t, (0, 0, KN - 0.016), (0.036, 0.034, 0.03), "eis", saat=21, rauh=0.25)
		for a in (-30, 0, 35):
			w = math.radians(a - 90)
			kristall(t, (0, 0, KN - 0.02), (math.cos(w), 0.15 * (a / 30), math.sin(w)), 0.05 - abs(a) * 0.0004, 0.008, "eis")
	else:  # Ein großer Splitter
		kristall(t, (0, 0, KN + 0.004), (0.05, 0, -1), 0.08, 0.013, "eis", spitze_anteil=0.45)


def knauf_t5(t, form):
	if form == 1:  # Sonnenscheibe
		drehkoerper(t, [(0.008, KN - 0.01), (0.012, KN - 0.004), (0.011, KN)], "beschlag", n=10)
		scheibe(t, (0, 0, KN - 0.034), 0.024, 0.02, strahlen=12, strahl_laenge=0.35)
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.01, KN - 0.034)), 0.011, "stein", achse=Vector((0, s, 0)))
	else:  # Kugel mit kleinen Flügeln
		knauf(t, KN, 0.022, form="kugel")
		for s in (1, -1):
			for i in range(3):
				w = math.radians(-20 - 25 * i)
				b = Vector((s * 0.014, 0, KN - 0.018))
				feder(t, b, b + Vector((s * math.cos(w), 0, math.sin(w))) * (0.05 - 0.008 * i), 0.011, 0.004, bauch=0.004 * s)


def knauf_t6(t, form):
	if form == 1:  # Langer Dorn
		drehkoerper(t, [(0.012, KN - 0.012), (0.018, KN - 0.006), (0.012, KN)], "beschlag", n=6)
		stachel(t, (0, 0, KN - 0.01), (0, 0, KN - 0.08), 0.014)
	else:  # Klauen um einen roten Stein
		edelstein(t, Vector((0, 0, KN - 0.03)), 0.016, "stein", achse="z", n=6)
		for k in range(3):
			a = 2 * math.pi * k / 3
			r = Vector((math.cos(a), math.sin(a), 0))
			stachel(t, Vector((0, 0, KN)) + r * 0.008, Vector((0, 0, KN - 0.055)) + r * 0.004, 0.006,
					kruemmung=r * 0.026)


# Teil -> Tier -> (Anzahl Formen, Baufunktion)
MODULE = {
	"klinge": {1: (3, klinge_t1), 2: (2, klinge_t2), 3: (2, klinge_t3), 4: (2, klinge_t4), 5: (2, klinge_t5), 6: (2, klinge_t6)},
	"parier": {1: (2, parier_t1), 2: (2, parier_t2), 3: (2, parier_t3), 4: (2, parier_t4), 5: (2, parier_t5), 6: (2, parier_t6)},
	"griff": {1: (2, griff_t1), 2: (2, griff_t2), 3: (1, griff_t3), 4: (1, griff_t4), 5: (1, griff_t5), 6: (1, griff_t6)},
	"knauf": {1: (2, knauf_t1), 2: (2, knauf_t2), 3: (2, knauf_t3), 4: (2, knauf_t4), 5: (2, knauf_t5), 6: (2, knauf_t6)},
}
