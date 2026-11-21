"""Tiermodelle (Wolf, Wildschwein, Bär, Berglöwe, Krokodil, ...) mit Varianten.

python3 tiere.py -- <ausgabe> [art,art,...]       Bild <ausgabe>/<art>.png, mit GLB=1 je Variante ein GLB.
Varianten derselben Art teilen das Netz (gleiche Form) und unterscheiden sich in Größe, Fellfarbe und Fellhöhe.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import tierform as tf  # noqa: E402


def weich(x, a, b):
	t = min(1.0, max(0.0, (x - a) / (b - a)))
	return t * t * (3 - 2 * t)


def mischen(a, b, t):
	return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def nahe(p, c, r):
	d = (p - Vector(c)).length
	return math.exp(-(d / r) ** 2)


# ================================================================ Wolf


def wolf_form(F, mager=0.0):
	"""Wolf, Blick nach -Y, Widerrist ~0,8 m. mager > 0: schmaler (Moorwolf)."""
	b = 1.0 - 0.18 * mager
	# Rumpf: tiefer, schmaler Brustkorb vorne, schlanke Taille, Kruppe
	F.ellipsoid((0, -0.18, 0.62), (0.14 * b, 0.26, 0.185), k=0.05, kipp=0.2)
	F.ellipsoid((0, 0.12, 0.70), (0.1 * b, 0.22, 0.085), k=0.07)
	F.ellipsoid((0, 0.36, 0.68), (0.115 * b, 0.14, 0.12), k=0.05)
	F.kette([(0, -0.36, 0.80), (0, -0.1, 0.80), (0, 0.25, 0.76), (0, 0.45, 0.72)], [0.08, 0.075, 0.075, 0.065], k=0.05)
	F.ellipsoid((0, -0.38, 0.62), (0.09 * b, 0.07, 0.12), k=0.05)          # Brust vorne (Vorbrust)
	# Hals und Kopf (langer Fang)
	F.kapsel((0, -0.34, 0.74), (0, -0.53, 0.89), 0.115 * b, 0.08, k=0.05)
	F.ellipsoid((0, -0.585, 0.925), (0.08, 0.095, 0.08), k=0.03)           # Schädel
	F.ellipsoid((0, -0.565, 0.89), (0.09, 0.055, 0.065), k=0.03)           # Wangen
	F.kapsel((0, -0.64, 0.92), (0, -0.85, 0.875), 0.05, 0.03, k=0.035)     # Fang oben
	F.kapsel((0, -0.62, 0.875), (0, -0.82, 0.852), 0.04, 0.02, k=0.025)    # Unterkiefer
	# Ohren (spitz, aufrecht, leicht nach außen)
	F.spiegeln(F.kapsel, [0.052, -0.57, 0.98], [0.066, -0.575, 1.075], 0.032, 0.003, k=0.015)
	# Vorderbeine: Schulterblatt, Ellbogen, Handwurzel, Pfote (Unterarm schlank)
	F.spiegeln(F.kette, [[0.08, -0.20, 0.70], [0.10, -0.32, 0.45], [0.09, -0.29, 0.30], [0.08, -0.27, 0.12],
		[0.078, -0.30, 0.04]], [0.07 * b, 0.045, 0.028, 0.02, 0.024], k=0.03)
	F.spiegeln(F.ellipsoid, [0.078, -0.32, 0.024], [0.03, 0.045, 0.024], k=0.015)
	# Hinterbeine: kräftiger Oberschenkel, Knie, Sprunggelenk (Fersenhöcker), Mittelfuß, Pfote
	F.spiegeln(F.ellipsoid, [0.085, 0.36, 0.58], [0.075 * b, 0.12, 0.15], k=0.04, kipp=-0.35)
	F.spiegeln(F.kette, [[0.09, 0.36, 0.62], [0.10, 0.28, 0.42], [0.085, 0.43, 0.20], [0.078, 0.40, 0.04]],
		[0.07 * b, 0.04, 0.022, 0.022], k=0.03)
	F.spiegeln(F.ellipsoid, [0.078, 0.375, 0.024], [0.029, 0.044, 0.024], k=0.015)
	# Rute: buschig, hängend
	F.kette([(0, 0.46, 0.71), (0, 0.57, 0.6), (0, 0.62, 0.45), (0, 0.63, 0.32)], [0.035, 0.05, 0.055, 0.025], k=0.04)


def wolf_fell(p, hoehe=1.0):
	s = 0.0035
	s += 0.007 * nahe(p, (0, -0.42, 0.78), 0.15)       # Halskrause
	s += 0.005 * nahe(p, (0, -0.55, 0.86), 0.07)       # Backenbart
	s += 0.007 * nahe(p, (0, 0.6, 0.45), 0.16)         # Rute
	s += 0.003 * weich(p.z, 0.6, 0.8)                  # Rücken
	s *= 1.0 - 0.8 * weich(-p.z, -0.30, -0.12)         # Beine kurz
	s *= 1.0 - 0.9 * nahe(p, (0, -0.74, 0.88), 0.07)   # Schnauze kurz
	s *= max(0.0, 1.0 - 0.9 * nahe(p, (0.058, -0.57, 1.03), 0.05) - 0.9 * nahe(p, (-0.058, -0.57, 1.03), 0.05))
	return s * hoehe


def wolf_farbe(V):
	"""V: Farben ruecken, seite, bauch, beine, gesicht, spitzen."""
	def f(p, n):
		c = V["seite"]
		# Sattel: dunkler Rücken
		c = mischen(c, V["ruecken"], weich(p.z, 0.66, 0.82) * (1 - weich(-p.y, 0.45, 0.6)))
		# heller Bauch, Kehle und Innenseiten
		unten = weich(-n.z, 0.2, 0.8) * weich(p.z, 0.25, 0.4)
		c = mischen(c, V["bauch"], unten)
		c = mischen(c, V["bauch"], nahe(p, (0, -0.55, 0.80), 0.08))                     # Kehle
		c = mischen(c, V["beine"], weich(-p.z, -0.45, -0.25))
		c = mischen(c, V["gesicht"], nahe(p, (0, -0.76, 0.86), 0.07) * 0.9)           # Schnauze hell
		c = mischen(c, V["gesicht"], nahe(p, (0.04, -0.66, 0.93), 0.03) + nahe(p, (-0.04, -0.66, 0.93), 0.03))
		c = mischen(c, V["spitzen"], weich(p.z, 1.03, 1.07))                             # Ohrspitzen
		c = mischen(c, V["spitzen"], weich(-p.z, -0.36, -0.30) * weich(p.y, 0.55, 0.62))  # Rutenspitze
		c = mischen(c, V["ruecken"], nahe(p, (0, 0.5, 0.70), 0.05) * 0.8)                 # Violdrüse
		return c
	return f


def wolf_augen(obs, mat_auge, mat_nase):
	for x in (0.038, -0.038):
		obs.append(tf.kugel("auge", (x, -0.665, 0.94), 0.012, mat_auge))
	obs.append(tf.kugel("nase", (0, -0.865, 0.885), 0.021, mat_nase))


WOLF_KNOCHEN = [
	("Hips", (0, 0.32, 0.72), (0, 0.10, 0.74), None),
	("Spine", (0, 0.10, 0.74), (0, -0.15, 0.76), "Hips"),
	("Chest", (0, -0.15, 0.76), (0, -0.33, 0.76), "Spine"),
	("Neck", (0, -0.33, 0.76), (0, -0.52, 0.88), "Chest"),
	("Head", (0, -0.52, 0.88), (0, -0.82, 0.88), "Neck"),
	("Jaw", (0, -0.60, 0.86), (0, -0.77, 0.85), "Head"),
	("Tail1", (0, 0.46, 0.71), (0, 0.58, 0.58), "Hips"),
	("Tail2", (0, 0.58, 0.58), (0, 0.64, 0.30), "Tail1"),
]
for s, n in ((1, "Left"), (-1, "Right")):
	WOLF_KNOCHEN += [
		(n + "Shoulder", (0.085 * s, -0.22, 0.66), (0.10 * s, -0.30, 0.44), "Chest"),
		(n + "FrontLeg", (0.10 * s, -0.30, 0.44), (0.085 * s, -0.27, 0.15), n + "Shoulder"),
		(n + "FrontPaw", (0.085 * s, -0.27, 0.15), (0.08 * s, -0.33, 0.03), n + "FrontLeg"),
		(n + "Thigh", (0.085 * s, 0.38, 0.68), (0.105 * s, 0.28, 0.44), "Hips"),
		(n + "Shin", (0.105 * s, 0.28, 0.44), (0.085 * s, 0.44, 0.19), n + "Thigh"),
		(n + "HindFoot", (0.085 * s, 0.44, 0.19), (0.08 * s, 0.38, 0.03), n + "Shin"),
	]


# ================================================================ Allgemeine Hilfen für Vierbeiner


def vierbeiner_knochen(h, s, v_bein, h_bein, nacken, kopf, schwanz):
	"""Skelett: Hüfte h, Schulter s (je (y, z)), Beinpunkte als Listen [(x, y, z)...] (links), Nacken/Kopf/Schwanz-Ketten."""
	K = [("Hips", (0, h[0], h[1]), (0, (h[0] + s[0]) / 2, (h[1] + s[1]) / 2), None),
		("Spine", (0, (h[0] + s[0]) / 2, (h[1] + s[1]) / 2), (0, s[0], s[1]), "Hips"),
		("Neck", (0, s[0], s[1]), nacken, "Spine"), ("Head", nacken, kopf, "Neck")]
	for i in range(len(schwanz) - 1):
		K.append(("Tail%d" % (i + 1), schwanz[i], schwanz[i + 1], "Hips" if i == 0 else "Tail%d" % i))
	for sg, n in ((1, "Left"), (-1, "Right")):
		for bein, eltern, namen in ((v_bein, "Spine", ("Shoulder", "FrontLeg", "FrontPaw")),
				(h_bein, "Hips", ("Thigh", "Shin", "HindFoot"))):
			pts = [(p[0] * sg, p[1], p[2]) for p in bein]
			for j in range(3):
				K.append((n + namen[j], pts[j], pts[j + 1], eltern if j == 0 else n + namen[j - 1]))
	return K


def standard_farbe(ruecken_z, kopf, schnauze, bauch_z=(0.25, 0.4), bein_z=(0.25, 0.45)):
	"""Fellfarben: Rücken dunkler, Bauch hell, Beine, Gesicht. V hat ruecken, seite, bauch, beine, gesicht, spitzen."""
	def mach(V):
		def f(p, n):
			c = V["seite"]
			c = mischen(c, V["ruecken"], weich(p.z, *ruecken_z))
			c = mischen(c, V["bauch"], weich(-n.z, 0.2, 0.8) * weich(p.z, *bauch_z))
			c = mischen(c, V["beine"], 1 - weich(p.z, *bein_z))
			c = mischen(c, V["gesicht"], nahe(p, schnauze, 0.07))
			c = mischen(c, V.get("kopf", c), nahe(p, kopf, 0.12) * (1 if "kopf" in V else 0))
			return c
		return f
	return mach


# ================================================================ Wildschwein


def schwein_form(F, bache=0.0):
	"""Keiler: Widerrist ~0,85 m, keilförmiger Kopf, Borstenkamm. bache > 0: kleiner Kopf, ohne Hauer."""
	F.ellipsoid((0, -0.15, 0.58), (0.2, 0.42, 0.25), k=0.06, kipp=0.12)          # massiger Vorderleib
	F.ellipsoid((0, 0.28, 0.56), (0.17, 0.3, 0.2), k=0.07)
	F.kette([(0, -0.45, 0.78), (0, -0.1, 0.8), (0, 0.35, 0.7), (0, 0.55, 0.6)], [0.11, 0.12, 0.1, 0.08], k=0.07)
	# Kopf: keilförmig, tief angesetzt
	F.kapsel((0, -0.48, 0.68), (0, -0.66, 0.58), 0.18, 0.12, k=0.07)
	F.kapsel((0, -0.66, 0.58), (0, -0.86, 0.44), 0.11, 0.06, k=0.05)
	F.ellipsoid((0, -0.88, 0.43), (0.06, 0.025, 0.055), k=0.02, kipp=0.5)         # Rüsselscheibe
	F.spiegeln(F.kapsel, [0.08, -0.55, 0.78], [0.11, -0.5, 0.88], 0.035, 0.008, k=0.02)   # Ohren
	if bache <= 0:
		F.spiegeln(F.kapsel, [0.06, -0.8, 0.44], [0.09, -0.84, 0.53], 0.013, 0.004, k=0.005)   # Hauer
	# Beine kurz, kräftig oben, schlanke Läufe mit Klauen
	F.spiegeln(F.kette, [[0.12, -0.28, 0.55], [0.12, -0.3, 0.32], [0.1, -0.28, 0.12], [0.1, -0.31, 0.03]],
		[0.09, 0.05, 0.03, 0.03], k=0.04)
	F.spiegeln(F.kette, [[0.11, 0.38, 0.5], [0.12, 0.3, 0.3], [0.1, 0.42, 0.14], [0.1, 0.38, 0.03]],
		[0.1, 0.05, 0.03, 0.03], k=0.04)
	F.kette([(0, 0.6, 0.6), (0, 0.66, 0.48), (0, 0.67, 0.38)], [0.025, 0.015, 0.01], k=0.02)   # Pürzel
	# Borstenkamm (Federn) auf dem Rücken
	for i in range(9):
		y = -0.55 + 0.11 * i
		F.kapsel((0, y, 0.82 - 0.03 * max(0, i - 5)), (0, y + 0.02, 0.9 - 0.04 * max(0, i - 4)), 0.02, 0.008, k=0.04)


def schwein_fell(p, hoehe=1.0):
	s = 0.008 + 0.012 * weich(p.z, 0.7, 0.9) * (1 - weich(p.y, 0.2, 0.5))
	s *= 1.0 - 0.9 * nahe(p, (0, -0.88, 0.43), 0.1)
	s *= 1.0 - 0.7 * weich(-p.z, -0.25, -0.1)
	return s * hoehe


def schwein_augen(obs, mat_auge, mat_nase):
	for x in (0.075, -0.075):
		obs.append(tf.kugel("auge", (x, -0.66, 0.66), 0.011, mat_auge))
	for x in (0.018, -0.018):
		obs.append(tf.kugel("nase", (x, -0.905, 0.43), 0.012, mat_nase))


SCHWEIN_KNOCHEN = vierbeiner_knochen((0.35, 0.68), (-0.3, 0.74), [(0.12, -0.28, 0.55), (0.12, -0.3, 0.32), (0.1, -0.28, 0.12), (0.1, -0.31, 0.03)],
	[(0.11, 0.38, 0.5), (0.12, 0.3, 0.3), (0.1, 0.42, 0.14), (0.1, 0.38, 0.03)], (0, -0.55, 0.66), (0, -0.9, 0.43),
	[(0, 0.6, 0.6), (0, 0.67, 0.38)])


# ================================================================ Bär


def baer_form(F, gross=0.0):
	"""Braunbär: Widerrist ~1,0 m mit Schulterbuckel, Sohlengänger, runder Kopf mit kurzen Ohren."""
	F.ellipsoid((0, -0.25, 0.75), (0.3, 0.5, 0.33), k=0.08, kipp=0.08)
	F.ellipsoid((0, 0.35, 0.72), (0.28, 0.42, 0.3), k=0.1)
	F.ellipsoid((0, -0.35, 1.0), (0.18, 0.25, 0.13), k=0.1)                     # Schulterbuckel
	F.kapsel((0, -0.55, 0.88), (0, -0.82, 0.86), 0.2, 0.15, k=0.08)           # Nacken
	F.ellipsoid((0, -0.9, 0.86), (0.15, 0.15, 0.14), k=0.05)                    # Schädel breit
	F.kapsel((0, -0.98, 0.83), (0, -1.15, 0.78), 0.085, 0.055, k=0.05)        # Schnauze
	F.spiegeln(F.ellipsoid, [0.1, -0.86, 0.99], [0.04, 0.02, 0.035], k=0.02)   # runde Ohren
	# Beine: dicke Säulen, breite Tatzen
	F.spiegeln(F.kette, [[0.18, -0.4, 0.75], [0.2, -0.45, 0.42], [0.18, -0.42, 0.12], [0.18, -0.48, 0.05]],
		[0.14, 0.1, 0.08, 0.07], k=0.06)
	F.spiegeln(F.ellipsoid, [0.18, -0.5, 0.04], [0.08, 0.11, 0.045], k=0.03)
	F.spiegeln(F.kette, [[0.18, 0.5, 0.75], [0.2, 0.42, 0.42], [0.18, 0.52, 0.15], [0.18, 0.48, 0.05]],
		[0.16, 0.1, 0.075, 0.07], k=0.06)
	F.spiegeln(F.ellipsoid, [0.18, 0.44, 0.04], [0.075, 0.13, 0.045], k=0.03)
	F.kapsel((0, 0.75, 0.75), (0, 0.82, 0.68), 0.05, 0.035, k=0.04)


def baer_fell(p, hoehe=1.0):
	s = 0.016 + 0.014 * nahe(p, (0, -0.4, 1.05), 0.25) + 0.008 * nahe(p, (0, -0.85, 0.78), 0.12)
	s *= 1.0 - 0.85 * nahe(p, (0, -1.15, 0.78), 0.08)
	s *= 1.0 - 0.5 * weich(-p.z, -0.15, -0.05)
	return s * hoehe


def baer_augen(obs, mat_auge, mat_nase):
	for x in (0.06, -0.06):
		obs.append(tf.kugel("auge", (x, -1.02, 0.9), 0.014, mat_auge))
	obs.append(tf.kugel("nase", (0, -1.2, 0.79), 0.035, mat_nase))


BAER_KNOCHEN = vierbeiner_knochen((0.4, 0.8), (-0.35, 0.9), [(0.18, -0.4, 0.75), (0.2, -0.45, 0.42), (0.18, -0.42, 0.12), (0.18, -0.5, 0.04)],
	[(0.18, 0.5, 0.75), (0.2, 0.42, 0.42), (0.18, 0.52, 0.15), (0.18, 0.44, 0.04)], (0, -0.8, 0.87), (0, -1.18, 0.78),
	[(0, 0.72, 0.76), (0, 0.84, 0.66)])


# ================================================================ Berglöwe (Puma)


def loewe_form(F, x=0.0):
	"""Puma: lang und niedrig (Widerrist ~0,7 m), kleiner runder Kopf, langer dicker Schwanz."""
	F.ellipsoid((0, -0.2, 0.55), (0.14, 0.3, 0.17), k=0.06, kipp=0.06)
	F.ellipsoid((0, 0.25, 0.55), (0.13, 0.32, 0.14), k=0.08)
	F.kette([(0, -0.42, 0.68), (0, -0.05, 0.66), (0, 0.4, 0.66), (0, 0.58, 0.63)], [0.08, 0.08, 0.08, 0.07], k=0.06)
	F.kapsel((0, -0.42, 0.62), (0, -0.62, 0.74), 0.1, 0.075, k=0.05)
	F.ellipsoid((0, -0.69, 0.765), (0.085, 0.085, 0.078), k=0.03)
	F.kapsel((0, -0.73, 0.735), (0, -0.82, 0.715), 0.045, 0.035, k=0.03)        # kurze Schnauze
	F.ellipsoid((0, -0.76, 0.7), (0.05, 0.04, 0.03), k=0.02)                    # Kinn
	F.spiegeln(F.kapsel, [0.05, -0.665, 0.81], [0.058, -0.665, 0.865], 0.026, 0.008, k=0.012)  # Ohren
	F.spiegeln(F.kette, [[0.09, -0.28, 0.58], [0.1, -0.36, 0.36], [0.085, -0.32, 0.12], [0.08, -0.36, 0.035]],
		[0.07, 0.05, 0.035, 0.035], k=0.035)
	F.spiegeln(F.ellipsoid, [0.08, -0.38, 0.03], [0.04, 0.05, 0.03], k=0.02)
	F.spiegeln(F.ellipsoid, [0.09, 0.42, 0.48], [0.08, 0.15, 0.17], k=0.04, kipp=-0.3)
	F.spiegeln(F.kette, [[0.09, 0.42, 0.52], [0.1, 0.32, 0.32], [0.085, 0.5, 0.16], [0.08, 0.46, 0.035]],
		[0.07, 0.045, 0.03, 0.033], k=0.035)
	F.spiegeln(F.ellipsoid, [0.08, 0.44, 0.03], [0.038, 0.05, 0.03], k=0.02)
	F.kette([(0, 0.6, 0.63), (0, 0.82, 0.45), (0, 0.98, 0.22), (0, 1.15, 0.12), (0, 1.27, 0.18)],
		[0.045, 0.04, 0.035, 0.035, 0.035], k=0.03)


def loewe_fell(p, hoehe=1.0):
	s = 0.004
	return s * hoehe


def loewe_farbe(V):
	def f(p, n):
		c = V["seite"]
		c = mischen(c, V["ruecken"], weich(p.z, 0.6, 0.72))
		c = mischen(c, V["bauch"], weich(-n.z, 0.1, 0.7) * weich(p.z, 0.2, 0.35))
		c = mischen(c, V["bauch"], nahe(p, (0, -0.76, 0.7), 0.05) + nahe(p, (0, -0.6, 0.62), 0.06))   # Kinn, Kehle
		c = mischen(c, V["gesicht"], nahe(p, (0.03, -0.81, 0.74), 0.02) + nahe(p, (-0.03, -0.81, 0.74), 0.02))  # Schnurrbart-Fleck
		c = mischen(c, V["spitzen"], weich(p.y, 1.17, 1.24))                                        # Schwanzspitze
		c = mischen(c, V["spitzen"], nahe(p, (0.05, -0.66, 0.85), 0.02) + nahe(p, (-0.05, -0.66, 0.85), 0.02))   # Ohrrückseite
		if V.get("flecken"):
			from mathutils import noise
			f_ = noise.voronoi(p * 9.0)[0][0]
			c = mischen(c, V["spitzen"], 0.7 * (1 - weich(f_, 0.08, 0.16)) * weich(p.z, 0.3, 0.5))
		return c
	return f


def loewe_augen(obs, mat_auge, mat_nase):
	for x in (0.032, -0.032):
		obs.append(tf.kugel("auge", (x, -0.75, 0.78), 0.012, mat_auge))
	obs.append(tf.kugel("nase", (0, -0.835, 0.73), 0.016, mat_nase))


LOEWE_KNOCHEN = vierbeiner_knochen((0.4, 0.62), (-0.3, 0.66), [(0.09, -0.28, 0.58), (0.1, -0.36, 0.36), (0.085, -0.32, 0.12), (0.08, -0.38, 0.03)],
	[(0.09, 0.42, 0.52), (0.1, 0.32, 0.32), (0.085, 0.5, 0.16), (0.08, 0.44, 0.03)], (0, -0.62, 0.74), (0, -0.84, 0.72),
	[(0, 0.6, 0.63), (0, 0.82, 0.45), (0, 0.98, 0.22), (0, 1.15, 0.12), (0, 1.27, 0.18)])


# ================================================================ Krokodil


def kroko_form(F, x=0.0):
	"""Krokodil: ~3,4 m lang, flach, lange Schnauze, Rückenschilde, seitlich abgespreizte Beine."""
	F.ellipsoid((0, 0.0, 0.25), (0.32, 0.7, 0.16), k=0.08)
	F.kapsel((0, -0.55, 0.26), (0, -0.85, 0.27), 0.22, 0.17, k=0.08)          # Hals
	F.ellipsoid((0, -1.0, 0.27), (0.17, 0.2, 0.1), k=0.05)                     # Kopf
	F.ellipsoid((0, -1.38, 0.22), (0.1, 0.36, 0.055), k=0.06)                   # Schnauze oben
	F.ellipsoid((0, -1.32, 0.17), (0.09, 0.38, 0.04), k=0.04)                   # Unterkiefer
	F.spiegeln(F.ellipsoid, [0.07, -0.98, 0.36], [0.035, 0.05, 0.03], k=0.02)  # Augenhöcker
	F.ellipsoid((0, -1.7, 0.24), (0.05, 0.04, 0.03), k=0.03)                    # Nasenhöcker
	# Schwanz: lang, seitlich abgeflacht, oben Kamm
	pts = [(0, 0.6, 0.26), (0, 1.0, 0.22), (0, 1.4, 0.18), (0, 1.75, 0.14), (0, 2.05, 0.1)]
	F.kette(pts, [0.2, 0.15, 0.1, 0.06, 0.02], k=0.06)
	# Beine seitlich (Ellbogen nach außen)
	F.spiegeln(F.kette, [[0.25, -0.45, 0.22], [0.42, -0.5, 0.18], [0.45, -0.55, 0.04]], [0.08, 0.06, 0.05], k=0.04)
	F.spiegeln(F.ellipsoid, [0.46, -0.6, 0.025], [0.06, 0.08, 0.02], k=0.02)
	F.spiegeln(F.kette, [[0.25, 0.45, 0.22], [0.45, 0.42, 0.2], [0.48, 0.36, 0.04]], [0.1, 0.07, 0.05], k=0.04)
	F.spiegeln(F.ellipsoid, [0.49, 0.3, 0.025], [0.07, 0.1, 0.02], k=0.02)
	# Rückenschilde: zwei Reihen Höcker
	for i in range(16):
		y = -0.7 + 0.12 * i
		z = 0.38 - 0.012 * max(0, i - 8) - (0.02 if i < 2 else 0)
		for x in (0.08, -0.08):
			F.ellipsoid((x, y, z), (0.025, 0.04, 0.03), k=0.03)
	for i in range(12):
		y = 1.0 + 0.09 * i
		F.ellipsoid((0, y, 0.3 - 0.016 * i), (0.012, 0.04, 0.04 - 0.002 * i), k=0.02)


def kroko_fell(p, hoehe=1.0):
	return 0.0


def kroko_schuppen(ob):
	"""Hornplatten: Zellmuster eingedrückt (Fugen), oben gröber als am Bauch."""
	from mathutils import noise
	me = ob.data
	n = len(me.vertices)
	P, N = np.empty(n * 3), np.empty(n * 3)
	me.vertices.foreach_get("co", P)
	me.vertices.foreach_get("normal", N)
	P, N = P.reshape(-1, 3), N.reshape(-1, 3)
	for i in range(n):
		p = Vector(P[i])
		skala = 22.0 if N[i][2] > -0.3 else 40.0
		d = noise.voronoi(p * skala)[0]
		fuge = 1.0 - weich(d[1] - d[0], 0.0, 0.15)
		P[i] -= N[i] * 0.006 * fuge
	me.vertices.foreach_set("co", P.ravel())
	me.update()


def kroko_farbe(V):
	def f(p, n):
		c = mischen(V["seite"], V["ruecken"], weich(n.z, 0.3, 0.9))
		c = mischen(c, V["bauch"], weich(-n.z, 0.2, 0.7))
		from mathutils import noise
		c = mischen(c, V["spitzen"], 0.5 * weich(noise.noise(p * 3.0), 0.2, 0.6) * weich(n.z, 0.0, 0.5))
		return c
	return f


def kroko_augen(obs, mat_auge, mat_nase):
	for x in (0.075, -0.075):
		obs.append(tf.kugel("auge", (x, -1.0, 0.385), 0.018, mat_auge))
	# Zähne entlang des Kiefers
	for sg in (1, -1):
		for i in range(14):
			y = -1.66 + 0.05 * i
			obs.append(tf.kugel("zahn", (sg * (0.065 + 0.0012 * i * 3), y, 0.185), 0.01, mat_nase, seg=6))


KROKO_KNOCHEN = vierbeiner_knochen((0.5, 0.26), (-0.45, 0.26), [(0.25, -0.45, 0.22), (0.42, -0.5, 0.18), (0.45, -0.55, 0.04), (0.46, -0.66, 0.02)],
	[(0.25, 0.45, 0.22), (0.45, 0.42, 0.2), (0.48, 0.36, 0.04), (0.49, 0.24, 0.02)], (0, -0.95, 0.27), (0, -1.72, 0.22),
	[(0, 0.6, 0.26), (0, 1.0, 0.22), (0, 1.4, 0.18), (0, 1.75, 0.14), (0, 2.05, 0.1)])
KROKO_KNOCHEN.append(("Jaw", (0, -1.0, 0.2), (0, -1.68, 0.17), "Head"))


# ================================================================ Hirsch


def hirsch_form(F, geweih=True):
	"""Rothirsch: Widerrist ~1,2 m, lange schlanke Läufe, aufrechter Hals, Geweih (nur Hirsch)."""
	F.ellipsoid((0, -0.15, 0.98), (0.17, 0.38, 0.22), k=0.07, kipp=0.05)
	F.ellipsoid((0, 0.3, 1.0), (0.16, 0.3, 0.2), k=0.08)
	F.kapsel((0, -0.42, 1.08), (0, -0.62, 1.45), 0.12, 0.075, k=0.06)           # Hals
	F.ellipsoid((0, -0.68, 1.52), (0.07, 0.1, 0.075), k=0.03)                    # Schädel
	F.kapsel((0, -0.72, 1.5), (0, -0.92, 1.42), 0.055, 0.032, k=0.03)            # Äser
	F.spiegeln(F.kapsel, [0.05, -0.64, 1.58], [0.13, -0.6, 1.66], 0.035, 0.008, k=0.015)   # Lauscher
	for sg in (1, -1):
		bein = lambda pts, r: F.kette([(x * sg, y, z) for x, y, z in pts], r, k=0.03)
		bein([(0.1, -0.3, 0.95), (0.11, -0.36, 0.62), (0.09, -0.33, 0.35), (0.085, -0.34, 0.06), (0.085, -0.37, 0.02)],
			[0.08, 0.045, 0.026, 0.022, 0.024])
		bein([(0.1, 0.42, 0.98), (0.12, 0.3, 0.66), (0.09, 0.48, 0.42), (0.085, 0.44, 0.06), (0.085, 0.41, 0.02)],
			[0.1, 0.05, 0.026, 0.022, 0.024])
		if geweih:
			# Stangen mit Augspross, Mittelspross und Krone
			b = (0.05 * sg, -0.64, 1.6)
			F.kette([b, (0.14 * sg, -0.6, 1.78), (0.24 * sg, -0.55, 1.98), (0.28 * sg, -0.5, 2.15)], [0.022, 0.018, 0.014, 0.01], k=0.01)
			F.kapsel((0.09 * sg, -0.62, 1.67), (0.12 * sg, -0.8, 1.72), 0.014, 0.004, k=0.008)
			F.kapsel((0.2 * sg, -0.57, 1.9), (0.25 * sg, -0.75, 1.96), 0.012, 0.004, k=0.008)
			F.kapsel((0.27 * sg, -0.52, 2.08), (0.36 * sg, -0.55, 2.2), 0.01, 0.003, k=0.006)
			F.kapsel((0.27 * sg, -0.52, 2.08), (0.24 * sg, -0.4, 2.22), 0.01, 0.003, k=0.006)
	F.kapsel((0, 0.56, 1.05), (0, 0.62, 0.95), 0.04, 0.02, k=0.03)               # Wedel


def hirsch_fell(p, hoehe=1.0):
	return (0.003 + 0.01 * nahe(p, (0, -0.5, 1.15), 0.12)) * hoehe * (1 if p.z < 1.6 else 0)


def hirsch_farbe(V):
	def f(p, n):
		c = mischen(V["seite"], V["ruecken"], weich(p.z, 1.1, 1.25) * weich(-p.y, -0.6, 0.3))
		c = mischen(c, V["bauch"], weich(-n.z, 0.2, 0.8) * weich(p.z, 0.7, 0.85))
		c = mischen(c, V["bauch"], nahe(p, (0, 0.55, 1.0), 0.1))                       # Spiegel
		c = mischen(c, V["beine"], 1 - weich(p.z, 0.4, 0.7))
		c = mischen(c, V["geweih"], weich(p.z, 1.62, 1.7) * weich(abs(p.x), 0.05, 0.08))
		c = mischen(c, V["gesicht"], nahe(p, (0, -0.9, 1.43), 0.05))
		return c
	return f


def hirsch_augen(obs, mat_auge, mat_nase):
	for x in (0.055, -0.055):
		obs.append(tf.kugel("auge", (x, -0.75, 1.53), 0.014, mat_auge))
	obs.append(tf.kugel("nase", (0, -0.94, 1.42), 0.022, mat_nase))


HIRSCH_KNOCHEN = vierbeiner_knochen((0.35, 1.0), (-0.3, 1.05), [(0.1, -0.3, 0.95), (0.11, -0.36, 0.62), (0.09, -0.33, 0.35), (0.085, -0.37, 0.02)],
	[(0.1, 0.42, 0.98), (0.12, 0.3, 0.66), (0.09, 0.48, 0.42), (0.085, 0.41, 0.02)], (0, -0.62, 1.45), (0, -0.92, 1.42),
	[(0, 0.56, 1.05), (0, 0.62, 0.95)])


# ================================================================ Riesenkrabbe


def krabbe_form(F):
	"""Riesenkrabbe: Panzer ~1,3 m breit, 8 Laufbeine, 2 große Scheren, Stielaugen."""
	F.ellipsoid((0, 0, 0.55), (0.65, 0.48, 0.2), k=0.05)
	F.ellipsoid((0, -0.1, 0.62), (0.5, 0.36, 0.18), k=0.08)
	for i in range(6):   # Zacken am Vorderrand
		a = -0.9 + 0.36 * i
		F.kapsel((0.6 * math.sin(a), -0.42 * math.cos(a), 0.56), (0.72 * math.sin(a), -0.52 * math.cos(a), 0.6), 0.035, 0.005, k=0.03)
	for sg in (1, -1):
		for i in range(4):
			y = -0.12 + 0.17 * i
			a = (0.55 * sg, y, 0.5)
			b = (1.0 * sg, y + 0.05 * i, 0.75)
			c = (1.25 * sg, y + 0.12 * i, 0.03)
			F.kette([a, b, c], [0.06, 0.045, 0.015], k=0.02)
		# Schere: Arm, Hand, zwei Finger
		F.kette([(0.4 * sg, -0.35, 0.5), (0.65 * sg, -0.7, 0.55), (0.55 * sg, -0.95, 0.5)], [0.08, 0.07, 0.06], k=0.03)
		F.ellipsoid((0.5 * sg, -1.1, 0.5), (0.13, 0.2, 0.11), k=0.03)
		F.kapsel((0.48 * sg, -1.25, 0.53), (0.4 * sg, -1.48, 0.55), 0.06, 0.015, k=0.02)
		F.kapsel((0.5 * sg, -1.25, 0.45), (0.42 * sg, -1.45, 0.44), 0.045, 0.012, k=0.02)
		F.kapsel((0.12 * sg, -0.38, 0.66), (0.14 * sg, -0.46, 0.8), 0.022, 0.018, k=0.01)   # Augenstiel


def krabbe_farbe(V):
	def f(p, n):
		c = mischen(V["bauch"], V["ruecken"], weich(n.z, -0.2, 0.5))
		c = mischen(c, V["spitzen"], weich(-p.y, 1.3, 1.45))
		from mathutils import noise
		c = mischen(c, V["seite"], 0.4 * weich(noise.noise(p * 6), 0.1, 0.5))
		return c
	return f


def krabbe_augen(obs, mat_auge, mat_nase):
	for x in (0.14, -0.14):
		obs.append(tf.kugel("auge", (x, -0.47, 0.82), 0.03, mat_nase))


KRABBE_KNOCHEN = [("Body", (0, 0.2, 0.55), (0, -0.2, 0.55), None)]
for _s, _n in ((1, "Left"), (-1, "Right")):
	for _i in range(4):
		_y = -0.12 + 0.17 * _i
		KRABBE_KNOCHEN += [(_n + "Leg%d" % (_i + 1), (0.55 * _s, _y, 0.5), (1.0 * _s, _y + 0.05 * _i, 0.75), "Body"),
			(_n + "Leg%dEnd" % (_i + 1), (1.0 * _s, _y + 0.05 * _i, 0.75), (1.25 * _s, _y + 0.12 * _i, 0.03), _n + "Leg%d" % (_i + 1))]
	KRABBE_KNOCHEN += [(_n + "Arm", (0.4 * _s, -0.35, 0.5), (0.65 * _s, -0.7, 0.55), "Body"),
		(_n + "Claw", (0.65 * _s, -0.7, 0.55), (0.5 * _s, -1.2, 0.5), _n + "Arm"),
		(_n + "Pincer", (0.5 * _s, -1.25, 0.45), (0.42 * _s, -1.45, 0.44), _n + "Claw")]


# ================================================================ Riesenspinne


def spinne_form(F):
	"""Riesenspinne: Körper ~1,6 m lang, hohe Kniegelenke, Kieferklauen."""
	F.ellipsoid((0, 0.45, 0.75), (0.4, 0.55, 0.38), k=0.04, kipp=-0.25)         # Hinterleib
	F.ellipsoid((0, -0.25, 0.6), (0.26, 0.32, 0.16), k=0.04)                     # Kopfbrust
	F.kapsel((0, -0.02, 0.62), (0, 0.06, 0.66), 0.09, 0.09, k=0.05)            # Taille
	for sg in (1, -1):
		for i, (wink, lang) in enumerate(((-0.75, 1.3), (-0.3, 1.15), (0.2, 1.1), (0.65, 1.3))):
			a = Vector((0.2 * sg, -0.3 + 0.12 * i, 0.58))
			rich = Vector((math.cos(wink) * sg, math.sin(wink), 0))
			knie = a + rich * lang * 0.42 + Vector((0, 0, 0.55))
			fuss = a + rich * lang + Vector((0, 0, -0.56))
			mitte = knie + (fuss - knie) * 0.45 + rich * 0.12
			F.kette([tuple(a), tuple(knie), tuple(mitte), tuple(fuss)], [0.055, 0.04, 0.03, 0.01], k=0.02)
		F.kapsel((0.07 * sg, -0.55, 0.58), (0.06 * sg, -0.65, 0.42), 0.045, 0.01, k=0.02)       # Kieferklauen
		F.kapsel((0.12 * sg, -0.5, 0.6), (0.22 * sg, -0.7, 0.52), 0.03, 0.02, k=0.02)           # Taster


def spinne_fell(p, hoehe=1.0):
	return 0.006 * hoehe * weich(p.y, -0.1, 0.1)


def spinne_farbe(V):
	def f(p, n):
		c = mischen(V["bauch"], V["ruecken"], weich(n.z, -0.2, 0.4))
		c = mischen(c, V["beine"], weich(abs(p.x), 0.28, 0.4))
		# Streifen auf dem Hinterleib
		c = mischen(c, V["spitzen"], weich(math.sin(p.y * 22), 0.6, 0.9) * weich(p.y, 0.1, 0.2) * weich(n.z, 0.2, 0.6))
		c = mischen(c, V["spitzen"], weich(math.sin(math.hypot(p.x, p.y) * 30), 0.8, 0.95) * weich(abs(p.x), 0.4, 0.5))
		return c
	return f


def spinne_augen(obs, mat_auge, mat_nase):
	for x, y, z, r in ((0.05, -0.55, 0.7, 0.03), (-0.05, -0.55, 0.7, 0.03), (0.12, -0.5, 0.71, 0.02), (-0.12, -0.5, 0.71, 0.02),
			(0.07, -0.47, 0.75, 0.018), (-0.07, -0.47, 0.75, 0.018), (0.15, -0.44, 0.72, 0.014), (-0.15, -0.44, 0.72, 0.014)):
		obs.append(tf.kugel("auge", (x, y, z), r, mat_nase))


SPINNE_KNOCHEN = [("Body", (0, 0.1, 0.62), (0, -0.4, 0.6), None), ("Abdomen", (0, 0.06, 0.66), (0, 0.9, 0.85), "Body")]
for _s, _n in ((1, "Left"), (-1, "Right")):
	for _i, (_w, _l) in enumerate(((-0.75, 1.3), (-0.3, 1.15), (0.2, 1.1), (0.65, 1.3))):
		_a = Vector((0.2 * _s, -0.3 + 0.12 * _i, 0.58))
		_r = Vector((math.cos(_w) * _s, math.sin(_w), 0))
		_k = _a + _r * _l * 0.42 + Vector((0, 0, 0.55))
		_f = _a + _r * _l + Vector((0, 0, -0.56))
		SPINNE_KNOCHEN += [(_n + "Leg%d" % (_i + 1), tuple(_a), tuple(_k), "Body"), (_n + "Leg%dEnd" % (_i + 1), tuple(_k), tuple(_f), _n + "Leg%d" % (_i + 1))]


# ================================================================ Humanoide Ungeheuer (Moorschrat, Kalistare)


def humanoid_knochen(P):
	"""P: Punkte hips, chest, neck, head, kopf_ende, schulter, ellbogen, hand, hand_ende, huefte, knie, fuss, zehe (links, +x)."""
	K = [("Hips", P["hips"], P["chest"], None), ("Chest", P["chest"], P["neck"], "Hips"),
		("Neck", P["neck"], P["head"], "Chest"), ("Head", P["head"], P["kopf_ende"], "Neck")]
	for sg, n in ((1, "Left"), (-1, "Right")):
		m = lambda q: (q[0] * sg, q[1], q[2])
		K += [(n + "UpperArm", m(P["schulter"]), m(P["ellbogen"]), "Chest"), (n + "LowerArm", m(P["ellbogen"]), m(P["hand"]), n + "UpperArm"),
			(n + "Hand", m(P["hand"]), m(P["hand_ende"]), n + "LowerArm"),
			(n + "UpperLeg", m(P["huefte"]), m(P["knie"]), "Hips"), (n + "LowerLeg", m(P["knie"]), m(P["fuss"]), n + "UpperLeg"),
			(n + "Foot", m(P["fuss"]), m(P["zehe"]), n + "LowerLeg")]
	return K


def schrat_form(F):
	"""Moorschrat: ~2,6 m, gebeugt, lange Arme bis zum Knie, kleiner Kopf vorgeschoben, Rinde und Moos."""
	F.ellipsoid((0, 0.0, 1.45), (0.42, 0.32, 0.45), k=0.1, kipp=-0.35)          # Brust/Buckel
	F.ellipsoid((0, 0.05, 1.0), (0.34, 0.26, 0.3), k=0.12)                       # Bauch
	F.ellipsoid((0, 0.08, 1.85), (0.3, 0.25, 0.18), k=0.1)                       # Nackenbuckel
	F.ellipsoid((0, -0.3, 1.8), (0.14, 0.16, 0.16), k=0.06)                      # Kopf
	F.kapsel((0, -0.38, 1.72), (0, -0.48, 1.66), 0.09, 0.06, k=0.05)          # Maul
	for sg in (1, -1):
		F.kette([(0.4 * sg, -0.02, 1.75), (0.62 * sg, -0.1, 1.25), (0.68 * sg, -0.28, 0.72), (0.66 * sg, -0.34, 0.5)],
			[0.16, 0.12, 0.1, 0.11], k=0.06)
		F.ellipsoid((0.66 * sg, -0.36, 0.42), (0.13, 0.12, 0.16), k=0.05)        # Pranke
		for j in range(3):
			F.kapsel((0.62 * sg + 0.04 * j * sg, -0.38, 0.33), (0.6 * sg + 0.06 * j * sg, -0.46, 0.18), 0.035, 0.012, k=0.02)
		F.kette([(0.2 * sg, 0.08, 0.9), (0.28 * sg, -0.08, 0.5), (0.26 * sg, 0.05, 0.1)], [0.17, 0.13, 0.11], k=0.06)
		F.ellipsoid((0.27 * sg, -0.05, 0.06), (0.12, 0.2, 0.07), k=0.04)
		F.kapsel((0.1 * sg, -0.42, 1.68), (0.16 * sg, -0.46, 1.78), 0.025, 0.006, k=0.01)   # Hauer
	# Äste und Knorren auf dem Rücken
	for i, (x, y, z, dx, dz) in enumerate(((0.15, 0.25, 1.9, 0.1, 0.35), (-0.2, 0.28, 1.75, -0.18, 0.3), (0.0, 0.3, 1.55, 0.0, 0.2),
			(0.3, 0.2, 1.6, 0.25, 0.15), (-0.32, 0.2, 1.45, -0.2, 0.1))):
		F.kapsel((x, y, z), (x + dx, y + 0.12, z + dz), 0.04, 0.008, k=0.04)


def schrat_rinde(ob):
	"""Rindenfurchen: senkrecht gestreckte Rauschrillen."""
	from mathutils import noise
	me = ob.data
	n = len(me.vertices)
	P, N = np.empty(n * 3), np.empty(n * 3)
	me.vertices.foreach_get("co", P)
	me.vertices.foreach_get("normal", N)
	P, N = P.reshape(-1, 3), N.reshape(-1, 3)
	for i in range(n):
		p = Vector(P[i])
		r = 1 - abs(noise.noise(Vector((p.x * 14, p.y * 14, p.z * 3))))
		P[i] -= N[i] * 0.02 * r ** 4
	me.vertices.foreach_set("co", P.ravel())
	me.update()


def schrat_farbe(V):
	def f(p, n):
		from mathutils import noise
		c = mischen(V["seite"], V["ruecken"], 0.5 + 0.5 * noise.noise(p * 3))
		moos = weich(n.z, 0.2, 0.7) * weich(noise.noise(p * 4 + Vector((5, 5, 5))), -0.2, 0.3)
		c = mischen(c, V["moos"], moos)
		c = mischen(c, V["bauch"], weich(-p.z, -0.4, -0.1))   # schlammige Füße
		return c
	return f


def schrat_augen(obs, mat_auge, mat_nase):
	for x in (0.06, -0.06):
		obs.append(tf.kugel("auge", (x, -0.43, 1.84), 0.022, mat_auge))


SCHRAT_KNOCHEN = humanoid_knochen({"hips": (0, 0.05, 0.95), "chest": (0, 0.0, 1.4), "neck": (0, -0.1, 1.82), "head": (0, -0.25, 1.78),
	"kopf_ende": (0, -0.5, 1.75), "schulter": (0.4, -0.02, 1.75), "ellbogen": (0.62, -0.1, 1.25), "hand": (0.68, -0.28, 0.72),
	"hand_ende": (0.64, -0.4, 0.3), "huefte": (0.2, 0.08, 0.9), "knie": (0.28, -0.08, 0.5), "fuss": (0.26, 0.05, 0.1), "zehe": (0.27, -0.2, 0.05)})


# ================================================================ Kalistare (Dämonen aus dem Portal)


def kristall(obs, mat, basis, richtung, laenge, radius):
	"""Zahr-Kristall: sechseckiges Prisma mit Spitze (eigenes Objekt, leuchtend)."""
	import bmesh
	d = Vector(richtung).normalized()
	q = d.orthogonal().normalized()
	r = d.cross(q)
	bm = bmesh.new()
	unten, oben = [], []
	for k in range(6):
		a = k * math.pi / 3
		o = (q * math.cos(a) + r * math.sin(a)) * radius
		unten.append(bm.verts.new(Vector(basis) + o - d * radius))
		oben.append(bm.verts.new(Vector(basis) + o + d * laenge * 0.7))
	spitze = bm.verts.new(Vector(basis) + d * laenge)
	for k in range(6):
		j = (k + 1) % 6
		bm.faces.new([unten[k], unten[j], oben[j], oben[k]])
		bm.faces.new([oben[k], oben[j], spitze])
	bm.faces.new(list(reversed(unten)))
	me = bpy.data.meshes.new("kristall")
	bm.to_mesh(me)
	bm.free()
	me.materials.append(mat)
	ob = bpy.data.objects.new("kristall", me)
	bpy.context.scene.collection.objects.link(ob)
	obs.append(ob)


def risse(ob, tiefe=0.008, skala=7.0):
	"""Zahr-Risse: Zellkanten eingeschnitten (die Farbe leuchtet dort)."""
	from mathutils import noise
	me = ob.data
	n = len(me.vertices)
	P, N = np.empty(n * 3), np.empty(n * 3)
	me.vertices.foreach_get("co", P)
	me.vertices.foreach_get("normal", N)
	P, N = P.reshape(-1, 3), N.reshape(-1, 3)
	for i in range(n):
		d = noise.voronoi(Vector(P[i]) * skala)[0]
		P[i] -= N[i] * tiefe * (1 - weich(d[1] - d[0], 0.0, 0.08))
	me.vertices.foreach_set("co", P.ravel())
	me.update()


def kalistar_farbe(V):
	def f(p, n):
		from mathutils import noise
		d = noise.voronoi(p * V.get("riss_skala", 7.0))[0]
		riss = 1 - weich(d[1] - d[0], 0.0, 0.07)
		c = mischen(V["seite"], V["ruecken"], weich(n.z, 0.0, 0.7))
		c = mischen(c, V["glut"], riss)
		return c
	return f


def splitterling_form(F):
	"""Splitterling: ~0,6 m hoch, kriecht auf vier Klauenbeinen, Rücken voller Splitter."""
	F.ellipsoid((0, 0.05, 0.45), (0.2, 0.32, 0.17), k=0.05)
	F.ellipsoid((0, -0.32, 0.42), (0.13, 0.14, 0.11), k=0.04)
	F.kapsel((0, -0.4, 0.38), (0, -0.55, 0.33), 0.07, 0.03, k=0.03)
	F.spiegeln(F.kapsel, [0.05, -0.52, 0.32], [0.07, -0.62, 0.22], 0.02, 0.004, k=0.01)    # Kiefer
	for sg in (1, -1):
		for y, vor in ((-0.15, -1), (0.2, 1)):
			F.kette([(0.15 * sg, y, 0.45), (0.38 * sg, y + 0.05 * vor, 0.55), (0.45 * sg, y + 0.1 * vor, 0.02)], [0.05, 0.035, 0.008], k=0.02)
	F.kette([(0, 0.35, 0.45), (0, 0.6, 0.35), (0, 0.8, 0.4)], [0.06, 0.035, 0.01], k=0.03)


def splitterling_extra(obs, mat):
	import random
	rnd = random.Random(3)
	for i in range(14):
		y = -0.25 + 0.06 * i
		x = rnd.uniform(-0.12, 0.12)
		kristall(obs, mat, (x, y, 0.56 - abs(y - 0.05) * 0.25), (x * 2, rnd.uniform(-0.2, 0.4), 1), rnd.uniform(0.1, 0.22), 0.025)


def krieger_form(F):
	"""Kalistar-Krieger: ~2,2 m, Hörner, lange Klauen, Hinterläufe wie ein Tier (Zehengänger), gezackte Schultern."""
	F.ellipsoid((0, 0.0, 1.5), (0.32, 0.2, 0.28), k=0.08, kipp=-0.15)
	F.ellipsoid((0, 0.02, 1.12), (0.2, 0.15, 0.2), k=0.1)
	F.ellipsoid((0, -0.1, 1.95), (0.1, 0.12, 0.13), k=0.05)
	F.kapsel((0, -0.12, 1.88), (0, -0.2, 1.84), 0.07, 0.05, k=0.04)
	F.kapsel((0, -0.02, 1.7), (0, -0.08, 1.85), 0.09, 0.07, k=0.05)
	for sg in (1, -1):
		F.kette([(0.07 * sg, -0.08, 2.03), (0.2 * sg, 0.0, 2.12), (0.28 * sg, 0.12, 2.06), (0.3 * sg, 0.2, 1.92)], [0.035, 0.03, 0.02, 0.004], k=0.02)
		F.kette([(0.34 * sg, 0.0, 1.65), (0.55 * sg, -0.05, 1.3), (0.62 * sg, -0.15, 0.95)], [0.09, 0.07, 0.06], k=0.04)
		for j in range(3):
			F.kapsel((0.62 * sg + 0.03 * (j - 1) * sg, -0.17, 0.92), (0.63 * sg + 0.05 * (j - 1) * sg, -0.3, 0.6), 0.022, 0.003, k=0.015)
		for j in range(3):   # Schulterstacheln
			F.kapsel((0.3 * sg, 0.02 + 0.04 * j, 1.72), (0.45 * sg, 0.08 + 0.06 * j, 1.95 - 0.06 * j), 0.04, 0.004, k=0.02)
		# Bein: Oberschenkel nach vorne, Unterschenkel zurück, langer Mittelfuß
		F.kette([(0.15 * sg, 0.02, 1.0), (0.2 * sg, -0.2, 0.65), (0.18 * sg, 0.12, 0.3), (0.18 * sg, 0.02, 0.04), (0.18 * sg, -0.12, 0.02)],
			[0.11, 0.07, 0.05, 0.04, 0.03], k=0.04)
	F.kette([(0, 0.15, 1.0), (0, 0.45, 0.7), (0, 0.6, 0.35), (0, 0.65, 0.15)], [0.06, 0.04, 0.025, 0.004], k=0.03)   # Schwanz
	for i in range(5):   # Rückenstacheln
		F.kapsel((0, 0.15, 1.75 - 0.15 * i), (0, 0.32, 1.85 - 0.15 * i), 0.035, 0.004, k=0.02)


KRIEGER_KNOCHEN = humanoid_knochen({"hips": (0, 0.02, 1.0), "chest": (0, 0.0, 1.4), "neck": (0, -0.02, 1.7), "head": (0, -0.08, 1.85),
	"kopf_ende": (0, -0.1, 2.1), "schulter": (0.34, 0.0, 1.65), "ellbogen": (0.55, -0.05, 1.3), "hand": (0.62, -0.15, 0.95),
	"hand_ende": (0.63, -0.3, 0.6), "huefte": (0.15, 0.02, 1.0), "knie": (0.2, -0.2, 0.65), "fuss": (0.18, 0.12, 0.3), "zehe": (0.18, -0.12, 0.02)})


def seher_form(F):
	"""Kalistar-Seher: schwebt ~0,4 m über dem Boden, schmaler Leib läuft in einen Schweif aus, lange Arme, Stachelkrone."""
	F.ellipsoid((0, 0.0, 1.75), (0.22, 0.14, 0.26), k=0.07)
	F.kette([(0, 0.0, 1.5), (0, 0.05, 1.1), (0, 0.12, 0.75), (0, 0.18, 0.45)], [0.14, 0.09, 0.05, 0.01], k=0.06)
	F.ellipsoid((0, -0.05, 2.2), (0.09, 0.11, 0.13), k=0.04)
	F.kapsel((0, -0.03, 1.98), (0, -0.05, 2.12), 0.06, 0.05, k=0.04)
	for i in range(7):   # Krone
		a = -1.2 + 0.4 * i
		F.kapsel((0.08 * math.sin(a), -0.05 + 0.06 * math.cos(a), 2.28), (0.16 * math.sin(a), -0.03 + 0.1 * math.cos(a), 2.5), 0.02, 0.003, k=0.015)
	for sg in (1, -1):
		F.kette([(0.22 * sg, 0.0, 1.9), (0.5 * sg, -0.12, 1.75), (0.62 * sg, -0.35, 1.7), (0.6 * sg, -0.5, 1.75)], [0.06, 0.045, 0.035, 0.02], k=0.03)
		for j in range(4):
			F.kapsel((0.6 * sg, -0.5, 1.75), (0.58 * sg + 0.03 * (j - 1.5) * sg, -0.68, 1.8 + 0.04 * (j - 1.5)), 0.012, 0.002, k=0.008)
		# Fetzen/Flügelreste am Rücken
		F.kette([(0.12 * sg, 0.12, 1.95), (0.4 * sg, 0.3, 2.2), (0.55 * sg, 0.35, 1.7), (0.45 * sg, 0.3, 1.3)], [0.03, 0.02, 0.015, 0.004], k=0.02)


def seher_extra(obs, mat):
	kristall(obs, mat, (0, -0.62, 1.85), (0, 0, 1), 0.28, 0.06)          # schwebender Zahr-Kristall zwischen den Händen
	kristall(obs, mat, (0, -0.62, 1.85), (0, 0, -1), 0.18, 0.06)


SEHER_KNOCHEN = humanoid_knochen({"hips": (0, 0.05, 1.1), "chest": (0, 0.0, 1.6), "neck": (0, -0.03, 1.98), "head": (0, -0.05, 2.1),
	"kopf_ende": (0, -0.05, 2.4), "schulter": (0.22, 0.0, 1.9), "ellbogen": (0.5, -0.12, 1.75), "hand": (0.62, -0.35, 1.7),
	"hand_ende": (0.6, -0.6, 1.78), "huefte": (0.0, 0.08, 1.0), "knie": (0.0, 0.12, 0.75), "fuss": (0.0, 0.18, 0.45), "zehe": (0.0, 0.2, 0.4)})


def koloss_form(F):
	"""Zahr-Koloss: ~4,5 m, Gestein mit Zahr-Adern, riesige Arme, kleiner Kopf tief zwischen den Schultern."""
	F.ellipsoid((0, 0.0, 3.0), (0.95, 0.6, 0.75), k=0.15, kipp=-0.2)
	F.ellipsoid((0, 0.1, 2.2), (0.6, 0.45, 0.5), k=0.2)
	F.ellipsoid((0, -0.45, 3.35), (0.25, 0.25, 0.25), k=0.1)
	for sg in (1, -1):
		F.ellipsoid((0.95 * sg, 0.0, 3.5), (0.45, 0.45, 0.4), k=0.1)                   # Schulterfels
		F.kette([(1.05 * sg, -0.05, 3.2), (1.3 * sg, -0.2, 2.3), (1.35 * sg, -0.55, 1.5)], [0.35, 0.3, 0.33], k=0.12)
		F.ellipsoid((1.35 * sg, -0.65, 1.15), (0.38, 0.38, 0.42), k=0.1)              # Faust
		F.kette([(0.42 * sg, 0.1, 1.9), (0.5 * sg, -0.15, 1.0), (0.48 * sg, 0.0, 0.2)], [0.38, 0.3, 0.3], k=0.12)
		F.ellipsoid((0.48 * sg, -0.12, 0.15), (0.35, 0.45, 0.17), k=0.08)


def koloss_extra(obs, mat):
	import random
	rnd = random.Random(7)
	for (x, y, z, dx, dy, dz) in ((0.9, 0.2, 3.85, 0.3, 0.2, 1), (-0.95, 0.15, 3.8, -0.3, 0.3, 1), (0.3, 0.5, 3.5, 0.1, 1, 0.6),
			(-0.35, 0.5, 3.4, -0.2, 1, 0.5), (0, 0.55, 2.9, 0, 1, 0.3), (1.45, -0.2, 2.5, 1, 0, 0.3), (-1.45, -0.2, 2.5, -1, 0, 0.3)):
		for k in range(3):
			kristall(obs, mat, (x + rnd.uniform(-0.1, 0.1), y + rnd.uniform(-0.1, 0.1), z + rnd.uniform(-0.1, 0.1)),
				(dx + rnd.uniform(-0.4, 0.4), dy + rnd.uniform(-0.4, 0.4), dz + rnd.uniform(-0.3, 0.3)), rnd.uniform(0.35, 0.7), rnd.uniform(0.07, 0.13))


KOLOSS_KNOCHEN = humanoid_knochen({"hips": (0, 0.1, 2.0), "chest": (0, 0.0, 2.8), "neck": (0, -0.3, 3.3), "head": (0, -0.45, 3.35),
	"kopf_ende": (0, -0.5, 3.65), "schulter": (1.05, -0.05, 3.2), "ellbogen": (1.3, -0.2, 2.3), "hand": (1.35, -0.55, 1.5),
	"hand_ende": (1.35, -0.7, 0.8), "huefte": (0.42, 0.1, 1.9), "knie": (0.5, -0.15, 1.0), "fuss": (0.48, 0.0, 0.2), "zehe": (0.48, -0.5, 0.1)})


def augen_paar(x, y, z, r):
	def f(obs, mat_auge, mat_nase):
		for sx in (x, -x):
			obs.append(tf.kugel("auge", (sx, y, z), r, mat_auge))
	return f


ARTEN = {
	"wildschwein": {
		"form": schwein_form, "fell": schwein_fell, "augen": schwein_augen, "knochen": SCHWEIN_KNOCHEN,
		"farbe": standard_farbe((0.7, 0.9), (0, -0.62, 0.62), (0, -0.88, 0.44), bein_z=(0.15, 0.35)),
		"varianten": {
			"keiler": {"name": "Keiler", "skala": 1.0, "form": {"bache": 0.0},
				"farben": {"ruecken": (0.12, 0.1, 0.08), "seite": (0.27, 0.22, 0.17), "bauch": (0.3, 0.26, 0.2),
					"beine": (0.1, 0.09, 0.08), "gesicht": (0.38, 0.32, 0.27)}},
			"bache": {"name": "Bache", "skala": 0.82, "form": {"bache": 1.0},
				"farben": {"ruecken": (0.2, 0.16, 0.12), "seite": (0.35, 0.28, 0.21), "bauch": (0.4, 0.34, 0.26),
					"beine": (0.16, 0.13, 0.1), "gesicht": (0.45, 0.38, 0.3)}},
		},
	},
	"baer": {
		"form": baer_form, "fell": baer_fell, "augen": baer_augen, "knochen": BAER_KNOCHEN,
		"farbe": standard_farbe((0.9, 1.15), (0, -0.9, 0.86), (0, -1.12, 0.79), bein_z=(0.2, 0.5)),
		"varianten": {
			"braunbaer": {"name": "Braunbär", "skala": 1.0,
				"farben": {"ruecken": (0.33, 0.22, 0.13), "seite": (0.27, 0.17, 0.1), "bauch": (0.22, 0.14, 0.08),
					"beine": (0.16, 0.1, 0.06), "gesicht": (0.42, 0.32, 0.22)}},
			"hoehlenbaer": {"name": "Höhlenbär", "skala": 1.3, "fell": 1.3,
				"farben": {"ruecken": (0.32, 0.27, 0.23), "seite": (0.22, 0.19, 0.17), "bauch": (0.18, 0.15, 0.13),
					"beine": (0.14, 0.12, 0.1), "gesicht": (0.4, 0.35, 0.3)}},
		},
	},
	"bergloewe": {
		"form": loewe_form, "fell": loewe_fell, "augen": loewe_augen, "knochen": LOEWE_KNOCHEN, "farbe": loewe_farbe,
		"varianten": {
			"bergloewe": {"name": "Berglöwe", "skala": 1.0,
				"farben": {"ruecken": (0.48, 0.37, 0.27), "seite": (0.6, 0.48, 0.36), "bauch": (0.86, 0.82, 0.75),
					"gesicht": (0.12, 0.1, 0.08), "spitzen": (0.12, 0.1, 0.08)}},
			"schneeloewe": {"name": "Schneelöwe", "skala": 1.0, "flecken": True,
				"farben": {"ruecken": (0.68, 0.68, 0.66), "seite": (0.8, 0.79, 0.76), "bauch": (0.93, 0.93, 0.92),
					"gesicht": (0.2, 0.2, 0.2), "spitzen": (0.25, 0.25, 0.26)}, "flecken": True},
			"schattenloewe": {"name": "Schattenlöwe", "skala": 1.08,
				"farben": {"ruecken": (0.05, 0.05, 0.055), "seite": (0.08, 0.08, 0.09), "bauch": (0.14, 0.14, 0.15),
					"gesicht": (0.03, 0.03, 0.03), "spitzen": (0.03, 0.03, 0.03)}},
		},
	},
	"krokodil": {
		"form": kroko_form, "fell": kroko_fell, "augen": kroko_augen, "knochen": KROKO_KNOCHEN, "farbe": kroko_farbe,
		"nach": kroko_schuppen, "auge_farbe": (0.55, 0.45, 0.1), "nase_farbe": (0.85, 0.8, 0.65),
		"varianten": {
			"flusskrokodil": {"name": "Flusskrokodil", "skala": 1.0,
				"farben": {"ruecken": (0.2, 0.22, 0.13), "seite": (0.3, 0.3, 0.18), "bauch": (0.7, 0.66, 0.5),
					"spitzen": (0.12, 0.13, 0.08)}},
			"moorkrokodil": {"name": "Moorkrokodil", "skala": 1.35,
				"farben": {"ruecken": (0.13, 0.17, 0.09), "seite": (0.2, 0.23, 0.13), "bauch": (0.5, 0.48, 0.36),
					"spitzen": (0.25, 0.32, 0.12)}},
		},
	},
	"hirsch": {
		"form": hirsch_form, "fell": hirsch_fell, "augen": hirsch_augen, "knochen": HIRSCH_KNOCHEN, "farbe": hirsch_farbe,
		"varianten": {
			"hirsch": {"name": "Hirsch", "skala": 1.0, "form": {"geweih": True},
				"farben": {"ruecken": (0.36, 0.24, 0.15), "seite": (0.5, 0.34, 0.21), "bauch": (0.82, 0.74, 0.62),
					"beine": (0.38, 0.28, 0.2), "gesicht": (0.15, 0.12, 0.1), "geweih": (0.62, 0.55, 0.45)}},
			"hirschkuh": {"name": "Hirschkuh", "skala": 0.9, "form": {"geweih": False},
				"farben": {"ruecken": (0.42, 0.29, 0.18), "seite": (0.56, 0.39, 0.25), "bauch": (0.85, 0.77, 0.65),
					"beine": (0.42, 0.31, 0.22), "gesicht": (0.15, 0.12, 0.1), "geweih": (0.56, 0.39, 0.25)}},
		},
	},
	"riesenkrabbe": {
		"form": krabbe_form, "fell": lambda p, h=1.0: 0.0, "augen": krabbe_augen, "knochen": KRABBE_KNOCHEN, "farbe": krabbe_farbe,
		"nach": lambda ob: risse(ob, 0.004, 9.0),
		"varianten": {
			"riesenkrabbe": {"name": "Riesenkrabbe", "skala": 1.0,
				"farben": {"ruecken": (0.62, 0.22, 0.12), "seite": (0.45, 0.14, 0.08), "bauch": (0.88, 0.78, 0.62), "spitzen": (0.12, 0.08, 0.06)}},
			"felsenkrabbe": {"name": "Felsenkrabbe", "skala": 1.25,
				"farben": {"ruecken": (0.33, 0.33, 0.3), "seite": (0.22, 0.24, 0.2), "bauch": (0.7, 0.66, 0.56), "spitzen": (0.08, 0.08, 0.07)}},
		},
	},
	"riesenspinne": {
		"form": spinne_form, "fell": spinne_fell, "augen": spinne_augen, "knochen": SPINNE_KNOCHEN, "farbe": spinne_farbe,
		"nase_farbe": (0.02, 0.02, 0.02),
		"varianten": {
			"waldspinne": {"name": "Waldspinne", "skala": 1.0,
				"farben": {"ruecken": (0.25, 0.18, 0.12), "seite": (0.2, 0.15, 0.1), "bauch": (0.12, 0.1, 0.08), "beine": (0.3, 0.22, 0.15),
					"spitzen": (0.6, 0.48, 0.3)}},
			"hoehlenspinne": {"name": "Höhlenspinne", "skala": 1.3,
				"farben": {"ruecken": (0.72, 0.68, 0.6), "seite": (0.6, 0.56, 0.5), "bauch": (0.45, 0.42, 0.38), "beine": (0.65, 0.6, 0.53),
					"spitzen": (0.25, 0.22, 0.2)}},
		},
	},
	"moorschrat": {
		"form": schrat_form, "fell": lambda p, h=1.0: 0.0, "augen": schrat_augen, "knochen": SCHRAT_KNOCHEN, "farbe": schrat_farbe,
		"nach": schrat_rinde, "auge_farbe": (0.9, 0.75, 0.2),
		"varianten": {
			"moorschrat": {"name": "Moorschrat", "skala": 1.0,
				"farben": {"ruecken": (0.25, 0.2, 0.14), "seite": (0.34, 0.27, 0.18), "bauch": (0.15, 0.12, 0.08), "moos": (0.25, 0.36, 0.12)}},
		},
	},
	"kalistare": {
		"varianten": {
			"splitterling": {"name": "Splitterling", "skala": 1.0, "form_fn": splitterling_form, "extra": splitterling_extra,
				"augen": augen_paar(0.06, -0.42, 0.47, 0.018), "knochen": vierbeiner_knochen((0.25, 0.45), (-0.2, 0.45),
					[(0.15, -0.15, 0.45), (0.38, -0.2, 0.55), (0.45, -0.25, 0.02), (0.46, -0.3, 0.0)],
					[(0.15, 0.2, 0.45), (0.38, 0.25, 0.55), (0.45, 0.3, 0.02), (0.46, 0.35, 0.0)], (0, -0.4, 0.4), (0, -0.56, 0.33),
					[(0, 0.35, 0.45), (0, 0.6, 0.35), (0, 0.8, 0.4)]),
				"farben": {"ruecken": (0.08, 0.05, 0.05), "seite": (0.15, 0.06, 0.06), "glut": (1.0, 0.35, 0.08)}},
			"kalistar_krieger": {"name": "Kalistar-Krieger", "skala": 1.0, "form_fn": krieger_form,
				"augen": augen_paar(0.045, -0.2, 1.97, 0.016), "knochen": KRIEGER_KNOCHEN,
				"farben": {"ruecken": (0.1, 0.06, 0.06), "seite": (0.22, 0.05, 0.05), "glut": (1.0, 0.35, 0.08)}},
			"kalistar_seher": {"name": "Kalistar-Seher", "skala": 1.0, "form_fn": seher_form, "extra": seher_extra,
				"augen": augen_paar(0.04, -0.15, 2.23, 0.015), "knochen": SEHER_KNOCHEN,
				"farben": {"ruecken": (0.05, 0.04, 0.06), "seite": (0.14, 0.05, 0.1), "glut": (1.0, 0.3, 0.12)}},
			"zahr_koloss": {"name": "Zahr-Koloss", "skala": 1.0, "form_fn": koloss_form, "extra": koloss_extra, "raster": 0.016,
				"augen": augen_paar(0.1, -0.68, 3.4, 0.04), "knochen": KOLOSS_KNOCHEN, "riss_skala": 2.5, "risse": (0.03, 2.5),
				"farben": {"ruecken": (0.2, 0.17, 0.16), "seite": (0.13, 0.1, 0.1), "glut": (1.0, 0.4, 0.1)}},
		},
		"fell": lambda p, h=1.0: 0.0, "farbe": kalistar_farbe, "auge_farbe": (1.0, 0.55, 0.1), "kalistar": True,
	},
	"wolf": {
		"form": wolf_form, "fell": wolf_fell, "farbe": wolf_farbe, "augen": wolf_augen, "knochen": WOLF_KNOCHEN,
		"varianten": {
			"grauwolf": {"name": "Grauwolf", "skala": 1.0, "fell": 1.0,
				"farben": {"ruecken": (0.22, 0.2, 0.18), "seite": (0.45, 0.41, 0.36), "bauch": (0.78, 0.74, 0.66),
					"beine": (0.58, 0.5, 0.4), "gesicht": (0.8, 0.76, 0.7), "spitzen": (0.12, 0.11, 0.1)}},
			"schneewolf": {"name": "Schneewolf", "skala": 1.05, "fell": 1.35,
				"farben": {"ruecken": (0.78, 0.78, 0.79), "seite": (0.88, 0.88, 0.88), "bauch": (0.95, 0.95, 0.94),
					"beine": (0.9, 0.9, 0.89), "gesicht": (0.95, 0.95, 0.95), "spitzen": (0.6, 0.6, 0.62)}},
			"moorwolf": {"name": "Moorwolf", "skala": 0.95, "fell": 0.8, "mager": 1.0,
				"farben": {"ruecken": (0.16, 0.14, 0.1), "seite": (0.33, 0.28, 0.2), "bauch": (0.45, 0.4, 0.3),
					"beine": (0.25, 0.21, 0.16), "gesicht": (0.45, 0.4, 0.3), "spitzen": (0.08, 0.07, 0.06)}},
			"leitwolf": {"name": "Leitwolf", "skala": 1.3, "fell": 1.2,
				"farben": {"ruecken": (0.07, 0.07, 0.075), "seite": (0.14, 0.14, 0.15), "bauch": (0.3, 0.3, 0.3),
					"beine": (0.17, 0.17, 0.17), "gesicht": (0.32, 0.32, 0.32), "spitzen": (0.05, 0.05, 0.05)}},
		},
	},
}


def bauen(art, variante, saat=0):
	"""Baut eine Variante und gibt (Netz-Objekte, Skelett) zurück."""
	A = ARTEN[art]
	V = A["varianten"][variante]
	F = tf.Form()
	if "form_fn" in V:
		V["form_fn"](F)
	elif "mager" in V:
		A["form"](F, V["mager"])
	else:
		A["form"](F, **V.get("form", {}))
	koerper = F.netz(variante, raster=float(V.get("raster", os.environ.get("RASTER", "0.007"))))
	tf.glaetten(koerper, 3, 0.6)
	tf.verringern(koerper, int(os.environ.get("VOR_FELL", "120000")))
	tf.fell(koerper, lambda p: A["fell"](p, V.get("fell", 1.0)), saat=saat)
	tf.glaetten(koerper, 1, 0.3)
	if A.get("nach"):
		A["nach"](koerper)
	if A.get("kalistar"):
		risse(koerper, *V.get("risse", (0.008, 7.0)))
	tf.verringern(koerper, int(os.environ.get("MAX_FL", "40000")))
	for p in koerper.data.polygons:
		p.use_smooth = True
	fv = dict(V["farben"], flecken=V.get("flecken", False), riss_skala=V.get("riss_skala", 7.0))
	tf.farben(koerper, A["farbe"](fv))
	koerper.data.materials.append(tf.material("fell", punktfarbe=True))
	obs = [koerper]
	augen = V.get("augen", A.get("augen"))
	augen(obs, tf.material("auge", A.get("auge_farbe", (0.25, 0.16, 0.04)), 0.2),
		tf.material("nase", A.get("nase_farbe", (0.03, 0.03, 0.03)), 0.3))
	if V.get("extra"):
		V["extra"](obs, tf.material("zahr", (1.0, 0.4, 0.1), 0.1))
	for o in obs[1:]:
		tf.farben(o, lambda p, n, c=o.data.materials[0].diffuse_color: c[:3])
	arm = tf.skelett(variante + "_skelett", V.get("knochen", A.get("knochen")))
	if os.environ.get("GLB") == "1":
		tf.binden(obs, arm)   # Gewichte nur für den Export (dauert)
	s = V.get("skala", 1.0)
	for o in obs + [arm]:
		o.scale = (s, s, s)   # Größe der Variante (im Spiel als Skalierung)
	return obs, arm


if __name__ == "__main__":
	ARG = sys.argv[sys.argv.index("--") + 1:]
	AUS = ARG[0]
	os.makedirs(AUS, exist_ok=True)
	arten = ARG[1].split(",") if len(ARG) > 1 else list(ARTEN)
	from PIL import Image
	for art in arten:
		bilder = []
		for i, variante in enumerate(ARTEN[art]["varianten"]):
			if len(ARG) > 2 and variante not in ARG[2].split(","):
				continue
			bpy.ops.wm.read_factory_settings(use_empty=True)
			obs, arm = bauen(art, variante, i)
			print(variante, len(obs[0].data.polygons), "Flächen")
			bilder.append(tf.bilder(os.path.join(AUS, variante), obs))
			if os.environ.get("GLB") == "1":
				bpy.ops.object.select_all(action="DESELECT")
				for o in obs + [arm]:
					o.select_set(True)
				bpy.ops.export_scene.gltf(filepath=os.path.join(AUS, variante + ".glb"), use_selection=True,
					export_format="GLB", export_yup=True, export_apply=False, export_skins=True)
