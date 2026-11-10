"""Weitere Formen je Modulart und Tier, bis jedes Tier 5 Formen hat (Philipp, 09.11.).

Die von Hand gebauten Formen bleiben Form 1 bis n. Die übrigen Formen entstehen aus einer Grundform des
Tiers, die gezielt verformt wird: länger, breiter, gebogen, bauchig, gedreht … Die Anschlussstellen
(Klingenansatz, Tülle, Sehnenenden, Griffmitte) bleiben dabei fest, damit alle Module weiter zusammenpassen.
Der Stil des Tiers lenkt die Verformung: Mithril bekommt nur gerade Linien (Knicke statt Bögen),
Darksteel spitze Verläufe, die übrigen weiche Rundungen.

Koordinaten sind die des Blender-Bauraums vor dem Export (Klingen-Rahmen: Länge entlang +Z).
Fernkampf und Schild sind mit schild.umrechnen schon umgerechnet: natürlich (x, y, z) -> Blender (x, -z, -y).
"""
import math
from mathutils import Vector
from geo import anzahl, neue_verts

STIL = {1: "rund", 2: "rund", 3: "gerade", 4: "roh", 5: "rund", 6: "zackig"}
ZIEL = 5


def bauch(u, stil):
	"""0 an beiden Enden, 1 in der Mitte; Form nach Stil."""
	u = min(max(u, 0.0), 1.0)
	if stil == "gerade":
		return 1 - abs(2 * u - 1)
	if stil == "zackig":
		return (1 - abs(2 * u - 1)) ** 0.6
	return math.sin(math.pi * u)


def bogen(u, stil):
	"""0 bei u = 0, wächst zum Ende; gerade = linear (Knick statt Biegung)."""
	u = min(max(u, 0.0), 1.0)
	return u if stil == "gerade" else (u ** 1.6 if stil == "zackig" else u * u)


class Rahmen:
	"""Ausdehnung der neuen Punkte (wird vor dem Verformen bestimmt)."""
	def __init__(self, pts):
		self.min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
		self.max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
		self.mitte = (self.min + self.max) / 2


A = {"x": 0, "y": 1, "z": 2}


def entlang(achse, a0, ende="max"):
	"""u(p, r): 0 am Anschluss a0, 1 am äußersten Ende der Achse."""
	i = A[achse]
	def u(p, r):
		a1 = r.max[i] if ende == "max" else r.min[i]
		if abs(a1 - a0) < 1e-6:
			return 0.0
		return min(max((p[i] - a0) / (a1 - a0), 0.0), 1.0)
	return u


def betrag_entlang(achse, a0=0.0):
	"""u über |Koordinate|: 0 bei a0, 1 am weitesten Punkt (für beidseitige Teile)."""
	i = A[achse]
	def u(p, r):
		m = max(abs(r.max[i]), abs(r.min[i]))
		if m - a0 < 1e-6:
			return 0.0
		return min(max((abs(p[i]) - a0) / (m - a0), 0.0), 1.0)
	return u


# ---------------------------------------------------------------- Verformungen: f(p, r) -> neues p


def _sanft(prof, u):
	"""Am Anschluss (u = 0) bleibt alles wie es ist; die Änderung setzt über die ersten 6 % ein."""
	return 1 + (prof(u) - 1) * min(1.0, u / 0.06)


def breite(u_fn, prof, quer="x", mitte=0.0):
	i = A[quer]
	def f(p, r):
		q = p.copy(); q[i] = mitte + (p[i] - mitte) * _sanft(prof, u_fn(p, r)); return q
	return f


def radial(u_fn, prof, achse="z", mitte=(0.0, 0.0)):
	"""Querschnitt um eine Achse vergrößern/verkleinern."""
	j, k = [i for i in range(3) if i != A[achse]]
	def f(p, r):
		s = _sanft(prof, u_fn(p, r)); q = p.copy()
		q[j] = mitte[0] + (p[j] - mitte[0]) * s; q[k] = mitte[1] + (p[k] - mitte[1]) * s
		return q
	return f


def strecken(achse, a0, s):
	"""Länge ab a0 strecken (nur auf der Seite des Moduls)."""
	i = A[achse]
	def f(p, r):
		q = p.copy()
		if (p[i] - a0) * (1 if r.max[i] - a0 > a0 - r.min[i] else -1) > 0:
			q[i] = a0 + (p[i] - a0) * s
		return q
	return f


def versatz(u_fn, prof, richtung):
	"""Punkte um prof(u) * richtung verschieben (Biegen, Schwingen)."""
	d = Vector(richtung)
	def f(p, r):
		return p + d * prof(u_fn(p, r))
	return f


def drehen(u_fn, winkel, achse="z", mitte=(0.0, 0.0)):
	j, k = [i for i in range(3) if i != A[achse]]
	def f(p, r):
		a = winkel * u_fn(p, r); c, s = math.cos(a), math.sin(a)
		x, y = p[j] - mitte[0], p[k] - mitte[1]
		q = p.copy(); q[j] = mitte[0] + x * c - y * s; q[k] = mitte[1] + x * s + y * c
		return q
	return f


def skalieren(s, anker):
	anker = Vector(anker)
	def f(p, r):
		d = p - anker
		return anker + Vector((d.x * s[0], d.y * s[1], d.z * s[2]))
	return f


def skalieren_rahmen(s, fest):
	"""Skalieren um einen Punkt des Rahmens; fest z.B. ('mitte','mitte','max')."""
	def f(p, r):
		anker = Vector([getattr(r, fest[i])[i] for i in range(3)])
		d = p - anker
		return anker + Vector((d.x * s[0], d.y * s[1], d.z * s[2]))
	return f


def nach(*fs):
	def f(p, r):
		for g in fs:
			p = g(p, r)
		return p
	return f


# ---------------------------------------------------------------- Rezepte je Modulart
# Jedes Rezept: rezept(stil) -> Verformung f(p, r). Die Reihenfolge legt Form n+1, n+2 … fest.


def klingen(a0):
	u = entlang("z", a0)
	return [
		# Blattform: bauchig in der Mitte
		lambda st: breite(u, lambda v: 1 + 0.32 * bauch(v * 0.9, st)),
		# gebogen (Säbel); Mithril: keilförmig breiter zur Spitze statt Biegung
		lambda st: (breite(u, lambda v: 1 + 0.45 * v * (1 - v ** 6)) if st == "gerade" else
					nach(versatz(u, lambda v: 0.06 * bogen(v, st) * (1 if st != "zackig" else 1.2), (1, 0, 0)))),
		# schlank und lang
		lambda st: nach(breite(u, lambda v: 0.78), strecken("z", a0, 1.12)),
		# breit und kurz
		lambda st: nach(breite(u, lambda v: 1.28), strecken("z", a0, 0.86)),
	]


def schaefte(a0, achse="z", r_fest=True):
	"""Stiele, Schäfte, Griffe: Länge bleibt, Querschnitt ändert sich (Enden bleiben passend)."""
	u = entlang(achse, a0)
	def enden(prof):  # an beiden Enden zurück auf 1, damit Kopf und Ende weiter sitzen
		return lambda v: 1 + (prof(v) - 1) * min(1.0, v / 0.08, (1 - v) / 0.12)
	return [
		lambda st: radial(u, enden(lambda v: 1 + 0.16 * bauch(v, st)), achse),
		lambda st: radial(u, enden(lambda v: 0.86), achse),
		lambda st: radial(u, enden(lambda v: 1.12 - 0.22 * v), achse),
		lambda st: (radial(u, enden(lambda v: 1.1 if int(v * 7) % 2 == 0 else 0.95), achse) if st in ("gerade", "zackig") else
					radial(u, enden(lambda v: 1 + 0.07 * math.sin(v * math.pi * 12)), achse)),
	]


def griffe(a0, achse="z"):
	u = entlang(achse, a0)
	return [
		lambda st: radial(u, lambda v: 1 + 0.16 * bauch(v, st), achse),
		lambda st: radial(u, lambda v: 1 - 0.12 * bauch(v, st), achse),
		lambda st: breite(u, lambda v: 1.16, "x"),
		lambda st: radial(u, lambda v: 0.92 + 0.16 * v if st != "gerade" else 1.0 + 0.1 * (v > 0.5), achse),
	]


def kugelig(anker):
	"""Knauf, Schaftende, Buckel, Fokus: Proportionen ändern sich um den Anschluss."""
	return [
		lambda st: skalieren((0.85, 0.85, 1.4), anker),
		lambda st: skalieren((1.2, 1.2, 0.72), anker),
		lambda st: skalieren((1.28, 0.86, 1.0), anker),
		lambda st: skalieren((0.82, 0.82, 0.82), anker),
	]


PZ = 0.09


def parier():
	u = betrag_entlang("x", 0.015)
	return [
		lambda st: skalieren((1.25, 1.0, 1.0), (0, 0, PZ)),
		lambda st: nach(skalieren((0.8, 1.15, 1.3), (0, 0, PZ))),
		lambda st: versatz(u, lambda v: 0.035 * bogen(v, st), (0, 0, 1)),
		lambda st: versatz(u, lambda v: -0.035 * bogen(v, st), (0, 0, 1)),
	]


def axt():
	u = entlang("x", 0.025)
	return [
		lambda st: nach(strecken("x", 0.025, 1.22), breite(u, lambda v: 1 - 0.18 * v, "z", 0.72)),
		lambda st: versatz(lambda p, r: u(p, r) if p.z < 0.72 else 0.0, lambda v: -0.07 * bogen(v, st), (0, 0, 1)),
		lambda st: nach(strecken("x", 0.025, 0.82), breite(u, lambda v: 1 + 0.35 * v, "z", 0.72)),
		lambda st: versatz(u, lambda v: 0.035 * bogen(v, st), (0, 0, 1)),
	]


def hammer():
	u = betrag_entlang("x", 0.03)
	return [
		lambda st: nach(skalieren((1.3, 1, 1), (0, 0, 0.72)), radial(u, lambda v: 0.88, "x", (0, 0.72))),
		lambda st: nach(skalieren((0.85, 1, 1), (0, 0, 0.72)), radial(u, lambda v: 1.25, "x", (0, 0.72))),
		lambda st: radial(u, lambda v: 1 - 0.32 * v, "x", (0, 0.72)),
		lambda st: radial(u, lambda v: 1 + 0.3 * bauch(v, st), "x", (0, 0.72)),
	]


def schildkoerper():
	return [
		lambda st: skalieren((1.15, 0.9, 1.0), (0, 0, 0)),
		lambda st: skalieren((0.88, 1.15, 1.0), (0, 0, 0)),
		lambda st: skalieren((1.0, 1.0, 1.7), (0, 0, 0)),
		lambda st: skalieren((0.86, 0.86, 1.0), (0, 0, 0)),
	]


def wurfarme():
	# Arme entlang Blender y (Enden bei |y| = 0,68), Zugrichtung entlang z; Enden und Griff bleiben fest
	u = betrag_entlang("y", 0.09)
	return [
		lambda st: versatz(u, lambda v: -0.05 * bauch(v, st), (0, 0, 1)),
		lambda st: versatz(u, lambda v: 0.04 * bauch(v, st), (0, 0, 1)),
		lambda st: breite(u, lambda v: 1.35 - 0.25 * v, "x"),
		lambda st: versatz(u, lambda v: 0.03 * math.sin(2 * math.pi * v) if st != "gerade" else 0.03 * (1 - abs(4 * v - 1) if v < 0.5 else -(1 - abs(4 * v - 3))), (0, 0, 1)),
	]


def armbrustbogen():
	u = betrag_entlang("x", 0.05)
	return [
		lambda st: versatz(u, lambda v: -0.04 * bauch(v, st), (0, 0, 1)),
		lambda st: versatz(u, lambda v: 0.035 * bauch(v, st), (0, 0, 1)),
		lambda st: breite(u, lambda v: 1.35 - 0.3 * v, "y", -0.03),
		lambda st: nach(breite(u, lambda v: 0.75, "y", -0.03), versatz(u, lambda v: -0.02 * bogen(v, st), (0, 0, 1))),
	]


def schaft_kolben():
	# Kolben liegt bei Blender z < 0 (natürlich hinten); Höhe entlang Blender y (unten = +y)
	u = entlang("z", 0.0, "min")
	return [
		lambda st: nach(breite(u, lambda v: 1 + 0.25 * v, "y", 0.0), breite(u, lambda v: 1 + 0.15 * v, "x")),
		lambda st: nach(breite(u, lambda v: 1 - 0.15 * v, "y", 0.0), breite(u, lambda v: 0.88, "x")),
		lambda st: versatz(u, lambda v: 0.04 * bogen(v, st), (0, 1, 0)),
		lambda st: versatz(u, lambda v: -0.025 * bogen(v, st), (0, 1, 0)),
	]


def lauf():
	u = entlang("z", 0.02)
	m = (0.0, -0.035)
	return [
		lambda st: radial(u, lambda v: 1.18, "z", m),
		lambda st: radial(u, lambda v: 0.84, "z", m),
		lambda st: radial(u, lambda v: 1 + 0.45 * v ** 4 if st != "gerade" else 1 + 0.3 * (v > 0.9), "z", m),
		lambda st: radial(u, lambda v: 1.12 - 0.26 * v, "z", m),
	]


def sehne():
	u = betrag_entlang("y", 0.0)
	m = (0.0, -0.16)  # Sehne liegt bei Blender z = -0,16
	return [
		lambda st: radial(u, lambda v: 1.6, "y", m),
		lambda st: radial(u, lambda v: 0.7, "y", m),
		lambda st: radial(u, lambda v: 1.6 - 0.8 * v, "y", m),
		lambda st: radial(u, lambda v: 0.8 + 0.8 * v, "y", m),
	]


def koepfe(a0, kz):
	u = entlang("z", a0)
	return [
		lambda st: nach(radial(u, lambda v: 0.82, "z"), strecken("z", kz, 1.15)),
		lambda st: nach(radial(u, lambda v: 1.2, "z"), strecken("z", kz, 0.9)),
		lambda st: drehen(u, 0.7 if st != "gerade" else 0.0, "z") if st != "gerade" else radial(u, lambda v: 1 + 0.3 * v, "z"),
		lambda st: radial(u, lambda v: 1 + 0.4 * v * v, "z"),
	]


def schloss():
	return [
		lambda st: skalieren_rahmen((1.0, 1.15, 1.15), ("min", "mitte", "mitte")),
		lambda st: skalieren_rahmen((1.0, 0.85, 0.85), ("min", "mitte", "mitte")),
		lambda st: skalieren_rahmen((1.3, 1.0, 1.0), ("min", "mitte", "mitte")),
		lambda st: skalieren_rahmen((1.0, 1.0, 1.35), ("min", "mitte", "mitte")),
	]


def korb():
	return [
		lambda st: skalieren((1.15, 1.15, 1.1), (0, 0, PZ)),
		lambda st: skalieren((1.0, 1.0, 1.3), (0, 0, PZ)),
		lambda st: skalieren((1.22, 0.95, 1.0), (0, 0, PZ)),
		lambda st: skalieren((0.95, 1.15, 0.9), (0, 0, PZ)),
	]


def handschuh():
	"""Stulpe länger/kürzer/weiter, Hand kräftiger. Hand, Fassung und Klingenschiene bleiben an ihrem Platz."""
	W, AY = -0.072, -0.03
	def stulpe(fn):
		def f(p, r):
			if p.x >= W:
				return p
			return fn(p, min(1.0, (W - p.x) / 0.16))
		return f
	def laenge(s):
		return stulpe(lambda p, g: Vector((W + (p.x - W) * s, p.y, p.z)))
	def weite(s):
		return stulpe(lambda p, g: Vector((p.x, AY + (p.y - AY) * (1 + (s - 1) * g), p.z * (1 + (s - 1) * g))))
	def kraeftig(p, r):
		if p.x < W:
			return p
		return Vector((p.x * 1.04, AY + (p.y - AY) * 1.06, p.z * 1.05))
	return [
		lambda st: laenge(1.18),
		lambda st: weite(1.16 if st != "gerade" else 1.1),
		lambda st: laenge(0.84),
		lambda st: nach(kraeftig, weite(1.06)),
	]


REZEPTE = {
	"schwertklinge": klingen(0.112),
	"grossschwertklinge": klingen(0.2),
	"degenklinge": klingen(0.112),
	"messerklinge": klingen(0.086),
	"speerspitze": klingen(1.5),
	"parierstange": parier(),
	"knauf": kugelig((0, 0, -0.076)),
	"einhandgriff": griffe(-0.07),
	"zweihandgriff": griffe(-0.12),
	"korb": korb(),
	"stiel": schaefte(-0.3),
	"speerschaft": schaefte(-0.7),
	"stabschaft": schaefte(-0.75),
	"schaftende": kugelig((0, 0, 0)),
	"axtkopf": axt(),
	"hammerkopf": hammer(),
	"schildkoerper": schildkoerper(),
	"schildbuckel": kugelig((0, 0, 0)),
	"wurfarme": wurfarme(),
	"bogengriff": griffe(-0.1, "y"),
	"sehne": sehne(),
	"armbrustbogen": armbrustbogen(),
	"armbrustschaft": schaft_kolben(),
	"musketenschaft": schaft_kolben(),
	"musketenlauf": lauf(),
	"schloss": schloss(),
	"feuerkopf": koepfe(0.86, 0.86),
	"eiskopf": koepfe(0.86, 0.86),
	"blitzkopf": koepfe(0.86, 0.86),
	"lebenskopf": koepfe(0.86, 0.86),
	"handschuh": handschuh(),
	"handklinge": klingen(0.0),
	"fokus": kugelig((0, 0, 0.97)),
}


def auffuellen(arten):
	"""Ergänzt jede Modulart mit Rezept auf 5 Formen je Tier."""
	neu = {}
	for art, tiers in arten.items():
		if art not in REZEPTE:
			neu[art] = tiers
			continue
		neu[art] = {}
		for tier, (n, bauen) in tiers.items():
			neu[art][tier] = (max(n, ZIEL), _bauen(art, tier, n, bauen))
	return neu


def _bauen(art, tier, n, bauen):
	def f(t, form):
		if form <= n:
			return bauen(t, form)
		k = form - n - 1                  # welches Rezept
		basis = k % n + 1                 # aus welcher Grundform
		verformung = REZEPTE[art][k % len(REZEPTE[art])](STIL[tier])
		n0 = anzahl(t)
		bauen(t, basis)
		vs = list(neue_verts(t, n0))
		r = Rahmen([v.co.copy() for v in vs])
		for v in vs:
			v.co = verformung(v.co.copy(), r)
	return f
