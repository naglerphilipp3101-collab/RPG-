"""Palladium-Rüstungen (Tier 2): verziert und edel, Renaissance-Formen.

Eigene Formen je Satz (Helme, Schultern, Schnitte); die Goldzierde an Rändern und Säumen kommt danach aus tierstil.py.
Formensprache: geriffelte Platten, Kämme mit Goldseil, große Schultern mit Brechrand, Schirme und Wangenklappen,
Halskrausen, geschlitzte Puffärmel, gezackte Säume, Diademe. Namen wie Iron: palladium_<satz>_<slot>.
"""
import math

import numpy as np
from mathutils import Vector

import iron as ir
import rgeo as g
import waffensaetze as ws
from iron import ZW, Z0, tabelle
from waffensaetze import AUGE_S, SLOTS, blech, blatt, obj, ring

PI = math.pi
SAETZE = ws.SAETZE


def bauen(K, satz):
	fn = BAU[satz]
	out = {}
	for slot in SLOTS:
		ob = fn[slot](K)
		ob.name = ob.data.name = "palladium_%s_%s" % (satz, slot)
		out[slot] = ob
	return out


# ================================================================ Hilfen


def nach_aussen(f):
	return lambda p: (p - f.c).normalized()


def riffel(n, tiefe=0.004, w0=0.0, breite=PI):
	"""Kehlungen (Maximilian-Riffelung) um w0 herum, n Rippen je Halbkreis."""
	return lambda s, w: tiefe * (0.5 + 0.5 * math.cos(w * n * 2)) * math.exp(-(g.wdiff(w, w0) / breite) ** 2)


def kopf_pfad(f, ab, phi_von, phi_bis, n=48, extra=0.0):
	"""Punkte über den Scheitel: phi < 0 Stirnseite (w = 0), phi > 0 Nacken (w = π)."""
	out = []
	for u in np.linspace(0, 1, n):
		phi = phi_von + (phi_bis - phi_von) * u
		s, w = (abs(phi), 0.0) if phi < 0 else (phi, PI)
		out.append((u, s, w, f.punkt(s, w, g._wert(ab, s, w) if callable(ab) else ab + extra)))
	return out


def finne(t, f, ab, phi_von, phi_bis, hoehe, dicke=0.003, material="platte", seil=True, n=60, versenkt=0.004):
	"""Kamm (Blechfinne) längs über den Kopf, Höhenprofil hoehe(u), oben ein Goldseil aus Perlen."""
	pfad = kopf_pfad(f, ab, phi_von, phi_bis, n)
	unten, oben = [], []
	for u, s, w, p in pfad:
		nn = (p - f.c).normalized()
		unten.append(p - nn * versenkt)
		oben.append(p + nn * hoehe(u))
	# Querschnitt: zwei gewölbte Wangen, unten breit (Fuß), oben schmal, damit das Blech nicht wie ein Spiegel wirkt
	stufen = 5
	fuss = max(dicke, 0.012)
	reihen_r, reihen_l = [], []
	for pu, po in zip(unten, oben):
		zr, zl = [], []
		for k in range(stufen + 1):
			v = k / stufen
			b = dicke / 2 + (fuss / 2 - dicke / 2) * (1 - v) ** 2
			p = pu.lerp(po, v)
			zr.append(t.vert(p + Vector((b, 0, 0))))
			zl.append(t.vert(p - Vector((b, 0, 0))))
		reihen_r.append(zr)
		reihen_l.append(zl)
	for i in range(n - 1):
		for k in range(stufen):
			t.flaeche([reihen_r[i][k], reihen_r[i + 1][k], reihen_r[i + 1][k + 1], reihen_r[i][k + 1]], material)
			t.flaeche([reihen_l[i + 1][k], reihen_l[i][k], reihen_l[i][k + 1], reihen_l[i + 1][k + 1]], material)
		t.flaeche([reihen_r[i][-1], reihen_r[i + 1][-1], reihen_l[i + 1][-1], reihen_l[i][-1]], material)
	for i, umk in ((0, False), (n - 1, True)):
		for k in range(stufen):
			q = [reihen_r[i][k], reihen_r[i][k + 1], reihen_l[i][k + 1], reihen_l[i][k]]
			t.flaeche(list(reversed(q)) if umk else q, material)
	if seil:
		g.zug(t, oben[1:-1], 0.0032, "rand", seg=6)
		for i in range(2, n - 2, 2):
			g.niete(t, oben[i], (oben[i] - f.c).normalized(), 0.0042, "rand")
	return oben


def busch(t, f, ab, phi_von=-0.95, phi_bis=1.65, hoehe=0.075, material="stoff_akzent", lagen=5):
	"""Helmbusch (Rosshaar) längs über den Kopf."""
	for k in range(lagen):
		dx = 0.006 * (k - (lagen - 1) / 2)
		links, rechts = [], []
		for u, s, w, basis in kopf_pfad(f, ab, phi_von, phi_bis, 44, 0.006):
			h = (0.012 + hoehe * math.sin(min(1.0, u * 1.05) * PI) ** 0.5) * (1 - 0.12 * abs(k - (lagen - 1) / 2))
			nn = (basis - f.c).normalized()
			mitte = basis + nn * h * 0.5 + Vector((dx, 0, 0))
			links.append(t.vert(mitte + nn * h * 0.5))
			rechts.append(t.vert(mitte - nn * h * 0.5))
		for i in range(len(links) - 1):
			t.flaeche([links[i], rechts[i], rechts[i + 1], links[i + 1]], material)


def schirm(t, f, s_fn, ab, w_von, w_bis, breite, heben=0.0, material="platte", n=40, stufen=4):
	"""Schirm/Krempe auf einem Teil des Umfangs: waagrecht nach außen um breite(w), heben(w) biegt nach oben."""
	reihen = []
	for j in range(n + 1):
		w = w_von + (w_bis - w_von) * j / n
		s = g._wert(s_fn, w)
		p = f.punkt(s, w, g._wert(ab, s, w) if callable(ab) else ab)
		h = p - f.c
		h.z = 0
		h.normalize()
		b = g._wert(breite, w)
		zeile = []
		for i in range(stufen + 1):
			u = i / stufen
			q = p + h * b * u + Vector((0, 0, g._wert(heben, w) * u * u))
			zeile.append(t.vert(q))
		reihen.append(zeile)
	for j in range(n):
		for i in range(stufen):
			t.flaeche([reihen[j][i], reihen[j + 1][i], reihen[j + 1][i + 1], reihen[j][i + 1]], material)
	return [z[-1].co.copy() for z in reihen]


def diadem(t, f, A, s=1.18, spitze=0.035, material="borte"):
	"""Stirnreif mit Mittelspitze und Stein über der Stirn. A: Abstand (Zahl oder Funktion s, w)."""
	a = (lambda s_, w_: g._wert(A, s_, w_)) if callable(A) else (lambda s_, w_: A)
	pts, zu = g.rand_punkte(f, lambda w: s + 0.06 * (1 - math.cos(g.wdiff(w, 0) / 2)) ** 2 * 0, A, n=96)
	g.zug(t, pts, 0.0045, material, zu=zu, flach=0.5, aussen=nach_aussen(f))
	pts, zu = g.rand_punkte(f, s + 0.035, A, n=96)
	g.zug(t, pts, 0.0025, material, zu=zu, aussen=nach_aussen(f))
	# Spitze über der Stirn
	links = [f.punkt(s + 0.02 - spitze * u * 3, -0.25 * (1 - u), a(s, 0) + 0.001) for u in np.linspace(0, 1, 8)]
	rechts = [f.punkt(s + 0.02 - spitze * u * 3, 0.25 * (1 - u), a(s, 0) + 0.001) for u in np.linspace(0, 1, 8)]
	g.zug(t, links + list(reversed(rechts))[1:], 0.003, material, aussen=nach_aussen(f))
	g.niete(t, f.punkt(s - 0.02, 0.0, a(s, 0) + 0.002), f.normale(s - 0.02, 0.0, a(s, 0)), 0.009, "stoff_akzent")
	for sg in (1, -1):
		g.niete(t, f.punkt(s + 0.018, sg * 0.55, a(s, sg * 0.55) + 0.002), f.normale(s + 0.018, sg * 0.55, a(s, 0)), 0.005, material)


def rand_alle(r, f, s_fn, ab, radius=0.0045, material="rand", **kw):
	pts, zu = g.rand_punkte(f, s_fn, ab, **kw)
	g.zug(r, pts, radius, material, zu=zu)


# ================================================================ Helme


def helm_kamm(K, kamm_h=0.05, visier="balg", rondel=False, riffeln=0, A=0.024):
	"""Geschlossener Helm: Glocke mit Kamm, Visier (balg = Blasebalg-Rippen, rund = glatte Glocke mit Atemlöchern),
	Kinnreff und Halsreifen. Sehschlitz auf Augenhöhe."""
	f = ir.kopf_feld(K)
	rf = riffel(riffeln, 0.004, PI / 2, 2.0) if riffeln else (lambda s, w: 0.0)
	glocke = lambda s, w: A + rf(s, w) * g.weich(-s, -1.5, -0.4)
	spalt_o, spalt_u = AUGE_S - 0.045, AUGE_S + 0.045
	unten = lambda w: spalt_o + (2.4 - spalt_o) * g.weich(g.wdiff(w, 0), 1.15, 1.55)
	teile = [blech("glocke", f, 0.0, unten, glocke, d=0.003, nu=44, nw=96)]
	r = g.Teil("rand")
	ring(r, f, unten, glocke, 0.005, n=120)
	if visier == "balg":
		vis = lambda s, w: A + 0.01 + 0.03 * math.exp(-(g.wdiff(w, 0) / 0.6) ** 2) * math.exp(-((s - 1.95) / 0.3) ** 2) \
			+ 0.006 * max(0.0, math.sin((s - spalt_u) * 38)) ** 2 * g.weich(s, spalt_u + 0.05, spalt_u + 0.1)
	else:
		vis = lambda s, w: A + 0.012 + 0.022 * math.exp(-(g.wdiff(w, 0) / 0.8) ** 2) * math.exp(-((s - 1.98) / 0.35) ** 2)
	teile.append(blech("visier", f, spalt_u, 2.42, vis, d=0.003, nu=40, nw=48, w_von=-1.45, w_bis=1.45))
	for s in (spalt_u, 2.42):
		pts, _ = g.rand_punkte(f, s, vis, w_von=-1.45, w_bis=1.45, n=60)
		g.zug(r, pts, 0.0045, "rand")
	for sg in (1, -1):
		pts = [f.punkt(s, sg * 1.45, vis(s, sg * 1.45)) for s in np.linspace(spalt_u, 2.42, 24)]
		g.zug(r, pts, 0.004, "rand")
		g.niete(r, f.punkt(AUGE_S, sg * PI / 2, A + 0.012), f.normale(AUGE_S, sg * PI / 2, A + 0.012), 0.013, "rand")
	pts = [f.punkt(AUGE_S, w, A - 0.008) for w in np.linspace(-1.2, 1.2, 40)]
	g.zug(r, pts, 0.03, "stoff_dunkel", flach=0.12, aussen=nach_aussen(f))
	if visier == "rund":
		for sg in (1, -1):
			for i in range(3):
				for j in range(4):
					s, w = 1.95 + 0.06 * i, sg * (0.25 + 0.09 * j)
					g.niete(r, f.punkt(s, w, vis(s, w) + 0.0003), f.normale(s, w, vis(s, w)), 0.0038, "stoff_dunkel")
	# Kamm
	finne(r, f, glocke, -1.2, 2.0, lambda u: kamm_h * math.sin(u * PI) ** 0.55 + 0.004)
	# Halsreifen
	for k in range(3):
		s0 = 2.34 + 0.055 * k
		teile.append(blech("halsreif", f, s0, s0 + 0.075, A + 0.012 + 0.006 * k, d=0.0025, nu=4, nw=96))
		ring(r, f, s0, A + 0.012 + 0.006 * k, 0.003, n=96)
	if rondel:
		# Rondelle im Nacken auf kurzem Stiel
		p = f.punkt(2.05, PI, A + 0.004)
		n = f.normale(2.05, PI, A)
		g.zug(r, [p, p + n * 0.03], 0.005, "rand", seg=8)
		c = p + n * 0.032
		q = Vector((1, 0, 0))
		o = n.cross(q).normalized()
		scheibe = [c + (q * math.cos(a) + o * math.sin(a)) * 0.045 for a in np.linspace(0, 2 * PI, 33)[:-1]]
		g.zug(r, scheibe, 0.004, "rand", zu=True)
		mitte = r.vert(c)
		ring_v = [r.vert(c + (q * math.cos(a) + o * math.sin(a)) * 0.045) for a in np.linspace(0, 2 * PI, 33)[:-1]]
		for i in range(32):
			r.flaeche([ring_v[i], ring_v[(i + 1) % 32], mitte], "platte")
			r.flaeche([ring_v[(i + 1) % 32], ring_v[i], r.vert(c - n * 0.002)], "platte")
		g.niete(r, c + n * 0.002, n, 0.012, "rand")
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def burgonet(K, kamm_h=0.065, bart=True, A=0.024):
	"""Burgunderhelm: offene Glocke mit hohem Kamm, Stirnschirm, Wangenklappen, Nackenschirm, wahlweise Bart (Kinnplatte)."""
	f = ir.kopf_feld(K)
	glocke = lambda s, w: A
	stirn = AUGE_S - 0.17
	unten = lambda w: stirn + (2.3 - stirn) * g.weich(g.wdiff(w, 0), 0.5, 1.6)
	teile = [blech("glocke", f, 0.0, unten, glocke, d=0.003, nu=40, nw=96)]
	r = g.Teil("rand")
	ring(r, f, unten, glocke, 0.005, n=120)
	# Stirnschirm, leicht nach oben geschwungen
	sch = g.Teil("schirm")
	aussen = schirm(sch, f, lambda w: stirn + 0.01, A, -1.05, 1.05, lambda w: 0.055 * math.cos(w / 1.05 * PI / 2) ** 0.7 + 0.004,
		heben=lambda w: 0.018, n=40)
	teile.append(obj(sch, 40, 0.003))
	g.zug(r, aussen, 0.004, "rand")
	# Nackenschirm in drei Folgen
	for k in range(3):
		s0 = 2.18 + 0.07 * k
		teile.append(blech("nacken", f, s0, s0 + 0.09, A + 0.006 + 0.01 * k, d=0.0025, nu=5, nw=40, w_von=PI - 1.2,
			w_bis=PI + 1.2))
		pts, _ = g.rand_punkte(f, s0 + 0.09, A + 0.006 + 0.01 * k, w_von=PI - 1.2, w_bis=PI + 1.2, n=40)
		g.zug(r, pts, 0.003, "rand")
	# Wangenklappen
	for sg in (1, -1):
		wm = sg * 1.05
		kl = lambda w, wm=wm: 2.32 - 0.08 * (g.wdiff(w, wm) / 0.45) ** 2
		wange = lambda s, w: A + 0.004 + 0.006 * g.weich(s, 1.8, 2.2)
		teile.append(blech("wange", f, stirn + 0.08, kl, wange, d=0.003, nu=20, nw=20, w_von=wm - 0.45, w_bis=wm + 0.45))
		rand = [f.punkt(stirn + 0.08, wm - 0.45, wange(stirn + 0.08, wm - 0.45))]
		rand += [f.punkt(s, wm - 0.45, wange(s, wm - 0.45)) for s in np.linspace(stirn + 0.08, kl(wm - 0.45), 12)]
		rand += [f.punkt(kl(w), w, wange(kl(w), w)) for w in np.linspace(wm - 0.45, wm + 0.45, 16)]
		rand += [f.punkt(s, wm + 0.45, wange(s, wm + 0.45)) for s in np.linspace(kl(wm + 0.45), stirn + 0.08, 12)]
		g.zug(r, rand, 0.0035, "rand")
		g.niete(r, f.punkt(stirn + 0.12, wm, wange(stirn + 0.12, wm) + 0.001), f.normale(stirn + 0.12, wm, A), 0.008, "rand")
	if bart:
		# Kinnplatte (Bart) bis unter die Nase, oben gerollter Rand
		bo = lambda w: AUGE_S + 0.2 + 0.08 * (g.wdiff(w, 0) / 1.1) ** 2
		vor = lambda s, w: A + 0.016 + 0.01 * math.exp(-(g.wdiff(w, 0) / 0.6) ** 2)
		teile.append(blech("bart", f, bo, 2.45, vor, d=0.003, nu=18, nw=40, w_von=-1.1, w_bis=1.1))
		pts, _ = g.rand_punkte(f, bo, vor, w_von=-1.1, w_bis=1.1, n=40)
		g.zug(r, pts, 0.006, "rand")
		for k in range(2):
			teile.append(blech("halsreif", f, 2.4 + 0.05 * k, 2.48 + 0.05 * k, A + 0.03 + 0.006 * k, d=0.0025, nu=3,
				nw=48, w_von=-1.3, w_bis=1.3))
	finne(r, f, glocke, -1.25, 2.1, lambda u: kamm_h * math.sin(u * PI) ** 0.6 + 0.004)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def haube(K, material="leder", A=0.012, s_bis=2.2, extra=None, name="haube", d=0.004):
	"""Haube mit freiem Gesicht (wie die Kettenhaube): Schädel ganz, darunter nur Seiten, Nacken und Kinnriemen-Bereich."""
	f = ir.kopf_feld(K)
	t = g.Teil(name)
	g.platte(t, f, 0.0, 1.25, A, nu=20, nw=96, material_name=material, extra=extra)
	g.platte(t, f, 1.25, s_bis, A, nu=22, nw=60, w_von=0.95, w_bis=2 * PI - 0.95, material_name=material, extra=extra)
	return obj(t, 50, d), f


def kettenhaube(K, A=0.012, kragen=True):
	f = ir.kopf_feld(K)
	t = g.Teil("kettenhaube")
	g.platte(t, f, 0.0, 1.25, A, nu=24, nw=96, material_name="kette")
	g.platte(t, f, 1.25, 2.42, A, nu=26, nw=60, w_von=0.85, w_bis=2 * PI - 0.85, material_name="kette")
	g.platte(t, f, 2.08, 2.42, A, nu=8, nw=24, w_von=-0.87, w_bis=0.87, material_name="kette")
	teile = [obj(t, 60, 0.003)]
	if kragen:
		fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
		kt = g.Teil("kettenkragen")
		flare = lambda s, w: 0.02 * g.weich(-s, -0.66, -0.56)
		ku = tabelle([(0, 0.56), (0.9, 0.6), (PI / 2, 0.58), (2.3, 0.6), (PI, 0.57)])
		g.platte(kt, fr, ku, 0.78, 0.014, nu=16, nw=96, extra=flare, material_name="kette")
		teile.append(obj(kt, 60, 0.003))
	return teile, f


def morion(K, A=0.034, kamm_h=0.058, haube=True):
	"""Morion: hohe Glocke mit Kamm, Krempe vorne und hinten hochgeschwungen (Schiffsform)."""
	teile, f = kettenhaube(K) if haube else ([], ir.kopf_feld(K))
	s_r = 1.42
	ab = lambda s, w: A + 0.012 * g.weich(-s, -1.0, -0.2)
	teile.append(blech("glocke", f, 0.0, s_r, ab, d=0.003, nu=36, nw=96))
	r = g.Teil("rand")
	ws.krempe(r, f, s_r, ab, lambda w: 0.045 + 0.03 * abs(math.cos(w)) ** 2, "platte", neigung=0.05, n=96,
		hoch=lambda w: 0.075 * abs(math.cos(w)) ** 3, stufen=5)
	aussen = []
	for j in range(96):
		w = 2 * PI * j / 96
		p = f.punkt(s_r, w, ab(s_r, w))
		h = p - f.c
		h.z = 0
		h.normalize()
		b = 0.045 + 0.03 * abs(math.cos(w)) ** 2
		aussen.append(p + h * b + Vector((0, 0, -0.05 * b + 0.075 * abs(math.cos(w)) ** 3)))
	g.zug(r, aussen, 0.0045, "rand", zu=True)
	ring(r, f, s_r, ab, 0.004, n=96)
	finne(r, f, ab, -1.3, 1.3, lambda u: kamm_h * math.sin(u * PI) ** 0.7 + 0.004)
	for k in range(16):
		w = 2 * PI * k / 16
		g.niete(r, f.punkt(s_r - 0.04, w, ab(s_r - 0.04, w) + 0.001), f.normale(s_r - 0.04, w, A), 0.0045, "rand")
	teile.append(obj(r, 40, 0.0))
	return g.vereinen(teile, "x")


def cabasset(K, A=0.03, unter="leder"):
	"""Cabasset: mandelförmig hohe Glocke mit kleinem Stiel oben und schmaler, flacher Krempe."""
	f = ir.kopf_feld(K)
	teile = []
	if unter:
		k, _ = haube(K, unter, 0.012, 2.1, name="kappe", extra=lambda s, w: 0.004 * g.weich(s, 1.6, 2.0), d=0.004)
		teile.append(k)
	s_r = 1.38
	ab = lambda s, w: A + 0.06 * max(0.0, 1 - s / 0.95) ** 1.6
	teile.append(blech("glocke", f, 0.0, s_r, ab, d=0.003, nu=36, nw=96))
	r = g.Teil("rand")
	aussen = ws.krempe(r, f, s_r, ab, 0.035, "platte", neigung=0.08, n=96, stufen=3)
	g.zug(r, aussen, 0.004, "rand", zu=True)
	ring(r, f, s_r, ab, 0.004, n=96)
	top = f.punkt(0.0, 0.0, ab(0.0, 0.0))
	g.zug(r, [top - Vector((0, 0, 0.005)), top + Vector((0, 0.008, 0.028))], 0.0045, "rand", seg=8)
	for k in range(8):
		w = 2 * PI * k / 8
		pts = [f.punkt(s, w, ab(s, w) + 0.001) for s in np.linspace(0.12, s_r - 0.05, 16)]
		g.zug(r, pts, 0.0025, "rand", aussen=nach_aussen(f))
	teile.append(obj(r, 40, 0.0))
	return g.vereinen(teile, "x")


def eisenhut(K, A=0.032):
	"""Eisenhut: runde Glocke mit breiter, hängender Krempe, darunter Lederhaube."""
	f = ir.kopf_feld(K)
	k, _ = haube(K, "leder", 0.012, 2.25, name="haube", extra=lambda s, w: 0.006 * g.weich(s, 1.6, 2.2), d=0.004)
	teile = [k]
	s_r = 1.32
	ab = lambda s, w: A + 0.008 * math.exp(-(math.sin(w) * math.sin(s) / 0.05) ** 2) * g.weich(-s, -1.1, -0.2)
	teile.append(blech("glocke", f, 0.0, s_r, ab, d=0.003, nu=34, nw=96))
	r = g.Teil("rand")
	aussen = ws.krempe(r, f, s_r, ab, 0.075, "platte", neigung=0.35, n=96, stufen=5)
	g.zug(r, aussen, 0.005, "rand", zu=True)
	ring(r, f, s_r, ab, 0.004, n=96)
	for k in range(12):
		w = 2 * PI * k / 12
		g.niete(r, f.punkt(s_r - 0.05, w, ab(s_r - 0.05, w) + 0.001), f.normale(s_r - 0.05, w, A), 0.005, "rand")
	teile.append(obj(r, 40, 0.0))
	return g.vereinen(teile, "x")


def attisch(K, A=0.024):
	"""Attischer Helm: offenes Gesicht, Stirnband mit Spitze, große Wangenklappen, Nackenschwung, Rosshaarbusch."""
	f = ir.kopf_feld(K)
	stirn = AUGE_S - 0.16
	glocke = lambda s, w: A + 0.012 * g.weich(-s, -1.2, -0.3) + 0.014 * g.weich(s, 2.0, 2.35) * g.weich(g.wdiff(w, 0), 1.6, 2.4)
	unten = lambda w: stirn + (2.38 - stirn) * g.weich(g.wdiff(w, 0), 0.55, 1.7)
	teile = [blech("glocke", f, 0.0, unten, glocke, d=0.003, nu=40, nw=96)]
	r = g.Teil("rand")
	ring(r, f, unten, glocke, 0.005, n=120)
	# Stirnband (Stephane) mit Spitze
	sb = lambda w: stirn - 0.05 - 0.07 * math.exp(-(g.wdiff(w, 0) / 0.25) ** 2)
	teile.append(blech("stephane", f, sb, stirn + 0.005, lambda s, w: glocke(s, w) + 0.006, d=0.003, nu=8, nw=48,
		w_von=-1.5, w_bis=1.5))
	pts, _ = g.rand_punkte(f, sb, lambda s, w: glocke(s, w) + 0.006, w_von=-1.5, w_bis=1.5, n=48)
	g.zug(r, pts, 0.004, "rand")
	# Wangenklappen, vorne bis zum Kinn
	for sg in (1, -1):
		wm = sg * 0.95
		kl = lambda w, wm=wm: 2.42 - 0.1 * (g.wdiff(w, wm) / 0.55) ** 2
		wange = lambda s, w: A + 0.006 + 0.008 * g.weich(s, 1.9, 2.3)
		teile.append(blech("wange", f, stirn + 0.07, kl, wange, d=0.003, nu=22, nw=20, w_von=wm - 0.5, w_bis=wm + 0.5))
		rand = [f.punkt(s, wm - 0.5, wange(s, wm - 0.5)) for s in np.linspace(stirn + 0.07, kl(wm - 0.5), 12)]
		rand += [f.punkt(kl(w), w, wange(kl(w), w)) for w in np.linspace(wm - 0.5, wm + 0.5, 16)]
		rand += [f.punkt(s, wm + 0.5, wange(s, wm + 0.5)) for s in np.linspace(kl(wm + 0.5), stirn + 0.07, 12)]
		g.zug(r, rand, 0.0035, "rand")
		# Spirale auf der Wange
		c_s, c_w = 2.08, wm
		sp = [f.punkt(c_s + 0.11 * (1 - a / 9) * math.sin(a) * 0.5, c_w + 0.11 * (1 - a / 9) * math.cos(a) * 0.6,
			wange(c_s, c_w) + 0.001) for a in np.linspace(0, 8, 50)]
		g.zug(r, sp, 0.0025, "rand", aussen=nach_aussen(f))
	# Bügel und Busch
	pts = [p for _, _, _, p in kopf_pfad(f, lambda s, w: glocke(s, w) + 0.004, -0.9, 1.6, 30)]
	g.zug(r, pts, 0.008, "rand", flach=0.6, aussen=lambda p: Vector((1, 0, 0)))
	b = g.Teil("busch")
	busch(b, f, glocke, -0.95, 1.65, 0.08, "stoff_akzent")
	teile.append(obj(b, 60, 0.004))
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def kapuze_diadem(K, material, saum="stoff_akzent", diadem_an=True, **kw):
	teile, f, weit = ws.kapuze(K, material, saum=saum, **kw)
	if diadem_an:
		r = g.Teil("diadem")
		diadem(r, f, 0.009, 1.22)   # Reif auf der Stirn, unter der Kapuze
		teile.append(r.objekt())
	return teile, f, weit


# ================================================================ Schultern und Arme


def schulter(K, seite, A=0.034, gross=1.0, brechrand=0.045, lamellen=3, rf=0, bogen=0.0, material="platte"):
	"""Große Schulter mit Brechrand (hochstehender Kragenflügel), Lamellen über dem Oberarm, wahlweise geriffelt
	und mit gebogtem (wellig ausgeschnittenem) Rand."""
	f = ir.schulter_feld(K, seite)
	aussen = PI / 2 if seite > 0 else 3 * PI / 2
	innen = aussen + PI
	bis = lambda w: (0.78 + 0.62 * (1 - (g.wdiff(w, aussen) / PI) ** 2)) * gross + bogen * abs(math.sin(w * 4))
	rff = riffel(rf, 0.004, aussen, 1.2) if rf else (lambda s, w: 0.0)
	ab = lambda s, w: A + rff(s, w) * g.weich(s, 0.2, 0.5)
	teile = [blech("schulter", f, 0.0, bis, ab, d=0.003, nu=24, nw=96, material_name=material)]
	r = g.Teil("schulter_rand")
	pts, zu = g.rand_punkte(f, bis, lambda s, w: ab(s, w) + 0.002, n=144)
	g.zug(r, pts, 0.005, "rand", zu=zu)
	if brechrand > 0:
		# Brechrand: Flügel steht an der Halsseite der Schulter senkrecht hoch
		basis = [f.punkt(0.62, w, ab(0.62, w)) for w in np.linspace(innen - 1.15, innen + 1.15, 28)]
		hoch = [p + Vector((0, 0, 0.8 * brechrand * min(1.0, math.sin(u * PI) * 2.0) ** 0.8 + 0.004)) for p, u in zip(basis, np.linspace(0, 1, 28))]
		ft = g.Teil("brechrand")
		ub = [ft.vert(p - Vector((0, 0, 0.004))) for p in basis]
		ob = [ft.vert(p) for p in hoch]
		for i in range(27):
			ft.flaeche([ub[i], ub[i + 1], ob[i + 1], ob[i]], material)
		o = ft.objekt(30)
		g.dicke(o, 0.003, 0.0)
		teile.append(o)
		g.zug(r, hoch, 0.0035, "rand")
	fa = ir.oberarm_feld(K, seite)
	aussen_arm = 3 * PI / 2 if seite > 0 else PI / 2
	for k in range(lamellen):
		a0 = 0.075 * gross + 0.042 * k
		breite = 1.6 - 0.12 * k
		lab = 0.032 - 0.004 * k
		teile.append(blech("lamelle", fa, a0, a0 + 0.058, lab, d=0.0025, nu=6, nw=28, w_von=aussen_arm - breite,
			w_bis=aussen_arm + breite, material_name=material))
		pts, _ = g.rand_punkte(fa, a0 + 0.058, lab, w_von=aussen_arm - breite, w_bis=aussen_arm + breite, n=40)
		g.zug(r, pts, 0.003, "rand")
		g.nieten_reihe(r, fa, a0 + 0.02, lab, [aussen_arm - breite + 0.2, aussen_arm + breite - 0.2], 0.0045, "rand")
	g.nieten_reihe(r, f, lambda w: bis(w) - 0.07, A, [aussen - 1.0, aussen, aussen + 1.0], 0.006, "rand")
	teile.append(r.objekt())
	return teile


def oberarm(K, seite, rf=0):
	return ir._oberarm(K, seite)


def armroehre(K, seite, A=0.016, rf=6, glocke=0.02, bogen=0.012):
	"""Unterarmröhre mit Riffeln und gebogter Stulpe."""
	fa, l_ober, l_ges = ir.arm_feld(K, seite)
	von, bis = l_ober + 0.05, l_ges - 0.045
	aussen = 3 * PI / 2 if seite > 0 else PI / 2
	rff = riffel(rf, 0.003, aussen, 1.4) if rf else (lambda s, w: 0.0)
	teile = [blech("unterarm", fa, von, bis, lambda s, w: A + rff(s, w), nu=20, nw=64)]
	r = g.Teil("unterarm_rand")
	for s in (von, bis):
		ring(r, fa, s, lambda s, w: A + rff(s, w), n=64)
	gl = lambda s, w: glocke * g.weich(s, l_ges - 0.06, l_ges + 0.01)
	stb = lambda w: l_ges + 0.012 + bogen * abs(math.sin(w * 3))
	teile.append(blech("stulpe", fa, l_ges - 0.065, stb, A + 0.004, nu=10, nw=64, extra=gl))
	pts, zu = g.rand_punkte(fa, stb, A + 0.004, n=96, extra=gl)
	g.zug(r, pts, 0.0035, "rand", zu=zu)
	teile.append(r.objekt())
	return teile


def armschiene(K, seite, A=0.012, material="leder", platte=True):
	"""Armschiene aus Leder mit Goldplatte außen und Schnürung innen."""
	fa, l_ober, l_ges = ir.arm_feld(K, seite)
	von, bis = l_ober + 0.07, l_ges - 0.02
	teile = [blech("armschiene", fa, von, bis, A, d=0.004, nu=16, nw=48, material_name=material)]
	r = g.Teil("naht")
	for s in (von, bis):
		ring(r, fa, s, A, 0.0035, "leder_dunkel", flach=0.6, n=48)
	innen = PI / 2 if seite > 0 else 3 * PI / 2
	ws.schnuerung(r, fa, von + 0.02, bis - 0.04, A + 0.002, innen, 0.25, 6)
	if platte:
		aussen = PI / 2 if seite < 0 else 3 * PI / 2
		ex = lambda s, w: 0.004 * math.exp(-(g.wdiff(w, aussen) / 0.25) ** 2)
		teile.append(blech("armplatte", fa, von + 0.015, bis - 0.015, lambda s, w: A + 0.005 + ex(s, w), d=0.0025, nu=12,
			nw=16, w_von=aussen - 0.7, w_bis=aussen + 0.7))
		pts, _ = g.rand_punkte(fa, von + 0.015, A + 0.005, w_von=aussen - 0.7, w_bis=aussen + 0.7, n=16, extra=ex)
		g.zug(r, pts, 0.003, "rand")
		pts, _ = g.rand_punkte(fa, bis - 0.015, A + 0.005, w_von=aussen - 0.7, w_bis=aussen + 0.7, n=16, extra=ex)
		g.zug(r, pts, 0.003, "rand")
	teile.append(r.objekt())
	return teile


def panzerhand(K, seite, rf=6, knoechel=True, faust=False):
	"""Plattenhandschuh: dunkler Handschuh, geriffelte Röhre, geschuppter Handrücken, Knöchelbuckel."""
	teile = [ws.faeustling(K, seite, "leder_dunkel", 0.009, 0.09) if faust else ir.handschuh(K, seite, "leder_dunkel", 0.003, 0.09)]
	teile += armroehre(K, seite, rf=rf)
	hf, rw = ws.hand_feld(K, seite)
	r = g.Teil("hand_rand")
	for k in range(4):
		a0 = 0.0 + 0.026 * k
		ab = (0.016 if faust else 0.008) + 0.002 * k
		teile.append(blech("handplatte", hf, a0, a0 + 0.034, ab, d=0.002, nu=4, nw=16, w_von=rw - 1.2, w_bis=rw + 1.2))
		ring(r, hf, a0 + 0.034, ab, 0.0022, w_von=rw - 1.2, w_bis=rw + 1.2, n=16)
	if knoechel:
		s = hf.achse.laenge()
		for k in range(4):
			w = rw - 0.75 + 1.5 * k / 3
			ab = 0.024 if faust else 0.014
			g.niete(r, hf.punkt(s - 0.008, w, ab), hf.normale(s - 0.008, w, ab), 0.0065, "rand")
	teile.append(r.objekt())
	return teile


def stulpenhand(K, seite, material="leder", glocke=0.03, laenge=0.13, bogen=0.014, platte=False):
	"""Handschuh mit weiter, gebogt ausgeschnittener Stulpe."""
	teile = [ir.handschuh(K, seite, material, 0.0028, 0.05)]
	fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.8)
	gl = lambda s, w: glocke * g.weich(-s, -(l_ges - 0.02), -(l_ges - laenge))
	oben = lambda w: l_ges - laenge - 0.01 - bogen * abs(math.sin(w * 3))
	teile.append(blech("stulpe", fa, oben, l_ges - 0.015, lambda s, w: 0.009 + gl(s, w), d=0.003, nu=10, nw=72,
		material_name=material))
	r = g.Teil("naht")
	pts, zu = g.rand_punkte(fa, oben, lambda s, w: 0.009 + gl(s, w) + 0.001, n=96)
	g.zug(r, pts, 0.003, "rand", zu=zu, flach=0.6)
	if platte:
		hf, rw = ws.hand_feld(K, seite)
		teile.append(blech("handplatte", hf, 0.012, hf.achse.laenge() - 0.005, 0.008, d=0.002, nu=6, nw=14,
			w_von=rw - 1.0, w_bis=rw + 1.0))
	teile.append(r.objekt())
	return teile


# ================================================================ Rumpf


def harnisch(K, rf=0, fauld=3, schultern=dict(), unter=None, halsberge=True, nur_vorne=False, A=0.03):
	"""Harnisch aus iron.schwer_brust (Riffelung, Bauchreifen) mit Palladium-Schultern."""
	ob = ir.schwer_brust(K, riffel=rf, fauld=fauld, unter=unter, arme=False, halsberge=halsberge, name="h",
		nur_vorne=nur_vorne, A=A)
	teile = [ob]
	for seite in (1, -1):
		teile += schulter(K, seite, **schultern)
		teile += oberarm(K, seite)
	return teile


def gezackt(basis, tiefe, zacken, rund=False):
	"""Saumlinie mit Zacken (Dagging): basis + Zacken nach unten (s kleiner)."""
	if rund:
		return lambda w: basis - tiefe * abs(math.sin(w * zacken / 2)) ** 0.6
	return lambda w: basis - tiefe * (1 - abs(((w * zacken / (2 * PI)) % 1.0) * 2 - 1))


def wappenrock(K, unten, A=0.07, material="stoff_akzent", breite=0.95, oben_z=None, mitte_liste=(0.0, PI)):
	"""Wappenrock aus zwei Bahnen mit Saumlinie unten(w) (Funktion, s = z - ZW)."""
	f = ir.wams_feld(K)
	teile = []
	oben = tabelle([(0, 0.66), (0.5, 0.70), (0.95, 0.70), (2.2, 0.72), (PI, 0.73)])
	fl = lambda s, w: 0.02 * g.weich(-s, -(0.85 - ZW), -0.0) + 0.01 * g.weich(s, 1.18 - ZW, 1.4 - ZW)
	for mitte in mitte_liste:
		t = g.Teil("wappenrock")
		g.platte(t, f, unten, lambda w: oben(w) + 0.795 - ZW, lambda s, w: A + fl(s, w), nu=50, nw=60, w_von=mitte - breite,
			w_bis=mitte + breite, material_name=material)
		teile.append(obj(t, 60, 0.004))
	return teile, f, fl


def halskrause(K, z=1.53, A=0.02, breite=0.035, falten=28, material="futter"):
	"""Halskrause: gefältelter Ring um den Hals."""
	f = ir.wams_feld(K)
	t = g.Teil("krause")
	n = falten * 6
	ringe = []
	for j in range(n):
		w = 2 * PI * j / n
		welle = 0.012 * math.sin(w * falten)
		p = f.punkt(z - ZW, w, A)
		h = p - f.achse.punkt(z - ZW)
		h.z = 0
		h.normalize()
		zeile = []
		for i in range(5):
			u = i / 4
			zeile.append(t.vert(p + h * breite * u + Vector((0, 0, welle * u))))
		ringe.append(zeile)
	for j in range(n):
		k = (j + 1) % n
		for i in range(4):
			t.flaeche([ringe[j][i], ringe[k][i], ringe[k][i + 1], ringe[j][i + 1]], material)
	return obj(t, 60, 0.003)


def umhang(K, unten_z=0.55, w_offen=1.2, A=0.07, material="stoff_akzent", oben_z=None, einseitig=0, gezackt_tiefe=0.0):
	"""Umhang über Rücken und Schultern; einseitig = 1/-1 hängt nur über eine Schulter (halber Mantel)."""
	fw = ir.wams_feld(K)
	oben = tabelle([(0, 0.0), (1.2, 0.665), (PI / 2, 0.69), (PI, 0.68)])
	weite = lambda s, w: A + 0.05 * g.weich(-s, -(1.2 - ZW), -(unten_z - ZW))
	w0, w1 = w_offen, 2 * PI - w_offen
	if einseitig:
		# halber Mantel: von der Schulter (vorne) über den Rücken bis zur anderen Seite
		w0, w1 = (PI / 2 - 0.9, PI + 1.4) if einseitig > 0 else (PI - 1.4, 3 * PI / 2 + 0.9)
	saum = (lambda w: unten_z - ZW - gezackt_tiefe * abs(math.sin(w * 9)) ** 0.6) if gezackt_tiefe else unten_z - ZW
	t = g.Teil("umhang")
	g.platte(t, fw, saum, lambda w: oben(w) + 0.79 - ZW, weite, nu=56, nw=72, w_von=w0, w_bis=w1, material_name=material)
	return [obj(t, 60, 0.005)], fw, weite


def schaerpe(K, z=0.99, seite=-1, material="stoff_akzent"):
	"""Schärpe um die Hüfte mit Knoten und zwei hängenden Enden."""
	teile = ir.guertel(K, z, 0.065, 0.04, material, schnalle=False)
	s = g.Teil("schaerpe")
	fw = ir.wams_feld(K)
	w0 = 0.55 * seite
	p = fw.punkt(z - ZW, w0, 0.055)
	n = fw.normale(z - ZW, w0, 0.05)
	pts = [p + Vector((0.008 * k * seite, 0, -0.045 * k)) + n * (0.004 * k) for k in range(8)]
	blatt(s, pts, lambda u: 0.028, n, material)
	pts = [p + Vector((-0.02 * seite + 0.004 * k * seite, 0, -0.04 * k)) + n * (0.006 + 0.004 * k) for k in range(6)]
	blatt(s, pts, lambda u: 0.026, n, material)
	g.zug(s, [p + Vector((-0.02, 0, 0.018)), p + Vector((0.02, 0, -0.018))], 0.02, material, flach=0.5, aussen=lambda q: n)
	teile.append(obj(s, 60, 0.003))
	return teile


def brustplatte(K, A=0.032, unten_z=1.0, gans=0.02, rf=0):
	"""Bruststück vorne mit Gänsebauch (Spitze unten vorne) und Riemen."""
	f = ir.rumpf_feld(K)
	oben = tabelle([(0, 0.64), (0.4, 0.69), (0.8, 0.66), (1.3, 0.55), (1.75, 0.5)])
	uz = unten_z - Z0
	unten = tabelle([(0, uz - 0.05), (0.5, uz), (1.75, uz + 0.03)])
	rff = riffel(rf, 0.004, 0.0, 1.0) if rf else (lambda s, w: 0.0)
	form = lambda s, w: 0.012 * math.exp(-(g.wdiff(w, 0) / 0.22) ** 2) * g.weich(s, 0.2, 0.45) \
		+ gans * math.exp(-(g.wdiff(w, 0) / 0.6) ** 2) * math.exp(-((s - uz - 0.06) / 0.1) ** 2) + rff(s, w) * g.weich(s, uz, uz + 0.12)
	teile = [blech("brustplatte", f, unten, oben, lambda s, w: A + form(s, w), d=0.003, nu=36, nw=56, w_von=-1.75, w_bis=1.75)]
	r = g.Teil("brustplatte_rand")
	for fn in (oben, unten):
		pts, _ = g.rand_punkte(f, fn, lambda s, w: A + form(s, w) + 0.001, w_von=-1.75, w_bis=1.75, n=80)
		g.zug(r, pts, 0.0045, "rand")
	for z in (0.30, 0.52):
		pts, _ = g.rand_punkte(f, z, A - 0.012, w_von=1.65, w_bis=2 * PI - 1.65, n=40)
		g.zug(r, pts, 0.011, "leder_dunkel", flach=0.3)
	teile.append(r.objekt())
	return teile, f


def tassetten(K, z_oben=0.97, laenge=0.22, A=0.075, folgen=3, w_liste=(0.75, -0.75), breite=0.55, material="platte"):
	"""Beintaschen: Folgen aus Blech an der Hüfte."""
	fw = ir.wams_feld(K)
	teile = []
	r = g.Teil("tassetten_rand")
	for w0 in w_liste:
		for k in range(folgen):
			a = z_oben - ZW - laenge * (k + 1) / folgen
			b = z_oben - ZW - laenge * k / folgen + 0.012
			ab = lambda s, w, k=k: A + 0.004 * k + 0.02 * g.weich(-s, -(z_oben - ZW), -(z_oben - laenge - ZW))
			teile.append(blech("tassette", fw, a, b, ab, d=0.003, nu=5, nw=16, w_von=w0 - breite, w_bis=w0 + breite,
				material_name=material))
			pts, _ = g.rand_punkte(fw, a, ab, w_von=w0 - breite, w_bis=w0 + breite, n=16)
			g.zug(r, pts, 0.0035, "rand")
	teile.append(r.objekt())
	return teile


def pteruges(K, z_oben=0.98, laenge=0.24, A=0.05, n=20, material="leder"):
	"""Lederstreifen-Rock (zwei versetzte Lagen) mit Goldspitzen."""
	fw = ir.wams_feld(K)
	teile = []
	r = g.Teil("spitzen")
	for lage in range(2):
		for k in range(n):
			w0 = 2 * PI * (k + 0.5 * lage) / n
			b = PI / n * 0.85
			a = z_oben - ZW - laenge + 0.05 * lage
			ab = lambda s, w, lage=lage: A + 0.008 * (1 - lage) + 0.025 * g.weich(-s, -(z_oben - ZW), -a)
			teile.append(blech("streifen", fw, a, z_oben - ZW + 0.01, ab, d=0.004, nu=6, nw=3, w_von=w0 - b, w_bis=w0 + b,
				material_name=material))
			pts, _ = g.rand_punkte(fw, a + 0.004, lambda s, w, ab=ab: ab(s, w) + 0.003, w_von=w0 - b, w_bis=w0 + b, n=4)
			g.zug(r, pts, 0.004, "rand", flach=0.6)
	teile.append(r.objekt())
	return teile


def muskelpanzer(K, A=0.02):
	"""Muskelpanzer: folgt der Brust- und Bauchform (wenig geglättet)."""
	f = ir.rumpf_feld(K, glatt=(2, 1), konvex=0.35)
	oben = tabelle([(0, 0.665), (0.4, 0.70), (0.75, 0.66), (1.15, 0.52), (1.57, 0.49), (2.0, 0.52),
		(2.4, 0.70), (2.8, 0.72), (PI, 0.71)])
	unten = tabelle([(0, 0.14), (0.6, 0.16), (PI / 2, 0.19), (PI, 0.18)])
	teile = [blech("muskelpanzer", f, unten, oben, A, d=0.003, nu=56, nw=96)]
	r = g.Teil("rand")
	for fn in (oben, unten):
		pts, zu = g.rand_punkte(f, fn, A + 0.002, n=144)
		g.zug(r, pts, 0.005, "rand", zu=zu)
	teile.append(r.objekt())
	return teile, f


def robe(K, material, A=0.02, weite=0.07, unten_z=0.10, manschette=0.035, aermel_puff=0.0, offen=0.0):
	teile, f = ir.wams(K, material, A, unten_z=unten_z, kragen_z=1.54, aermel_bis=1.0, weite=weite, z0=0.08,
		aermel_abstand=0.01, manschette=manschette, rock_ab=0.95, puff=aermel_puff, offen=offen)
	return teile, f


def stehkragen(K, hoehe=0.09, A=0.022, material="stoff_akzent", offen=0.35, aus=0.025):
	"""Hoher, nach außen geschwungener Kragen (vorne offen)."""
	fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	s0 = 0.69
	t = g.Teil("stehkragen")
	g.platte(t, fr, lambda w: s0 + 0.03 * math.cos(g.wdiff(w, PI) / 2) ** 2 * 0, lambda w: s0 + hoehe, lambda s, w: A + aus * g.weich(s, s0 + 0.02, s0 + hoehe),
		nu=10, nw=72, w_von=offen, w_bis=2 * PI - offen, material_name=material)
	return obj(t, 60, 0.004)


def kragen_lagen(K, lagen=2, unten_liste=(0.50, 0.58), A=0.03, material="stoff_akzent", gezackt_tiefe=0.0):
	"""Schulterkragen (Pelerine) in Lagen, unterste zuerst."""
	fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	teile = []
	for k in range(lagen):
		u0 = unten_liste[k]
		# vorne und hinten länger als über den Schultern (fällt rund über die Brust)
		ku = lambda w, u0=u0: u0 - 0.06 * math.cos(w) ** 2 - gezackt_tiefe * abs(math.sin(w * 7)) ** 0.6
		flare = lambda s, w, u0=u0, k=k: A + 0.01 * k + 0.02 * g.weich(-s, -(u0 + 0.15), -(u0 - 0.06))
		t = g.Teil("pelerine")
		g.platte(t, fr, ku, 0.79, flare, nu=24, nw=96, material_name=material)
		teile.append(obj(t, 60, 0.004))
	return teile


def stola(K, material="stoff_akzent", unten_z=0.35, breite=0.05, w0=0.32):
	"""Stola: zwei Bänder vom Nacken über die Brust nach unten."""
	fw = ir.wams_feld(K, 0.30)
	t = g.Teil("stola")
	for sg in (1, -1):
		pts = []
		for u in np.linspace(0, 1, 40):
			z = 1.52 - (1.52 - unten_z) * u
			w = sg * (w0 + 0.25 * max(0.0, 1 - u * 4))
			pts.append(fw.punkt(z - ZW, w, 0.11 + 0.04 * g.weich(-z, -1.0, -0.4)))
		blatt(t, pts, lambda u: breite / 2, lambda p: (p - fw.achse.punkt(p.z - ZW)).normalized(), material)
	return obj(t, 60, 0.003)


# ================================================================ Beine und Füße


def beinzeug(K, hose_material="stoff", rf=0, fluegel=0.03, A=0.016):
	"""Beinzeug: Diechlinge (geriffelt), Kniekachel mit muschelförmigem Seitenflügel, Beinröhre mit Grat."""
	teile = ir.hose(K, hose_material, 0.006)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("bein_rand")
		rff = riffel(rf, 0.003, 0.0, 1.3) if rf else (lambda s, w: 0.0)
		ab = lambda s, w: A + rff(s, w)
		teile.append(blech("diechling", fb, 0.15, l_knie - 0.06, ab, d=0.003, nu=24, nw=48, w_von=-2.0, w_bis=2.0))
		pts, _ = g.rand_punkte(fb, 0.15, ab, w_von=-2.0, w_bis=2.0, n=48)
		g.zug(r, pts, 0.0045, "rand")
		for k in range(2):
			a0 = 0.09 + 0.035 * k
			teile.append(blech("lamelle", fb, a0, a0 + 0.05, A + 0.004 - 0.003 * k, d=0.0025, nu=4, nw=30, w_von=-1.7,
				w_bis=1.7))
			pts, _ = g.rand_punkte(fb, a0, A + 0.004 - 0.003 * k, w_von=-1.7, w_bis=1.7, n=30)
			g.zug(r, pts, 0.003, "rand")
		buckel = lambda s, w: 0.022 * math.exp(-((s - l_knie) / 0.04) ** 2) * math.cos(min(g.wdiff(w, 0), PI / 2)) ** 2
		teile.append(blech("knie", fb, l_knie - 0.075, l_knie + 0.07, lambda s, w: A + 0.006 + buckel(s, w), d=0.003, nu=16,
			nw=36, w_von=-1.9, w_bis=1.9))
		for s in (l_knie - 0.075, l_knie + 0.07):
			pts, _ = g.rand_punkte(fb, s, lambda s_, w: A + 0.006 + buckel(s_, w), w_von=-1.9, w_bis=1.9, n=36)
			g.zug(r, pts, 0.004, "rand")
		# Muschelflügel außen am Knie
		if fluegel > 0:
			aw = PI / 2 if seite > 0 else 3 * PI / 2
			ft = g.Teil("fluegel")
			c = fb.punkt(l_knie, aw, A + 0.012)
			nrm = fb.normale(l_knie, aw, A + 0.012)
			ax = (fb.punkt(l_knie + 0.02, aw, A) - fb.punkt(l_knie - 0.02, aw, A)).normalized()
			q = nrm.cross(ax).normalized()
			rand_v, mitte = [], ft.vert(c + nrm * 0.006)
			for a in np.linspace(0, 2 * PI, 37)[:-1]:
				rr = fluegel * (1 + 0.18 * math.cos(a * 6))
				rand_v.append(ft.vert(c + (ax * math.cos(a) + q * math.sin(a)) * rr + nrm * (-0.004 + 0.002 * math.cos(a * 6))))
			for i in range(36):
				ft.flaeche([rand_v[i], rand_v[(i + 1) % 36], mitte], "platte")
			o = ft.objekt(30)
			g.dicke(o, 0.0025, -1.0)
			teile.append(o)
			g.niete(r, c + nrm * 0.006, nrm, 0.009, "rand")
		grat = lambda s, w: 0.006 * math.exp(-(g.wdiff(w, 0) / 0.25) ** 2)
		teile.append(blech("schiene", fb, l_knie + 0.055, l_ges - 0.07, lambda s, w: A - 0.002 + grat(s, w), d=0.003, nu=36,
			nw=56))
		for s in (l_knie + 0.055, l_ges - 0.07):
			ring(r, fb, s, lambda s_, w: A - 0.002 + grat(s_, w), 0.004, n=64)
		teile.append(r.objekt())
	return teile


def baerentatzen(K, schaft=0.12, breit=0.016):
	"""Eisenschuhe mit breiter, abgerundet-eckiger Kappe (Bärentatze)."""
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.009, schaft))
		ff = ir.fuss_feld(K, seite)
		L = ff.achse.laenge()
		r = g.Teil("schuh_rand")
		for k in range(5):
			a0 = 0.04 + (L - 0.1) * k / 5
			a1 = a0 + (L - 0.1) / 5 + 0.008
			ab = 0.014 + 0.0015 * k
			teile.append(blech("sabaton", ff, a0, a1, ab, d=0.0025, nu=4, nw=24, w_von=-1.45, w_bis=1.45))
			pts, _ = g.rand_punkte(ff, a0, ab, w_von=-1.45, w_bis=1.45, n=24)
			g.zug(r, pts, 0.0025, "rand")
		a0 = 0.04 + (L - 0.1)
		breite_fn = lambda s, w: breit * g.weich(s, a0, L - 0.01) * abs(math.sin(w)) ** 0.8
		teile.append(blech("tatze", ff, a0 - 0.002, L + 0.004, lambda s, w: 0.016 + breite_fn(s, w), d=0.0025, nu=12, nw=32,
			w_von=-1.8, w_bis=1.8))
		pts, _ = g.rand_punkte(ff, a0 - 0.002, lambda s, w: 0.016 + breite_fn(s, w), w_von=-1.8, w_bis=1.8, n=32)
		g.zug(r, pts, 0.003, "rand")
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		teile.append(blech("knoechel", fb, l_ges - 0.10, l_ges - 0.045, 0.011, d=0.0025, nu=6, nw=56))
		ring(r, fb, l_ges - 0.10, 0.011, 0.003, n=56)
		teile.append(r.objekt())
	return teile


def stiefel_pal(K, seite, material="leder", schaft=0.30, weite=0.0, umschlag=0.0, kappe=False, abstand=0.009,
		bogen=0.0):
	"""Stiefel mit optionalem Umschlag (gebogt), Goldkappe."""
	teile = [ir.stiefel(K, seite, material, abstand, schaft, weite=weite)]
	if umschlag > 0:
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		s_oben = l_ges - schaft - 0.03
		un = lambda w: s_oben + umschlag + bogen * abs(math.sin(w * 3))
		ab = lambda s, w: abstand + 0.016 + weite + 0.01 * g.weich(-s, -(s_oben + umschlag), -s_oben)
		teile.append(blech("umschlag", fb, s_oben + 0.004, un, ab, d=0.004, nu=6, nw=72, material_name=material))
	if kappe:
		ff = ir.fuss_feld(K, seite)
		L = ff.achse.laenge()
		teile.append(blech("kappe", ff, L - 0.065, L, 0.016, d=0.0025, nu=8, nw=24, w_von=-1.6, w_bis=1.6))
	return teile


# ================================================================ SCHWER


def schwer_kopf(K):
	return helm_kamm(K, kamm_h=0.024, visier="balg", riffeln=9)


def schwer_brust(K):
	return g.vereinen(harnisch(K, rf=9, fauld=4, schultern=dict(rf=7, brechrand=0.05, bogen=0.0)), "x")


def schwer_haende(K):
	teile = []
	for seite in (1, -1):
		teile += panzerhand(K, seite, rf=6)
	return g.vereinen(teile, "x")


def schwer_beine(K):
	return g.vereinen(beinzeug(K, "stoff", rf=6, fluegel=0.034), "x")


def schwer_fuesse(K):
	return g.vereinen(baerentatzen(K), "x")


# ---------------- Schwert und Schild: Burgunderhelm mit Bart, gezackter Wappenrock


def sus_kopf(K):
	return burgonet(K, 0.05, bart=True)


def sus_brust(K):
	teile = harnisch(K, rf=0, fauld=3, schultern=dict(brechrand=0.045, bogen=0.05, gross=1.05))
	wr, f, fl = wappenrock(K, gezackt(0.56 - ZW, 0.05, 14), A=0.072)
	teile += wr
	# Wappen: Schild mit Sonne
	r = g.Teil("wappen")
	A = 0.072
	for s0, w0 in ((1.22 - ZW, 0.0),):
		umriss = []
		for a in np.linspace(0, 1, 40):
			if a < 0.5:
				w = -0.32 + 0.64 * a * 2
				s = s0 + 0.11
			else:
				u = (a - 0.5) * 2
				w = 0.32 * math.cos(u * PI)
				s = s0 + 0.11 - 0.24 * math.sin(u * PI / 2) ** 1.6
			umriss.append(f.punkt(s, w, A + fl(s, w) + 0.006))
		g.zug(r, umriss, 0.005, "rand", zu=True)
		c = f.punkt(s0 + 0.01, 0.0, A + fl(s0, 0.0) + 0.007)
		g.niete(r, c, f.normale(s0, 0.0, A), 0.022, "rand")
		for k in range(12):
			a = 2 * PI * k / 12
			d = Vector((math.cos(a) * 0.4, 0, math.sin(a)))
			g.zug(r, [c + d * 0.03, c + d * 0.055], 0.0035, "rand")
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.97, 0.05, 0.085)
	return g.vereinen(teile, "x")


def sus_haende(K):
	teile = []
	for seite in (1, -1):
		teile += panzerhand(K, seite, rf=0)
	return g.vereinen(teile, "x")


def sus_beine(K):
	teile = beinzeug(K, "stoff", rf=0, fluegel=0.03)
	f = ir.wams_feld(K)
	t = g.Teil("kettenschurz")
	g.platte(t, f, gezackt(0.70 - ZW, 0.03, 24), 0.92 - ZW, lambda s, w: 0.022 + 0.03 * g.weich(-s, -(0.86 - ZW), -(0.70 - ZW)),
		nu=20, nw=96, material_name="kette")
	teile.append(obj(t, 60, 0.003))
	return g.vereinen(teile, "x")


def sus_fuesse(K):
	return g.vereinen(baerentatzen(K, breit=0.012), "x")


# ---------------- Hammer: Rennhelm mit Rondelle, stark geriffelt, runde Großschultern


def hammer_kopf(K):
	return helm_kamm(K, kamm_h=0.016, visier="rund", rondel=True, riffeln=12)


def hammer_brust(K):
	teile = harnisch(K, rf=13, fauld=4, unter=dict(material="kette", unten_z=0.62, weite=0.06, abstand=0.012,
		aermel_bis=0.55, aermel_abstand=0.01, steppung=0.0), schultern=dict(gross=1.18, A=0.04, rf=10, brechrand=0.06,
		lamellen=4))
	return g.vereinen(teile, "x")


def hammer_haende(K):
	teile = []
	for seite in (1, -1):
		teile += panzerhand(K, seite, rf=8, faust=True)
	return g.vereinen(teile, "x")


def hammer_beine(K):
	teile = beinzeug(K, "leder_dunkel", rf=8, fluegel=0.04)
	f = ir.wams_feld(K)
	t = g.Teil("kettenschurz")
	g.platte(t, f, 0.66 - ZW, 0.92 - ZW, lambda s, w: 0.024 + 0.035 * g.weich(-s, -(0.86 - ZW), -(0.66 - ZW)), nu=20, nw=96,
		material_name="kette")
	teile.append(obj(t, 60, 0.003))
	return g.vereinen(teile, "x")


def hammer_fuesse(K):
	teile = baerentatzen(K, breit=0.02)
	for seite in (1, -1):
		teile += ws.schienbein(K, seite, 0.022, 1.1, hoch=0.24)
	return g.vereinen(teile, "x")


# ---------------- Axt: Widderhelm, Fellmantel mit Goldspangen, geflanschte Schultern (M/S/M/S/M)


def axe_kopf(K):
	"""Offener Helm mit gewundenen Widderhörnern, Nasal und Kettenbehang."""
	f = ir.kopf_feld(K)
	A = 0.026
	ab = lambda s, w: A + 0.012 * g.weich(-s, -1.0, -0.2) + 0.006 * math.exp(-(math.sin(w) * math.sin(s) / 0.04) ** 2)
	unten = 1.52
	teile = [blech("kappe", f, 0.0, unten, ab, d=0.003, nu=34, nw=96)]
	r = g.Teil("rand")
	ring(r, f, unten, ab, 0.008, n=96, flach=0.5)
	nas = [f.punkt(s, 0.0, A + 0.008 + 0.02 * g.weich(s, 1.6, 1.95)) for s in np.linspace(unten - 0.04, 1.98, 16)]
	g.zug(r, nas, 0.014, "platte", flach=0.25, aussen=nach_aussen(f))
	# Augenbrauen-Bögen über dem Rand
	for sg in (1, -1):
		pts = [f.punkt(unten - 0.03 + 0.02 * math.sin(a), sg * (0.1 + a * 0.45), ab(unten, 0) + 0.004) for a in np.linspace(0, PI, 20)]
		g.zug(r, pts, 0.005, "rand", aussen=nach_aussen(f))
		# Widderhorn: Spirale seitlich am Helm
		c = f.punkt(1.15, sg * PI / 2, A + 0.02)
		n = f.normale(1.15, sg * PI / 2, A)
		v = Vector((0, -1, 0))
		u = n.cross(v).normalized()
		pts, radien = [], []
		for a in np.linspace(0, 1.75 * 2 * PI, 70):
			rr = 0.055 * (1 - a / (4.4 * PI))
			pts.append(c + (v * math.cos(a) * rr + u * math.sin(a) * rr) + n * (0.012 + a * 0.004))
		for i in range(len(pts) - 1):
			g.zug(r, [pts[i], pts[i + 1]], 0.016 * (1 - i / 80), "platte", seg=10)
		for i in range(0, len(pts), 5):
			g.niete(r, pts[i], n, 0.004, "rand")
	kt = g.Teil("behang")
	g.platte(kt, f, unten + 0.01, 2.48, lambda s, w: 0.018 + 0.025 * g.weich(s, 1.9, 2.45), nu=26, nw=60,
		w_von=1.15, w_bis=2 * PI - 1.15, material_name="kette")
	teile.append(obj(kt, 60, 0.003))
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def axe_brust(K):
	teile = harnisch(K, rf=5, fauld=2, unter=dict(material="kette", unten_z=0.64, weite=0.05, abstand=0.012,
		aermel_bis=0.8, aermel_abstand=0.009), halsberge=False, schultern=dict(gross=1.1, A=0.045, brechrand=0.0, bogen=0.07,
		rf=4))
	# Fellmantel über Rücken und Schultern, vorne mit zwei Goldspangen
	fw = ir.wams_feld(K)
	oben = tabelle([(0, 0.0), (1.3, 0.66), (PI / 2, 0.69), (PI, 0.68)])
	fell = lambda s, w: 0.095 + 0.04 * g.weich(-s, -(1.2 - ZW), -(0.7 - ZW)) + 0.003 * math.sin(w * 17 + s * 41 + math.sin(w * 7) * 3)
	t = g.Teil("umhang")
	g.platte(t, fw, lambda w: 0.58 - ZW + 0.04 * math.sin(w * 5), lambda w: oben(w) + 0.795 - ZW, fell, nu=50, nw=60,
		w_von=1.3, w_bis=2 * PI - 1.3, material_name="fell")
	teile.append(obj(t, 60, 0.008))
	r = g.Teil("spangen")
	pts, zu = g.rand_punkte(fw, lambda w: 1.47 - ZW, lambda s, w: 0.095, n=60, w_von=1.2, w_bis=2 * PI - 1.2)
	ws.pelzrand(r, pts, False, 0.036)
	fr = ir.rumpf_feld(K)
	for sg in (1, -1):
		p = fr.punkt(0.6, sg * 0.75, 0.05)
		g.niete(r, p, fr.normale(0.6, sg * 0.75, 0.05), 0.02, "rand")
	pts = [fr.punkt(0.6 + 0.04 * math.sin(u * PI), u * 0.75, 0.052) for u in np.linspace(-1, 1, 24)]
	g.zug(r, pts, 0.004, "rand")
	teile.append(r.objekt())
	teile += tassetten(K, 0.96, 0.24, 0.075, 3, (0.85, -0.85), 0.5)
	teile += ir.guertel(K, 0.97, 0.07, 0.07, "leder")
	return g.vereinen(teile, "x")


def axe_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder", 0.003, 0.05))
		teile += armroehre(K, seite, 0.014, rf=4, glocke=0.026, bogen=0.016)
	return g.vereinen(teile, "x")


def axe_beine(K):
	return g.vereinen(beinzeug(K, "leder_dunkel", rf=4, fluegel=0.036), "x")


def axe_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.26, kappe=True)
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("fell")
		pts, zu = g.rand_punkte(fb, l_ges - 0.29, 0.02, n=48)
		ws.pelzrand(r, pts, zu, 0.018)
		ring(r, fb, l_ges - 0.14, 0.014, 0.006, "rand", flach=0.4, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Leerenmagie: Kapuze mit Vollmaske, langer offener Mantel mit Stehkragen (M/S/M/S/M)


def void_kopf(K):
	teile, f, weit = kapuze_diadem(K, "stoff_dunkel", saum="rand", diadem_an=False, A=0.03, gesicht=0.85, tief=0.04,
		kragen_unten=tabelle([(0, 0.52), (0.9, 0.55), (PI / 2, 0.55), (PI, 0.48)]))
	A = 0.016
	nase = lambda s, w: 0.012 * math.exp(-(g.wdiff(w, 0) / 0.18) ** 2) * g.weich(s, 1.5, 1.75) * g.weich(-s, -2.0, -1.85)
	stirn = lambda s, w: 0.006 * math.exp(-((s - 1.45) / 0.06) ** 2)
	maske = lambda s, w: A + nase(s, w) + stirn(s, w) + 0.006 * g.weich(s, 1.9, 2.2)
	oben = lambda w: 1.30 + 0.06 * (g.wdiff(w, 0) / 1.0) ** 2
	teile.append(blech("maske", f, oben, 2.30, maske, d=0.0025, nu=36, nw=48, w_von=-1.0, w_bis=1.0))
	r = g.Teil("rand")
	pts, _ = g.rand_punkte(f, oben, maske, w_von=-1.0, w_bis=1.0, n=48)
	g.zug(r, pts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, 2.30, maske, w_von=-1.0, w_bis=1.0, n=48)
	g.zug(r, pts, 0.004, "rand")
	for sg in (1, -1):
		pts = [f.punkt(s, sg * 1.0, maske(s, sg * 1.0)) for s in np.linspace(oben(1.0), 2.3, 20)]
		g.zug(r, pts, 0.004, "rand")
		# Augenschlitz, mandelförmig, mit Goldlid
		auge = [f.punkt(AUGE_S + 0.018 * math.sin(a), sg * (0.36 + 0.17 * math.cos(a)), maske(AUGE_S, sg * 0.36) + 0.0005)
			for a in np.linspace(0, 2 * PI, 30)[:-1]]
		g.zug(r, auge, 0.0035, "rand", zu=True, aussen=nach_aussen(f))
		pts = [f.punkt(AUGE_S, sg * w, maske(AUGE_S, sg * w) - 0.0005) for w in np.linspace(0.22, 0.5, 12)]
		g.zug(r, pts, 0.012, "stoff_dunkel", flach=0.15, aussen=nach_aussen(f))
		# Ranken auf der Wange
		sp = [f.punkt(2.05 + 0.07 * (1 - a / 8) * math.sin(a), sg * (0.55 + 0.1 * (1 - a / 8) * math.cos(a)),
			maske(2.05, sg * 0.55) + 0.001) for a in np.linspace(0, 7, 40)]
		g.zug(r, sp, 0.0022, "rand", aussen=nach_aussen(f))
	pts = [f.punkt(2.08, w, maske(2.08, w) + 0.0005) for w in np.linspace(-0.22, 0.22, 12)]
	g.zug(r, pts, 0.004, "stoff_dunkel", flach=0.4, aussen=nach_aussen(f))
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def void_brust(K):
	teile = harnisch(K, rf=0, fauld=2, unter=dict(material="stoff_dunkel", unten_z=0.86, aermel_bis=1.0, steppung=0.0),
		schultern=dict(brechrand=0.04, bogen=0.04))
	f = ir.wams_feld(K, 0.30)
	t = g.Teil("mantel")
	flare = lambda s, w: 0.08 + 0.07 * g.weich(-s - ZW, -0.95, -0.35)
	g.platte(t, f, lambda w: 0.32 - ZW + 0.08 * math.cos(g.wdiff(w, PI) / 2) ** 2 * 0, 1.0 - ZW, flare, nu=56, nw=72,
		w_von=0.55, w_bis=2 * PI - 0.55, material_name="stoff_dunkel")
	teile.append(obj(t, 60, 0.004))
	teile.append(stehkragen(K, 0.1, 0.03, "stoff_dunkel", 0.45, 0.03))
	teile += ir.guertel(K, 0.97, 0.05, 0.085)
	return g.vereinen(teile, "x")


def void_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder_dunkel", 0.03, 0.12, 0.016, platte=True)
	return g.vereinen(teile, "x")


def void_beine(K):
	return g.vereinen(beinzeug(K, "stoff_dunkel", rf=0, fluegel=0.028), "x")


def void_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder_dunkel", 0.34, weite=0.012, umschlag=0.06, bogen=0.02, kappe=True)
	return g.vereinen(teile, "x")


# ================================================================ MITTEL


def mittel_kopf(K):
	return morion(K)


def mittel_brust(K):
	teile = []
	unter, _ = ir.wams(K, "stoff", 0.006, unten_z=0.70, kragen_z=1.52, aermel_bis=1.0, steppung=0.003, weite=0.035,
		aermel_abstand=0.004)
	teile += unter
	kette, _ = ir.wams(K, "kette", 0.014, unten_z=0.62, kragen_z=1.49, aermel_bis=0.52, weite=0.06, name="kettenhemd",
		aermel_abstand=0.011)
	teile += kette
	b, f = brustplatte(K, 0.034, 1.0, 0.025, rf=6)
	teile += b
	for seite in (1, -1):
		teile += schulter(K, seite, A=0.03, gross=0.9, brechrand=0.0, lamellen=2, bogen=0.05)
	teile += schaerpe(K, 0.99, -1)
	return g.vereinen(teile, "x")


def mittel_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.026, 0.11, 0.012)
		teile += armschiene(K, seite, 0.013, platte=True)
	return g.vereinen(teile, "x")


def mittel_beine(K):
	teile = ir.hose(K, "leder_dunkel", 0.006)
	for seite in (1, -1):
		teile += ws.kniekachel(K, seite, 0.016, 1.5)
	teile += tassetten(K, 0.97, 0.2, 0.05, 2, (0.8, -0.8), 0.55)
	return g.vereinen(teile, "x")


def mittel_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.32, weite=0.01, umschlag=0.05, bogen=0.018, kappe=True)
	return g.vereinen(teile, "x")


# ---------------- Großschwert: Landsknecht mit Brigantine, Cabasset und Puffärmeln (MMMMM)


def greatsword_kopf(K):
	return cabasset(K, 0.03, "stoff_akzent")


def greatsword_brust(K):
	teile, f = ir.wams(K, "stoff_akzent", 0.006, unten_z=0.62, kragen_z=1.52, aermel_bis=1.0, weite=0.05,
		aermel_abstand=0.008, puff=0.03, manschette=0.012)
	# Schlitze auf den Puffärmeln (helles Futter scheint durch)
	r = g.Teil("schlitze")
	for seite in (1, -1):
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
		for k in range(8):
			w = 2 * PI * k / 8
			pts = [fa.punkt(s, w, 0.008 + 0.03 * math.sin(min(1.0, max(0.0, s / l_ges)) * PI) ** 1.5 + 0.0015)
				for s in np.linspace(0.05, l_ober - 0.02, 14)]
			g.zug(r, pts, 0.006, "futter", flach=0.3, aussen=lambda p, fa=fa: Vector((0, 0, 1)))
	teile.append(r.objekt())
	b, fr = ws.vernietet(K, 0.028, "stoff_dunkel", 0.92, "brigantine", nieten=True)
	teile += b
	teile += schulter(K, 1, A=0.05, gross=1.15, brechrand=0.05, lamellen=3, bogen=0.05)
	teile += tassetten(K, 0.95, 0.2, 0.07, 2, (0.75, -0.75), 0.5)
	teile += ir.guertel(K, 0.95, 0.05, 0.07)
	return g.vereinen(teile, "x")


def greatsword_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.028, 0.12, 0.014, platte=True)
	return g.vereinen(teile, "x")


def greatsword_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006, bein_extra=ws.puffhose(0.045))
	r = g.Teil("schlitze")
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite, konvex=0.4)
		pf = ws.puffhose(0.045)
		for k in range(10):
			w = 2 * PI * k / 10
			pts = [fb.punkt(s, w, 0.006 + pf(s, w, l_knie, l_ges) + 0.0015) for s in np.linspace(0.08, l_knie - 0.05, 14)]
			g.zug(r, pts, 0.006, "stoff_akzent", flach=0.3, aussen=lambda p: Vector((0, 0, 1)))
		teile += ws.kniekachel(K, seite, 0.016, 1.4)
		ring(r, fb, l_knie + 0.06, 0.012, 0.007, "stoff_akzent", flach=0.4, n=48)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def greatsword_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder_dunkel", 0.18, kappe=True)
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("riemen")
		ring(r, fb, l_ges - 0.09, 0.015, 0.006, "rand", flach=0.4, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Speer: attischer Helm, Muskelpanzer, Lederstreifen (MMMMM)


def spear_kopf(K):
	return attisch(K)


def spear_brust(K):
	teile, _ = ir.wams(K, "stoff_akzent", 0.006, unten_z=0.66, kragen_z=1.53, aermel_bis=0.3, weite=0.04,
		aermel_abstand=0.005)
	m, f = muskelpanzer(K, 0.02)
	teile += m
	teile += pteruges(K, 0.97, 0.25, 0.05, 22)
	# Schulterstreifen
	for seite in (1, -1):
		fa = ir.oberarm_feld(K, seite)
		aussen = 3 * PI / 2 if seite > 0 else PI / 2
		for k in range(5):
			w0 = aussen - 1.0 + 0.5 * k
			teile.append(blech("schulterstreifen", fa, 0.06, 0.2, lambda s, w: 0.028 + 0.015 * g.weich(s, 0.1, 0.2), d=0.004,
				nu=6, nw=3, w_von=w0 - 0.2, w_bis=w0 + 0.2, material_name="leder"))
	# Löwenköpfe auf der Brust (Medaillons)
	r = g.Teil("medaillons")
	for sg in (1, -1):
		s, w = 0.52, sg * 0.45
		g.niete(r, f.punkt(s, w, 0.022), f.normale(s, w, 0.02), 0.02, "rand")
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.99, 0.04, 0.045)
	return g.vereinen(teile, "x")


def spear_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder", 0.003, 0.05))
		teile += armschiene(K, seite, 0.012, "leder", platte=True)
	return g.vereinen(teile, "x")


def spear_beine(K):
	teile, _ = ir.wams(K, "stoff_akzent", 0.006, unten_z=0.70, kragen_z=1.0, aermel_bis=0.0, weite=0.03)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite, konvex=0.4)
		# Beinschienen (Knemiden) nach der Wade geformt, Knie frei
		kn = lambda s, w: 0.012 + 0.012 * math.exp(-((s - l_knie) / 0.04) ** 2) * math.cos(min(g.wdiff(w, 0), PI / 2)) ** 2
		teile.append(blech("knemide", fb, l_knie - 0.06, l_ges - 0.06, kn, d=0.003, nu=36, nw=48, w_von=-2.2, w_bis=2.2))
	teile += ir.hose(K, "stoff", 0.004)
	return g.vereinen(teile, "x")


def spear_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.008, 0.1))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("riemen")
		for k in range(3):
			ring(r, fb, l_ges - 0.03 - 0.035 * k, 0.012, 0.005, "leder_dunkel", flach=0.35, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Eismagie: Robe mit Pelerine, Halsberge, Diadem auf der Kapuze (MMMMM)


def ice_kopf(K):
	teile, f, w = kapuze_diadem(K, "stoff", saum="futter", A=0.03, gesicht=0.85, tief=0.03,
		kragen_unten=tabelle([(0, 0.5), (PI / 2, 0.52), (PI, 0.46)]))
	return g.vereinen(teile, "x")


def ice_brust(K):
	teile, f = robe(K, "stoff", 0.02, 0.07, manschette=0.04)
	teile += kragen_lagen(K, 2, (0.40, 0.52), 0.035, "stoff_akzent", gezackt_tiefe=0.03)
	# Halsberge aus Blech über der Pelerine
	fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	hk_u = tabelle([(0, 0.6), (PI / 2, 0.62), (PI, 0.64)])
	teile.append(blech("halsberge", fr, hk_u, 0.79, lambda s, w: 0.075 + 0.02 * g.weich(-s, -0.72, -0.6), d=0.003, nu=10, nw=96))
	r = g.Teil("rand")
	pts, zu = g.rand_punkte(fr, hk_u, lambda s, w: 0.075 + 0.02 * g.weich(-s, -0.72, -0.6) + 0.002, n=120)
	g.zug(r, pts, 0.005, "rand", zu=zu)
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.98, 0.07, 0.04, "platte")
	return g.vereinen(teile, "x")


def ice_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.03, 0.12, 0.016, platte=True)
	return g.vereinen(teile, "x")


def ice_beine(K):
	return g.vereinen(ir.hose(K, "stoff_dunkel", 0.004), "x")


def ice_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.24, umschlag=0.04, bogen=0.015)
	return g.vereinen(teile, "x")


# ================================================================ LEICHT BIS MITTEL


# ---------------- Degen: Barett, Halskrause, Gänsebauch-Brust, halber Mantel (LMLML)


def rapier_kopf(K):
	f = ir.kopf_feld(K)
	puff = lambda s, w: 0.012 + 0.055 * math.sin(min(1.0, s / 1.12) * PI) ** 0.8 * (0.75 + 0.35 * math.cos(w + PI / 2))
	flach = lambda s, w: puff(s, w) - 0.035 * max(0.0, 1 - s / 0.5) ** 2
	teile = [blech("barett", f, 0.0, 1.12, flach, d=0.004, nu=30, nw=96, material_name="stoff_dunkel")]
	r = g.Teil("band")
	ring(r, f, 1.1, 0.012, 0.008, "rand", flach=0.5, n=96)
	for k in range(8):
		w = PI / 2 + 0.3 + 0.12 * k
		g.niete(r, f.punkt(1.0, w, flach(1.0, w) + 0.001), f.normale(1.0, w, flach(1.0, w)), 0.006, "futter")
	g.niete(r, f.punkt(0.95, -PI / 2 - 0.3, flach(0.95, -PI / 2 - 0.3) + 0.004), Vector((-1, 0, 0.2)), 0.014, "rand")
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def rapier_brust(K):
	teile, _ = ir.wams(K, "futter", 0.006, unten_z=0.92, kragen_z=1.53, aermel_bis=1.0, weite=0.0, aermel_abstand=0.006,
		puff=0.04, manschette=0.01, aermel_material="stoff_akzent")
	b, f = brustplatte(K, 0.03, 1.0, 0.03)
	teile += b
	teile.append(halskrause(K, 1.535, 0.02, 0.04, 30))
	u, fw, weite = umhang(K, 0.88, A=0.075, material="stoff_dunkel", einseitig=1)
	teile += u
	teile += ir.guertel(K, 0.98, 0.04, 0.04)
	return g.vereinen(teile, "x")


def rapier_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.04, 0.15, 0.02)
	return g.vereinen(teile, "x")


def rapier_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006, bein_extra=ws.puffhose(0.03))
	for seite in (1, -1):
		teile += ws.kniekachel(K, seite, 0.014, 1.2, "leder")
	return g.vereinen(teile, "x")


def rapier_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.42, weite=0.03, umschlag=0.08, bogen=0.025, abstand=0.013)
	return g.vereinen(teile, "x")


# ---------------- Bogen: Kapuze mit gezackter Pelerine, Gambeson, Armschienen (LMLML)


def bow_kopf(K):
	teile, f, w = ws.kapuze(K, "stoff", A=0.026, gesicht=0.9, saum="stoff_akzent", kragen=False, tief=0.02)
	teile += kragen_lagen(K, 1, (0.5,), 0.028, "stoff", gezackt_tiefe=0.05)
	return g.vereinen(teile, "x")


def bow_brust(K):
	teile, f = ir.wams(K, "stoff_akzent", 0.008, unten_z=0.66, kragen_z=1.5, aermel_bis=1.0, steppung=0.003, weite=0.05,
		aermel_abstand=0.006)
	t1, v1, fr = ws.schraeg_riemen(K, 0.022, 0.016, "leder", links_oben=True)
	teile.append(t1.objekt())
	# Lederkoller mit gebogtem Saum
	b, _ = ws.vernietet(K, 0.024, "leder", 0.9, "koller", nieten=False)
	teile += b
	teile += ir.guertel(K, 0.97, 0.05, 0.04)
	tt = g.Teil("tasche")
	fw = ir.wams_feld(K)
	ws.tasche(tt, fw.punkt(0.9 - ZW, 1.0, 0.07), fw.normale(0.9 - ZW, 1.0, 0.06), 0.08, 0.09, 0.03)
	teile.append(tt.objekt())
	return g.vereinen(teile, "x")


def bow_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ws.fingerlos(K, seite, "leder"))
		teile += armschiene(K, seite, 0.012, "leder_dunkel", platte=True)
	return g.vereinen(teile, "x")


def bow_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006)
	for seite in (1, -1):
		teile += ws.lederschutz(K, seite)
	return g.vereinen(teile, "x")


def bow_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.36, weite=0.012, umschlag=0.06, bogen=0.02)
	return g.vereinen(teile, "x")


# ---------------- Armbrust: Eisenhut, Gambeson mit Brustplatte und Beintaschen (LMLML)


def crossbow_kopf(K):
	return eisenhut(K)


def crossbow_brust(K):
	teile, f = ir.wams(K, "stoff", 0.008, unten_z=0.66, kragen_z=1.52, aermel_bis=1.0, steppung=0.004, weite=0.05,
		aermel_abstand=0.007)
	b, fr = brustplatte(K, 0.034, 0.98, 0.02, rf=4)
	teile += b
	teile += tassetten(K, 0.95, 0.16, 0.07, 2, (0.6, -0.6), 0.5)
	teile += ir.guertel(K, 0.96, 0.05, 0.075)
	tt = g.Teil("bolzentasche")
	fw = ir.wams_feld(K)
	ws.tasche(tt, fw.punkt(0.86 - ZW, 1.4, 0.09), fw.normale(0.86 - ZW, 1.4, 0.08), 0.07, 0.15, 0.04)
	teile.append(tt.objekt())
	return g.vereinen(teile, "x")


def crossbow_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.022, 0.09, 0.01)
	return g.vereinen(teile, "x")


def crossbow_beine(K):
	teile = ir.hose(K, "stoff", 0.006, bein_extra=ws.steppnaht())
	for seite in (1, -1):
		teile += ws.kniekachel(K, seite, 0.016, 1.5)
	return g.vereinen(teile, "x")


def crossbow_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder_dunkel", 0.22, kappe=True)
	return g.vereinen(teile, "x")


# ---------------- Muskete: Cabasset, langer Lederrock, Bandelier mit Pulverflaschen, Schärpe (LMLML)


def musket_kopf(K):
	return cabasset(K, 0.028, None)


def musket_brust(K):
	teile, f = ir.wams(K, "leder", 0.01, unten_z=0.52, kragen_z=1.52, aermel_bis=1.0, weite=0.07, aermel_abstand=0.007,
		offen=0.12, manschette=0.03)
	t1, v1, fr = ws.schraeg_riemen(K, 0.03, 0.018, "leder_dunkel", links_oben=True)
	for i in range(6, 28, 4):
		p = v1[i]
		n = (p - fr.achse.punkt(p.z - Z0)).normalized()
		ws.flasche(t1, p + n * 0.02, 0.022, "holz")
	teile.append(t1.objekt())
	teile += schaerpe(K, 0.97, 1, "stoff_akzent")
	teile.append(halskrause(K, 1.53, 0.02, 0.025, 24))
	return g.vereinen(teile, "x")


def musket_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.036, 0.14, 0.018)
	return g.vereinen(teile, "x")


def musket_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite, konvex=0.4)
		r = g.Teil("band")
		ring(r, fb, l_knie + 0.03, 0.012, 0.009, "stoff_akzent", flach=0.4, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def musket_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.42, weite=0.035, umschlag=0.09, bogen=0.025, abstand=0.013)
	return g.vereinen(teile, "x")


# ---------------- Lebensmagie: weiße Robe mit Stola, Mantel mit Spange, Diadem (LMLML)


def life_kopf(K):
	"""Diadem und Schleier: offener Schleier über dem Hinterkopf, Reif über der Stirn."""
	f = ir.kopf_feld(K, huelle=14)
	A = 0.016
	teile = []
	weit = lambda s, w: A + 0.02 * g.weich(s, 1.4, 2.3)
	t = g.Teil("schleier")
	unten = lambda w: 2.2 + 0.25 * g.weich(g.wdiff(w, 0), 1.8, 2.8)
	g.platte(t, f, 0.0, unten, weit, nu=28, nw=96, material_name="futter", w_von=1.25, w_bis=2 * PI - 1.25)
	g.platte(t, f, 0.0, 1.1, weit, nu=14, nw=40, material_name="futter", w_von=-1.27, w_bis=1.27)
	teile.append(obj(t, 60, 0.004))
	r = g.Teil("diadem")
	diadem(r, f, lambda s, w: weit(s, w) + 0.003, 1.1)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def life_brust(K):
	teile, f = robe(K, "futter", 0.02, 0.06, manschette=0.03)
	teile.append(stola(K, "stoff_akzent", 0.3, 0.07, 0.3))
	fw = ir.wams_feld(K, 0.38)
	weite = lambda s, w: 0.05 + 0.1 * g.weich(-(s + 0.12) - ZW, -0.95, -0.40)
	oben = tabelle([(0, 1.44), (1.0, 1.5), (PI / 2, 1.53), (PI, 1.52)])
	t = g.Teil("mantel")
	g.platte(t, fw, lambda w: 0.40 - ZW, lambda w: oben(w) - ZW, weite, nu=56, nw=80, w_von=0.6, w_bis=2 * PI - 0.6,
		material_name="futter")
	teile.append(obj(t, 60, 0.004))
	r = g.Teil("spange")
	fr = ir.rumpf_feld(K)
	pts = [fr.punkt(0.66, u * 0.62, 0.075) for u in np.linspace(-1, 1, 20)]
	g.zug(r, pts, 0.004, "rand")
	for sg in (1, -1):
		g.niete(r, fr.punkt(0.66, sg * 0.62, 0.075), fr.normale(0.66, sg * 0.62, 0.07), 0.018, "rand")
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.97, 0.05, 0.034, "leder")   # unter dem offenen Mantel
	return g.vereinen(teile, "x")


def life_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "futter", 0.03, 0.12, 0.018)
	return g.vereinen(teile, "x")


def life_beine(K):
	return g.vereinen(ir.hose(K, "futter", 0.004), "x")


def life_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.18, umschlag=0.035, bogen=0.012)
	return g.vereinen(teile, "x")


# ================================================================ LEICHT


def leicht_kopf(K):
	"""Flache Mütze mit Ohrenklappen."""
	f = ir.kopf_feld(K)
	puff = lambda s, w: 0.014 + 0.03 * math.sin(min(1.0, s / 1.15) * PI) ** 0.8
	teile = [blech("muetze", f, 0.0, 1.15, puff, d=0.004, nu=24, nw=96, material_name="stoff_akzent")]
	r = g.Teil("rand")
	ws.krempe(r, f, 1.12, 0.016, lambda w: 0.025 + 0.012 * math.cos(w) ** 2, "stoff_akzent", neigung=-0.6, n=96, stufen=3)
	for sg in (1, -1):
		wm = sg * PI / 2
		teile.append(blech("klappe", f, 1.12, lambda w, wm=wm: 1.95 - 0.1 * (g.wdiff(w, wm) / 0.5) ** 2, 0.014, d=0.004,
			nu=10, nw=16, w_von=wm - 0.5, w_bis=wm + 0.5, material_name="stoff_akzent"))
	teile.append(obj(r, 50, 0.004))
	return g.vereinen(teile, "x")


def leicht_brust(K):
	teile, f = ir.wams(K, "stoff", 0.008, unten_z=0.70, kragen_z=1.52, aermel_bis=1.0, weite=0.10, aermel_abstand=0.007,
		puff=0.03, manschette=0.01, aermel_material="stoff_akzent")
	r = g.Teil("schlitze")
	for seite in (1, -1):
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
		for k in range(8):
			w = 2 * PI * k / 8
			pts = [fa.punkt(s, w, 0.007 + 0.03 * math.sin(min(1.0, max(0.0, s / l_ges)) * PI) ** 1.5 + 0.0015)
				for s in np.linspace(0.05, l_ober - 0.02, 14)]
			g.zug(r, pts, 0.006, "futter", flach=0.3, aussen=lambda p: Vector((0, 0, 1)))
	teile.append(r.objekt())
	b, _ = ws.vernietet(K, 0.022, "leder", 0.9, "weste", nieten=False, offen=0.08)
	teile += b
	u, fw, weite = umhang(K, 1.02, A=0.06, material="stoff_akzent", einseitig=-1)
	teile += u
	teile += ir.guertel(K, 0.96, 0.04, 0.034)
	return g.vereinen(teile, "x")


def leicht_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder", 0.02, 0.1, 0.012)
	return g.vereinen(teile, "x")


def leicht_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006, bein_extra=ws.puffhose(0.03))
	return g.vereinen(teile, "x")


def leicht_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.24, weite=0.014, umschlag=0.05, bogen=0.016)
	return g.vereinen(teile, "x")


# ---------------- Messer: Kapuze mit Halbmaske, hochgeschlossener Koller mit Kreuzriemen (LLLLL)


def knife_kopf(K):
	teile, f, weit = ws.kapuze(K, "stoff_dunkel", A=0.022, gesicht=0.9, saum="rand",
		kragen_unten=tabelle([(0, 0.5), (PI / 2, 0.52), (PI, 0.48)]), tief=0.02, kragen_ab=0.018)
	tuch = lambda s, w: 0.008 + 0.006 * g.weich(s, 1.9, 2.3)
	o = lambda w: AUGE_S + 0.1 + 0.15 * (g.wdiff(w, 0) / 1.0) ** 2
	teile.append(blech("tuch", f, o, 2.45, tuch, d=0.003, nu=16, nw=40, w_von=-1.0, w_bis=1.0, material_name="leder_dunkel"))
	r = g.Teil("rand")
	pts, _ = g.rand_punkte(f, o, tuch, w_von=-1.0, w_bis=1.0, n=40)
	g.zug(r, pts, 0.003, "rand")
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def knife_brust(K):
	teile, f = ir.wams(K, "leder_dunkel", 0.005, unten_z=0.86, kragen_z=1.54, aermel_bis=1.0, weite=0.02, aermel_abstand=0.004)
	teile.append(stehkragen(K, 0.06, 0.012, "leder_dunkel", 0.25, 0.008))
	t1, v1, fr = ws.schraeg_riemen(K, 0.018, 0.012, "leder", links_oben=True)
	t2, v2, _ = ws.schraeg_riemen(K, 0.022, 0.012, "leder", links_oben=False)
	for vs, tt in ((v1, t1), (v2, t2)):
		for i in (12, 18, 24):
			p = vs[i]
			n = (p - fr.achse.punkt(p.z - Z0)).normalized()
			ws.scheide(tt, p + n * 0.014, (vs[i - 3] - vs[i + 3]).normalized(), n, 0.1)
	teile += [t1.objekt(), t2.objekt()]
	teile += ir.guertel(K, 0.96, 0.045, 0.02)
	return g.vereinen(teile, "x")


def knife_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ws.fingerlos(K, seite, "leder_dunkel"))
		teile += armschiene(K, seite, 0.009, "leder_dunkel", platte=True)
	return g.vereinen(teile, "x")


def knife_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.004)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite, konvex=0.6)
		r = g.Teil("riemen")
		for s in (0.14, 0.24):
			ring(r, fb, s, 0.008, 0.007, "leder", flach=0.35, n=40)
		teile.append(r.objekt())
		tt = g.Teil("scheide")
		w = 3 * PI / 2 if seite > 0 else PI / 2
		p = fb.punkt(0.2, w, 0.02)
		ws.scheide(tt, p, Vector((0, 0, -1)), fb.normale(0.2, w, 0.02), 0.14)
		teile.append(tt.objekt())
	return g.vereinen(teile, "x")


def knife_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder_dunkel", 0.3, abstand=0.006)
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("schnallen")
		for k in range(3):
			ring(r, fb, l_ges - 0.08 - 0.07 * k, 0.012, 0.005, "leder", flach=0.35, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Feuermagie: Robe mit Flammensaum, Pelerine, hoher Kragen (LLLLL)


def fire_kopf(K):
	teile, f, w = kapuze_diadem(K, "stoff_akzent", saum="stoff_dunkel", A=0.03, gesicht=0.85, tief=0.035, kragen=False)
	return g.vereinen(teile, "x")


def fire_brust(K):
	teile, f = ir.wams(K, "stoff_akzent", 0.02, unten_z=0.10, kragen_z=1.54, aermel_bis=1.0, weite=0.07, z0=0.08,
		aermel_abstand=0.01, manschette=0.035, rock_ab=0.95)
	# Überrock vorne und hinten mit Flammensaum
	fw = ir.wams_feld(K, 0.30)
	flamme = lambda w: 0.40 - ZW - 0.09 * abs(math.sin(w * 6)) ** 3 - 0.03 * abs(math.sin(w * 13))
	for mitte in (0.0, PI):
		t = g.Teil("ueberrock")
		g.platte(t, fw, flamme, 1.0 - ZW, lambda s, w: 0.032 + 0.085 * g.weich(-s - ZW, -0.95, -0.35), nu=50, nw=40,
			w_von=mitte - 0.75, w_bis=mitte + 0.75, material_name="stoff_dunkel")
		teile.append(obj(t, 60, 0.004))
	teile += kragen_lagen(K, 1, (0.5,), 0.03, "stoff_dunkel", gezackt_tiefe=0.06)   # kein Stehkragen: die Kapuze deckt den Hals
	teile += schaerpe(K, 0.98, -1, "stoff_dunkel")
	return g.vereinen(teile, "x")


def fire_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "stoff_dunkel", 0.03, 0.12, 0.02)
	return g.vereinen(teile, "x")


def fire_beine(K):
	return g.vereinen(ir.hose(K, "stoff_dunkel", 0.004), "x")


def fire_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder", 0.16)
	return g.vereinen(teile, "x")


# ---------------- Blitzmagie: langer Mantel mit doppelter Pelerine, Stehkragen, Diadem (LLLLL)


def lightning_kopf(K):
	f = ir.kopf_feld(K)
	r = g.Teil("diadem")
	diadem(r, f, 0.012, 1.1, 0.045)
	# Haarband hinten (Kopf bleibt frei)
	return g.vereinen([r.objekt()], "x")


def lightning_brust(K):
	teile, f = ir.wams(K, "stoff_dunkel", 0.012, unten_z=0.28, kragen_z=1.53, aermel_bis=1.0, weite=0.08, z0=0.26,
		aermel_abstand=0.008, manschette=0.03, rock_ab=0.95, offen=0.18)
	teile += kragen_lagen(K, 2, (0.38, 0.5), 0.03, "stoff_akzent")
	teile.append(stehkragen(K, 0.1, 0.03, "stoff_dunkel", 0.45, 0.035))
	teile += ir.guertel(K, 0.97, 0.05, 0.03)
	return g.vereinen(teile, "x")


def lightning_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhand(K, seite, "leder_dunkel", 0.026, 0.11, 0.016)
	return g.vereinen(teile, "x")


def lightning_beine(K):
	return g.vereinen(ir.hose(K, "stoff", 0.005), "x")


def lightning_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile += stiefel_pal(K, seite, "leder_dunkel", 0.36, weite=0.01, umschlag=0.05, bogen=0.02)
	return g.vereinen(teile, "x")


# ================================================================ Zuordnung


BAU = {}
for _s in ("schwer", "mittel", "leicht"):
	BAU[_s] = {slot: globals()[_s + "_" + slot] for slot in SLOTS}
BAU["sword_shield"] = {slot: globals()["sus_" + slot] for slot in SLOTS}
for _w in ("hammer", "axe", "void_magic", "greatsword", "spear", "ice_magic", "rapier", "bow", "crossbow", "musket",
		"life_magic", "knife", "fire_magic", "lightning_magic"):
	_k = _w.replace("_magic", "")
	BAU[_w] = {slot: globals()[_k + "_" + slot] for slot in SLOTS}
