"""Iron-Waffensätze: je Waffe ein Satz aus 5 Teilen (kopf, brust, haende, beine, fuesse).

Die Klasse jedes Teils (leicht/mittel/schwer) folgt der Tabelle im Rüstungsplan; das Gewicht der Teile
bestimmt im Spiel die Gesamtklasse. Die Grundformen kommen aus iron.py, hier stehen die Besonderheiten
jedes Satzes (Helmform, Umhang, Riemen, Taschen …). Namen: iron_<waffe>_<slot>, <waffe> = id aus weapons.json.
"""
import math
import bmesh
import numpy as np
from mathutils import Vector
import rgeo as g
import iron as ir
from iron import tabelle, ZW, Z0

PI = math.pi
SLOTS = ["kopf", "brust", "haende", "beine", "fuesse"]
AUGE_S, AUGE_W = 1.70, 0.36   # Augenmitte auf dem Kopffeld (s von oben, w zur Seite)

# Klasse je Teil (kopf, brust, haende, beine, fuesse) und Beschreibung für die Rüstkammer
SAETZE = {
	"sword_shield": ("Schwert und Schild", "SSSSS"),
	"hammer": ("Hammer", "SSSSS"),
	"axe": ("Axt", "MSMSM"),
	"void_magic": ("Leerenmagie", "MSMSM"),
	"greatsword": ("Großschwert", "MMMMM"),
	"spear": ("Speer", "MMMMM"),
	"ice_magic": ("Eismagie", "MMMMM"),
	"rapier": ("Degen", "LMLML"),
	"bow": ("Bogen", "LMLML"),
	"crossbow": ("Armbrust", "LMLML"),
	"musket": ("Muskete", "LMLML"),
	"life_magic": ("Lebensmagie", "LMLML"),
	"knife": ("Messer", "LLLLL"),
	"fire_magic": ("Feuermagie", "LLLLL"),
	"lightning_magic": ("Blitzmagie", "LLLLL"),
}


def bauen(K, waffe):
	"""Alle 5 Teile eines Waffensatzes als dict slot -> Objekt (Name iron_<waffe>_<slot>)."""
	fn = BAU[waffe]
	out = {}
	for slot in SLOTS:
		ob = fn[slot](K)
		ob.name = "iron_%s_%s" % (waffe, slot)
		ob.data.name = ob.name
		out[slot] = ob
	return out


# ================================================================ Hilfen


def obj(t, winkel=40, d=None, versatz=-1.0):
	o = t.objekt(winkel)
	if d:
		g.dicke(o, d, versatz)
	return o


def blech(t, feld, a, b, A, d=0.0025, **kw):
	"""Platte mit Blechstärke als eigenes Objekt."""
	tt = g.Teil(t)
	g.platte(tt, feld, a, b, A, **kw)
	return obj(tt, 30, d)


def ring(r, feld, s, A, radius=0.004, material="rand", flach=1.0, **kw):
	pts, zu = g.rand_punkte(feld, s, A, **kw)
	g.zug(r, pts, radius, material, zu=zu, flach=flach)


def kopfmitte(f):
	return f.c


def topf_flaeche(f, A, rund=0.0, hoeher=0.0, weiter=0.0):
	"""Abstandsfunktion für zylindrische Helme/Hüte: senkrechter (leicht elliptischer) Zylinder mit flachem Deckel
	um den Kopf. rund rundet die Deckelkante, hoeher/weiter vergrößern den Zylinder."""
	# Zylinderradius je Winkel w: größter waagrechter Kopfradius + A
	ws = np.linspace(0, 2 * PI, 97)
	R = []
	for w in ws:
		R.append(max(f.radius(s, w) * math.sin(s) for s in np.linspace(0.6, 2.0, 15)) + A + weiter)
	R = np.array(R)
	R = 0.5 * R + 0.5 * (R + np.roll(R, 1) + np.roll(R, -1) + np.roll(R, 2) + np.roll(R, -2)) / 5
	H = max(f.radius(s, w) * math.cos(s) for s in np.linspace(0, 0.6, 8) for w in np.linspace(0, 2 * PI, 12)) + A + hoeher

	def ab(s, w):
		rw = float(np.interp(w % (2 * PI), ws, R))
		t_z = rw / max(1e-4, math.sin(s))
		if math.cos(s) > 1e-4:
			t_d = H / math.cos(s)
			if rund > 0:
				# weiche Minimumbildung = gerundete Kante
				k = rund
				t = -k * math.log(math.exp(-t_z / k) + math.exp(-t_d / k))
			else:
				t = min(t_z, t_d)
		else:
			t = t_z
		return max(t - f.radius(s, w), A)
	return ab, H, R


def krempe(r, f, s_fn, ab_fn, breite, material="platte", neigung=0.25, n=96, hoch=None, stufen=4):
	"""Hutkrempe: Ring an der Kopfhülle bei s_fn(w), waagrecht nach außen um breite(w).
	neigung > 0 hängt nach unten. hoch(w) biegt den Rand nach oben (Krempe hochgeschlagen)."""
	reihen = []
	for j in range(n):
		w = 2 * PI * j / n
		s = g._wert(s_fn, w)
		p = f.punkt(s, w, ab_fn(s, w) if callable(ab_fn) else ab_fn)
		h = p - f.c
		h.z = 0
		h.normalize()
		b = g._wert(breite, w)
		zeile = []
		for i in range(stufen + 1):
			u = i / stufen
			q = p + h * b * u + Vector((0, 0, -neigung * b * u * u))
			if hoch:
				q.z += g._wert(hoch, w) * u ** 2
			zeile.append(r.vert(q))
		reihen.append(zeile)
	for j in range(n):
		k = (j + 1) % n
		for i in range(stufen):
			r.flaeche([reihen[j][i], reihen[k][i], reihen[k][i + 1], reihen[j][i + 1]], material)
	return [z[-1].co.copy() for z in reihen]


def blatt(t, pts, breite, normale, material="feder"):
	"""Flaches Band entlang pts mit Breitenprofil breite(u), quer zu 'normale' (Feder, Stola, Tuchende)."""
	n = len(pts)
	links, rechts = [], []
	for i, p in enumerate(pts):
		a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
		tg = (b - a).normalized()
		nn = normale(p) if callable(normale) else Vector(normale)
		q = tg.cross(nn).normalized()
		w = breite(i / (n - 1))
		links.append(t.vert(p + q * w))
		rechts.append(t.vert(p - q * w))
	for i in range(n - 1):
		t.flaeche([links[i], rechts[i], rechts[i + 1], links[i + 1]], material)


def feder(t, p0, richtung, oben, laenge=0.2, breite=0.025, material="feder"):
	"""Gebogene Hutfeder ab p0 in 'richtung', nach 'oben' geschwungen."""
	d = Vector(richtung).normalized()
	o = Vector(oben).normalized()
	pts = [p0 + d * laenge * u + o * laenge * 0.35 * math.sin(u * PI * 0.8) for u in np.linspace(0, 1, 18)]
	quer = d.cross(o).normalized()
	blatt(t, pts, lambda u: breite * math.sin(min(1.0, u * 1.15) * PI) ** 0.6 + 0.002, quer, material)
	g.zug(t, pts[:-2], 0.0015, material)


def tasche(t, p, n, b=0.06, h=0.07, d=0.025, material="leder"):
	"""Gürteltasche: flacher Quader-Schlauch an p, Rückseite zum Körper (n = nach außen)."""
	n = Vector(n).normalized()
	quer = n.cross(Vector((0, 0, 1))).normalized()
	oben = quer.cross(n).normalized()
	g.zug(t, [p + oben * h / 2 + n * d / 2, p - oben * h / 2 + n * d / 2], b / 2, material, seg=8, flach=d / b,
		aussen=lambda q: quer)
	# Deckel
	g.zug(t, [p + oben * h / 2 + n * (d + 0.004), p + oben * h * 0.1 + n * (d + 0.006)], b / 2 + 0.003, "leder_dunkel",
		seg=8, flach=0.12, aussen=lambda q: quer)


def flasche(t, p, groesse=0.035, material="holz"):
	"""Pulverflasche / Phiole: Zylinder mit Hals, hängt senkrecht."""
	g.zug(t, [p, p + Vector((0, 0, -groesse * 1.4))], groesse * 0.42, material, seg=10)
	g.zug(t, [p + Vector((0, 0, groesse * 0.35)), p], groesse * 0.16, "rand", seg=8)


def schraeg_riemen(K, A=0.03, breite=0.016, material="leder", feld=None, links_oben=True, z_unten=0.98, w_unten=None):
	"""Bandelier/Köcherriemen schräg über die Brust: Schulter links oben -> Hüfte rechts (oder gespiegelt).
	Gibt (Teil, Punkte vorne) zurück."""
	f = feld or ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	sg = 1 if links_oben else -1
	s_u = z_unten - Z0
	w_u = w_unten if w_unten is not None else -1.35 * sg
	pfad = []
	# vorne: Hüfte -> Schulter
	for u in np.linspace(0, 1, 30):
		pfad.append((s_u + (0.70 - s_u) * u, w_u + (0.62 * sg - w_u) * u))
	# über die Schulter
	for u in np.linspace(0, 1, 16)[1:]:
		pfad.append((0.70, 0.62 * sg + (2.5 - 0.62) * sg * u))
	# hinten: Schulter -> Hüfte
	w_h = PI - (PI - abs(w_u)) * 1.0 if sg > 0 else -(PI - abs(w_u))
	w_h = (PI + 1.35) * sg if w_unten is None else (2 * PI - w_unten if sg > 0 else -2 * PI - w_unten)
	for u in np.linspace(0, 1, 30)[1:]:
		pfad.append((0.70 + (s_u - 0.70) * u, 2.5 * sg + (w_h - 2.5 * sg) * u))
	pts = [f.punkt(s, w, A) for s, w in pfad]
	t = g.Teil("riemen")
	g.zug(t, pts, breite, material, flach=0.25, aussen=lambda p: (p - f.achse.punkt(p.z - Z0)).normalized())
	return t, pts[:30], f


def tabard(K, unten_z=0.50, A=0.06, material="stoff_akzent", breite=0.95, name="wappenrock"):
	"""Wappenrock aus zwei Bahnen (vorne/hinten), offen an den Seiten, über der Platte."""
	f = ir.wams_feld(K)
	teile = []
	oben = tabelle([(0, 0.66), (0.5, 0.70), (0.95, 0.70), (2.2, 0.72), (PI, 0.73)])
	fl = lambda s, w: 0.02 * g.weich(-s, -(0.85 - ZW), -(unten_z - ZW)) + 0.01 * g.weich(s, 1.18 - ZW, 1.4 - ZW)
	for mitte in (0.0, PI):
		t = g.Teil(name)
		g.platte(t, f, unten_z - ZW, lambda w: oben(w) + 0.795 - ZW, lambda s, w: A + fl(s, w), nu=50, nw=40,
			w_von=mitte - breite, w_bis=mitte + breite, material_name=material)
		o = obj(t, 60, 0.004)
		teile.append(o)
		r = g.Teil("saum")
		pts, _ = g.rand_punkte(f, unten_z - ZW + 0.004, lambda s, w: A + fl(s, w) + 0.003, w_von=mitte - breite,
			w_bis=mitte + breite, n=40)
		g.zug(r, pts, 0.004, "futter", flach=0.5)
		teile.append(r.objekt())
	return teile, f


def kapuze(K, material="stoff", A=0.022, gesicht=0.95, gesicht_unten=2.45, zipfel=0.0, kragen=True,
		kragen_unten=None, saum="stoff_akzent", tief=0.0, name="kapuze", kragen_weite=0.03, kragen_ab=0.0):
	"""Kapuze: Gesichtsöffnung |w| < gesicht, tief zieht den Rand nach vorne über die Stirn, hinten fällt sie weich.
	kragen_unten: Tabelle für die Unterkante des Schulterkragens (None = Gugel-Standard)."""
	f = ir.kopf_feld(K, huelle=14)
	zf = lambda s, w: zipfel * math.exp(-(g.wdiff(w, PI) / 0.5) ** 2) * math.exp(-((s - 0.75) / 0.35) ** 2)
	vor = lambda s, w: tief * math.exp(-(g.wdiff(w, 0) / 0.9) ** 2) * g.weich(s, 0.5, 1.0)
	# weicher Stoff: hinten am Hinterkopf etwas weiter, oben anliegend
	fall = lambda s, w: 0.012 * math.exp(-(g.wdiff(w, PI) / 1.2) ** 2) * g.weich(s, 0.9, 1.8)
	weit = lambda s, w: A + zf(s, w) + 0.012 * g.weich(s, 1.6, 2.4) + vor(s, w) + fall(s, w)
	s_stirn = 1.05 - tief * 3.0
	t = g.Teil(name)
	g.platte(t, f, 0.0, s_stirn, weit, nu=24, nw=96, material_name=material)
	g.platte(t, f, s_stirn, 2.45, weit, nu=28, nw=60, w_von=gesicht, w_bis=2 * PI - gesicht, material_name=material)
	if gesicht_unten < 2.45:
		g.platte(t, f, gesicht_unten, 2.45, weit, nu=4, nw=24, w_von=-gesicht - 0.02, w_bis=gesicht + 0.02,
			material_name=material)
	teile = [obj(t, 60, 0.004)]
	r = g.Teil("saum")
	if kragen:
		fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
		kt = g.Teil("kragen")
		flare = lambda s, w: 0.025 + kragen_ab + kragen_weite * g.weich(-s, -0.68, -0.48)
		ku = kragen_unten or tabelle([(0, 0.44), (0.9, 0.5), (PI / 2, 0.52), (2.3, 0.5), (PI, 0.46)])
		g.platte(kt, fr, ku, 0.79, 0.0, nu=24, nw=96, extra=flare, material_name=material)
		teile.append(obj(kt, 60, 0.004))
		pts, zu = g.rand_punkte(fr, ku, 0.0, n=120, extra=lambda s, w: flare(s, w) + 0.002)
		g.zug(r, pts, 0.004, saum, zu=zu, flach=0.5)
	gs = []
	for k in range(25):
		w = -gesicht - 0.01 + (2 * gesicht + 0.02) * k / 24
		gs.append(f.punkt(gesicht_unten, w, weit(gesicht_unten, w)))
	for k in range(36):
		s = gesicht_unten - (gesicht_unten - s_stirn) * k / 35
		gs.insert(0, f.punkt(s, -gesicht, weit(s, -gesicht)))
		gs.append(f.punkt(s, gesicht, weit(s, gesicht)))
	if gesicht_unten >= 2.45:
		gs = gs[:36] + gs[61:]   # ohne Kinnstück keine Naht unter dem Kinn
	g.zug(r, gs, 0.006, saum, flach=0.7)
	teile.append(r.objekt())
	return teile, f, weit


# ---------------- Hammer: Ritterhelm (Armet) mit Sehschlitz


def kappe(K, material="leder", A=0.012, s_bis=1.2, extra=None, name="kappe", d=0.004, f=None):
	f = f or ir.kopf_feld(K)
	t = g.Teil(name)
	g.platte(t, f, 0.0, s_bis, A, nu=24, nw=96, material_name=material, extra=extra)
	return obj(t, 50, d), f


def unterarm(K, seite, A=0.016, glocke=0.016, von_zus=0.05, bis_zus=0.045, material="platte"):
	"""Unterarmröhre mit glockenförmiger Stulpe (aus dem schweren Satz)."""
	fa, l_ober, l_ges = ir.arm_feld(K, seite)
	von, bis = l_ober + von_zus, l_ges - bis_zus
	teile = [blech("unterarm", fa, von, bis, A, nu=16, nw=48, material_name=material)]
	r = g.Teil("unterarm_rand")
	for s in (von, bis):
		ring(r, fa, s, A, n=64)
	gl = lambda s, w: glocke * g.weich(s, l_ges - 0.06, l_ges + 0.01)
	teile.append(blech("stulpe", fa, l_ges - 0.065, l_ges + 0.012, A + 0.004, nu=10, nw=48, extra=gl, material_name=material))
	ring(r, fa, l_ges + 0.012, A + 0.004, n=64, extra=gl)
	teile.append(r.objekt())
	return teile


def hand_feld(K, seite):
	n = "Left" if seite > 0 else "Right"
	h0 = K.gelenk(n + "Hand")
	mf = K.gelenk(n + "MiddleProximal")
	ha = g.Achse([h0, mf + (mf - h0).normalized() * 0.01])
	hf = g.Feld(K.bvh([n + x for x in ir.HAND], 0.4), ha, ringe=20, seg=48, r_max=0.12, konvex_anteil=1.0, glatt=(2, 2))
	return hf, ir._handruecken_winkel(K, seite, ha)


def faeustling(K, seite, material="leder_dunkel", abstand=0.009, stulpe=0.08):
	"""Fausthandschuh: Hand aufgeblasen, Loch am Handgelenk geschlossen, per Voxel zu einem Stück verschmolzen."""
	n = "Left" if seite > 0 else "Right"
	h = K.gelenk(n + "Hand")
	e = K.gelenk(n + "LowerArm")
	d = (h - e).normalized()
	namen = [n + x for x in ir.HAND] + [n + "LowerArm"]
	ob = g.huelle_aus_koerper(K, namen, 0.5, abstand, "faeustling", material, behalten=lambda p: (p - h).dot(d) > -stulpe - 0.02)
	bm = bmesh.new()
	bm.from_mesh(ob.data)
	bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
	bm.to_mesh(ob.data)
	bm.free()
	g.anwenden(ob, "REMESH", mode="VOXEL", voxel_size=0.0045)
	g.anwenden(ob, "SMOOTH", factor=0.6, iterations=3)
	g.schneiden(ob, h - d * stulpe, -d)
	g.material_setzen(ob, material)
	g.verringern(ob, 3000)
	g.glatt(ob, 70)
	g.dicke(ob, 0.002, -1.0)
	return ob


def fingerlos(K, seite, material="leder", abstand=0.0028, stulpe=0.05):
	"""Handschuh ohne Fingerkuppen: nur Handfläche und erste Fingerglieder."""
	n = "Left" if seite > 0 else "Right"
	h = K.gelenk(n + "Hand")
	e = K.gelenk(n + "LowerArm")
	d = (h - e).normalized()
	namen = [n + "Hand", n + "LowerArm", n + "ThumbMetacarpal"] + [n + f + "Proximal" for f in ("Index", "Middle", "Ring", "Little", "Thumb")]
	ob = g.huelle_aus_koerper(K, namen, 0.5, abstand, "fingerlos", material, behalten=lambda p: (p - h).dot(d) > -stulpe)
	g.schneiden(ob, h - d * stulpe, -d)
	g.dicke(ob, 0.002, -1.0)
	return ob


def wickel(r, feld, von, bis, A, n=9, material="stoff", breite=0.011, neigung=0.012, seg=48):
	for k in range(n):
		s = von + (bis - von) * k / max(1, n - 1)
		pts, zu = g.rand_punkte(feld, lambda w, s=s: s + neigung * math.sin(w), A, n=seg)
		g.zug(r, pts, breite, material, zu=zu, flach=0.3)


def schnuerung(r, feld, von, bis, A, w0=0.0, spalt=0.07, n=6, material="leder_dunkel"):
	for k in range(n):
		s = von + (bis - von) * k / max(1, n - 1)
		d = (bis - von) / max(1, n - 1) * 0.6
		g.zug(r, [feld.punkt(s, w0 - spalt, A), feld.punkt(s + d, w0 + spalt, A)], 0.0018, material)
		g.zug(r, [feld.punkt(s, w0 + spalt, A), feld.punkt(s + d, w0 - spalt, A)], 0.0018, material)


def umschlag(K, seite, hoehe, A=0.024, material="leder", breite=0.045, weite=0.0):
	fb, l_knie, l_ges = ir.bein_feld(K, seite)
	s_oben = l_ges - hoehe - 0.03
	u = g.Teil("umschlag")
	g.platte(u, fb, s_oben + 0.005, s_oben + breite, lambda s, w: A + weite * g.weich(-s, -(s_oben + breite), -s_oben),
		nu=5, nw=56, material_name=material)
	return obj(u, 50, 0.004)


def kniekachel(K, seite, A=0.016, breite=1.4, material="platte"):
	fb, l_knie, l_ges = ir.bein_feld(K, seite)
	buckel = lambda s, w: 0.02 * math.exp(-((s - l_knie) / 0.035) ** 2) * math.cos(min(g.wdiff(w, 0), PI / 2)) ** 2
	o = blech("knie", fb, l_knie - 0.06, l_knie + 0.055, A, nu=14, nw=28, w_von=-breite, w_bis=breite, extra=buckel,
		material_name=material)
	r = g.Teil("knie_rand")
	for s in (l_knie - 0.06, l_knie + 0.055):
		ring(r, fb, s, A, 0.0035, w_von=-breite, w_bis=breite, n=28, extra=buckel)
	for s in (l_knie - 0.035, l_knie + 0.035):
		pts, _ = g.rand_punkte(fb, s, A - 0.007, w_von=breite, w_bis=2 * PI - breite, n=24)
		g.zug(r, pts, 0.006, "leder_dunkel", flach=0.35, aussen=lambda p: Vector((0, 1, 0)))
	return [o, r.objekt()]


def schienbein(K, seite, A=0.019, breite=0.8, material="platte", hoch=0.27):
	fb, l_knie, l_ges = ir.bein_feld(K, seite)
	grat = lambda s, w: 0.005 * math.exp(-(g.wdiff(w, 0) / 0.2) ** 2)
	o = blech("schienbein", fb, l_ges - hoch, l_ges - 0.08, A, nu=12, nw=14, w_von=-breite, w_bis=breite, extra=grat,
		material_name=material)
	r = g.Teil("riemen")
	for s in (l_ges - hoch + 0.03, l_ges - 0.11):
		pts, _ = g.rand_punkte(fb, s, A, w_von=breite, w_bis=2 * PI - breite, n=40)
		g.zug(r, pts, 0.007, "leder_dunkel", flach=0.35)
		g.nieten_reihe(r, fb, s, A + 0.001, [-breite + 0.2, breite - 0.2], 0.0045)
	return [o, r.objekt()]


def brustplatte_vorne(K, A=0.035, unten_z=None, name="brustplatte"):
	"""Einzelnes Bruststück mit Riemen (für leichte und mittlere Sätze)."""
	f = ir.rumpf_feld(K)
	oben = tabelle([(0, 0.64), (0.4, 0.69), (0.8, 0.66), (1.3, 0.55), (1.75, 0.5)])
	uz = (unten_z or 1.03) - Z0
	unten = tabelle([(0, uz), (0.8, uz + 0.01), (1.75, uz + 0.03)])
	grat = lambda s, w: 0.01 * math.exp(-(g.wdiff(w, 0) / 0.22) ** 2) * g.weich(s, 0.2, 0.45)
	t = g.Teil(name)
	g.platte(t, f, unten, oben, A, nu=30, nw=56, extra=grat, w_von=-1.75, w_bis=1.75)
	teile = [obj(t, 30, 0.003)]
	r = g.Teil("brustplatte_rand")
	pts, _ = g.rand_punkte(f, oben, A + 0.002, w_von=-1.75, w_bis=1.75, n=80, extra=grat)
	g.zug(r, pts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, unten, A, w_von=-1.75, w_bis=1.75, n=80, extra=grat)
	g.zug(r, pts, 0.004, "rand")
	for z in (0.30, 0.52):
		pts, _ = g.rand_punkte(f, z, A - 0.012, w_von=1.65, w_bis=2 * PI - 1.65, n=40)
		g.zug(r, pts, 0.011, "leder_dunkel", flach=0.3)
	g.nieten_reihe(r, f, lambda w: unten(w) + 0.015, A, [-1.4, -0.7, 0.7, 1.4], 0.005, extra=grat)
	teile.append(r.objekt())
	return teile, f


def vernietet(K, A=0.024, material="leder", unten_z=0.94, name="brigantine", nieten=True, kragen=True, offen=0.0):
	"""Brigantine/Lederkoller auf dem Rumpf: Weste mit Nietenraster, ohne Ärmel."""
	f = ir.rumpf_feld(K, glatt=(4, 3), konvex=0.9)
	oben = tabelle([(0, 0.63), (0.35, 0.67), (0.7, 0.69), (1.15, 0.54), (1.57, 0.5), (2.0, 0.54),
		(2.4, 0.69), (2.8, 0.71), (PI, 0.72)])
	uz = unten_z - Z0
	unten = tabelle([(0, uz), (PI / 2, uz + 0.02), (PI, uz + 0.01)])
	weite = lambda s, w: 0.012 * g.weich(-s, -0.2, -0.0)
	t = g.Teil(name)
	g.platte(t, f, unten, oben, lambda s, w: A + weite(s, w), nu=40, nw=96, material_name=material,
		w_von=offen, w_bis=2 * PI - offen)
	teile = [obj(t, 50, 0.005)]
	r = g.Teil(name + "_rand")
	for fn in (oben, unten):
		pts, zu = g.rand_punkte(f, fn, A + 0.002, n=120, extra=weite, w_von=offen, w_bis=2 * PI - offen)
		g.zug(r, pts, 0.0035, "leder_dunkel", zu=zu, flach=0.6)
	if nieten:
		for k in range(9):
			s = uz + 0.035 + k * 0.058
			ws = [w for w in np.linspace(0, 2 * PI, 40, endpoint=False) + (0.08 if k % 2 else 0.0)
				if s < oben(w) - 0.03 and g.wdiff(w, 0) > offen + 0.05]
			g.nieten_reihe(r, f, s, A + 0.001, ws, 0.0055, extra=weite)
	teile.append(r.objekt())
	return teile, f


def pelzrand(r, pts, zu=True, radius=0.022):
	g.zug(r, pts, radius, "fell", zu=zu, seg=10, flach=0.8)


# ================================================================ SCHWER


# ---------------- Schwert und Schild: Ritter


def sus_kopf(K):
	"""Topfhelm mit Sehschlitz und Kreuz, Atemlöcher."""
	f = ir.kopf_feld(K)
	ab, H, R = topf_flaeche(f, 0.02, rund=0.012)
	unten = lambda w: 2.28 - 0.05 * math.cos(g.wdiff(w, PI) / 2) ** 2
	teile = [blech("topfhelm", f, 0.0, unten, ab, d=0.003, nu=48, nw=96)]
	r = g.Teil("helm_rand")
	pts, zu = g.rand_punkte(f, unten, ab, n=96)
	g.zug(r, pts, 0.005, "rand", zu=zu)
	# Deckelkante
	ring(r, f, 0.62, lambda s, w: ab(s, w) + 0.001, 0.003, n=96)
	# Sehschlitze (dunkel) links und rechts vom Kreuz
	for sg in (1, -1):
		for ds in (-0.025, 0.025):
			pts = [f.punkt(1.24 + ds, sg * w, ab(1.24 + ds, sg * w) + 0.0015) for w in np.linspace(0.12, 0.95, 20)]
			g.zug(r, pts, 0.0035, "rand", flach=0.6)
		pts = [f.punkt(1.24, sg * w, ab(1.24, sg * w) + 0.0005) for w in np.linspace(0.14, 0.93, 20)]
		g.zug(r, pts, 0.008, "stoff_dunkel", flach=0.25, aussen=lambda p: (p - f.c).normalized())
	# Kreuz: senkrechte Leiste und Querleiste unter dem Schlitz
	pts = [f.punkt(s, 0.0, ab(s, 0.0) + 0.003) for s in np.linspace(0.75, 2.2, 30)]
	g.zug(r, pts, 0.011, "platte", flach=0.35, aussen=lambda p: (p - f.c).normalized())
	pts = [f.punkt(1.42, w, ab(1.42, w) + 0.003) for w in np.linspace(-0.85, 0.85, 30)]
	g.zug(r, pts, 0.009, "platte", flach=0.35, aussen=lambda p: (p - f.c).normalized())
	for sg in (1, -1):
		for i in range(4):
			for j in range(3):
				s, w = 1.62 + 0.08 * i, sg * (0.22 + 0.11 * j)
				g.niete(r, f.punkt(s, w, ab(s, w) + 0.0004), f.normale(s, w, ab(s, w)), 0.004, "stoff_dunkel")
	for k in range(24):
		w = 2 * PI * k / 24
		g.niete(r, f.punkt(unten(w) - 0.05, w, ab(unten(w) - 0.05, w) + 0.001), f.normale(unten(w) - 0.05, w, ab(unten(w) - 0.05, w)), 0.0045)
	teile.append(r.objekt())
	return g.vereinen(teile, "iron_sword_shield_kopf")


def sus_brust(K):
	ob = ir.schwer_brust(K, fauld=3, name="h")
	wr, f = tabard(K, unten_z=0.50, A=0.072)
	# Kreuz vorne auf dem Wappenrock
	r = g.Teil("kreuz")
	A = 0.072
	fl = lambda s: 0.02 * g.weich(-s, -(0.85 - ZW), -0.0)
	pts = [f.punkt(s, 0.0, A + fl(s) + 0.006) for s in np.linspace(1.02 - ZW, 1.40 - ZW, 24)]
	blatt(r, pts, lambda u: 0.035, lambda p: (p - f.achse.punkt(p.z - ZW)).normalized(), "futter")
	pts = [f.punkt(1.27 - ZW, w, A + fl(1.27 - ZW) + 0.007) for w in np.linspace(-0.45, 0.45, 24)]
	blatt(r, pts, lambda u: 0.035, lambda p: (p - f.achse.punkt(p.z - ZW)).normalized(), "futter")
	gu = ir.guertel(K, 0.97, 0.05, 0.085)
	return g.vereinen([ob] + wr + [r.objekt()] + gu, "x")


def sus_beine(K):
	ob = ir.schwer_beine(K)
	# Kettenschurz unter den Bauchreifen
	f = ir.wams_feld(K)
	t = g.Teil("kettenschurz")
	g.platte(t, f, 0.70 - ZW, 0.92 - ZW, lambda s, w: 0.022 + 0.03 * g.weich(-s, -(0.86 - ZW), -(0.70 - ZW)), nu=20, nw=96,
		material_name="kette")
	return g.vereinen([ob, obj(t, 60, 0.003)], "x")


# ---------------- Hammer: Brecher


def hammer_kopf(K):
	f = ir.kopf_feld(K)
	A = 0.026
	kamm = lambda s, w: 0.008 * math.exp(-(math.sin(w) * math.sin(s) / 0.05) ** 2) * g.weich(-s, -1.6, -0.6)
	spalt_o, spalt_u = AUGE_S - 0.045, AUGE_S + 0.05
	# Glocke: vorne bis über die Augen, hinten und seitlich bis in den Nacken
	unten = lambda w: spalt_o + (2.4 - spalt_o) * g.weich(g.wdiff(w, 0), 1.15, 1.55)
	teile = [blech("glocke", f, 0.0, unten, lambda s, w: A + kamm(s, w), d=0.003, nu=44, nw=96)]
	r = g.Teil("rand")
	ring(r, f, unten, lambda s, w: A + kamm(s, w), 0.005, n=120)
	# Visier mit spitzer Schnauze (Spatzenschnabel)
	schn = lambda s, w: 0.055 * math.exp(-g.wdiff(w, 0) / 0.42) * math.exp(-((s - 2.02) / 0.3) ** 2)
	vis = lambda s, w: A + 0.008 + schn(s, w)
	vu = lambda w: 2.42
	teile.append(blech("visier", f, spalt_u, vu, vis, d=0.003, nu=30, nw=48, w_von=-1.45, w_bis=1.45))
	for fn in (spalt_u, vu):
		pts, _ = g.rand_punkte(f, fn, vis, w_von=-1.45, w_bis=1.45, n=60)
		g.zug(r, pts, 0.0045, "rand")
	pts = [f.punkt(s, w, vis(s, w)) for s, w in zip(np.linspace(spalt_u, 2.42, 24), [1.45] * 24)]
	g.zug(r, pts, 0.004, "rand")
	pts = [f.punkt(s, w, vis(s, w)) for s, w in zip(np.linspace(spalt_u, 2.42, 24), [-1.45] * 24)]
	g.zug(r, pts, 0.004, "rand")
	# Dunkler Grund im Sehschlitz
	pts = [f.punkt(AUGE_S, w, A - 0.008) for w in np.linspace(-1.2, 1.2, 40)]
	g.zug(r, pts, 0.03, "stoff_dunkel", flach=0.12, aussen=lambda p: (p - f.c).normalized())
	# Atemschlitze auf beiden Seiten der Schnauze
	for sg in (1, -1):
		for i in range(4):
			s = 1.92 + 0.07 * i
			pts = [f.punkt(s, sg * w, vis(s, sg * w) + 0.0008) for w in np.linspace(0.32, 0.62, 8)]
			g.zug(r, pts, 0.004, "stoff_dunkel", flach=0.4, aussen=lambda p: (p - f.c).normalized())
		g.niete(r, f.punkt(AUGE_S, sg * PI / 2, A + 0.012), f.normale(AUGE_S, sg * PI / 2, A + 0.012), 0.011)
	# Halsreifen
	for k in range(2):
		s0 = 2.36 + 0.06 * k
		teile.append(blech("halsreif", f, s0, s0 + 0.08, A + 0.01 + 0.006 * k, d=0.0025, nu=4, nw=96))
		ring(r, f, s0, A + 0.01 + 0.006 * k, 0.003, n=96)
	for k in range(14):
		w = PI / 2 + PI * k / 13
		s = unten(w) - 0.08
		if s > 2.0:
			g.niete(r, f.punkt(s, w, A + 0.001), f.normale(s, w, A), 0.0045)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Axt: Nordkrieger, grob und spitz


def hammer_brust(K):
	return ir.schwer_brust(K, riffel=7, fauld=4, unter=dict(material="kette", unten_z=0.62, weite=0.06, abstand=0.012,
		aermel_bis=0.55, aermel_abstand=0.01, steppung=0.0), name="x")


def hammer_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(faeustling(K, seite, "leder_dunkel", 0.009, 0.09))
		teile += unterarm(K, seite, 0.018, 0.022)
		hf, rw = hand_feld(K, seite)
		r = g.Teil("rand")
		for k in range(4):
			a0 = 0.0 + 0.026 * k
			teile.append(blech("handplatte", hf, a0, a0 + 0.034, 0.016 + 0.002 * k, nu=4, nw=16, w_von=rw - 1.25,
				w_bis=rw + 1.25))
			ring(r, hf, a0, 0.016 + 0.002 * k, 0.0025, w_von=rw - 1.25, w_bis=rw + 1.25, n=16)
		# Knöchelleiste mit Buckeln
		s = hf.achse.laenge() + 0.0
		for k in range(5):
			w = rw - 0.9 + 1.8 * k / 4
			g.niete(r, hf.punkt(s - 0.005, w, 0.024), hf.normale(s - 0.005, w, 0.024), 0.007)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def hammer_beine(K):
	ob = ir.schwer_beine(K, "leder_dunkel")
	teile = [ob]
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		# zusätzliche, dicke Kniebuckel
		r = g.Teil("buckel")
		g.niete(r, fb.punkt(l_knie, 0.0, 0.045), fb.normale(l_knie, 0.0, 0.045), 0.022)
		teile.append(r.objekt())
	f = ir.wams_feld(K)
	t = g.Teil("kettenschurz")
	g.platte(t, f, 0.66 - ZW, 0.92 - ZW, lambda s, w: 0.024 + 0.035 * g.weich(-s, -(0.86 - ZW), -(0.66 - ZW)), nu=20,
		nw=96, material_name="kette")
	teile.append(obj(t, 60, 0.003))
	return g.vereinen(teile, "x")


def hammer_fuesse(K):
	ob = ir.schwer_fuesse(K)
	teile = [ob]
	for seite in (1, -1):
		# breite Schienbeinplatte über dem Knöchelring
		teile += schienbein(K, seite, 0.022, 1.1, hoch=0.24)
	return g.vereinen(teile, "x")


# ---------------- Axt: Nordkrieger (M/S/M/S/M)


def axe_kopf(K):
	"""Brillenhelm: Kappe mit Grat, Augenbrille genau über den Augen, langes Nasal, Kettenbehang."""
	f = ir.kopf_feld(K)
	A = 0.026
	spitze = lambda s, w: 0.03 * max(0.0, 1 - s / 0.7) ** 1.5 + 0.006 * math.exp(-(math.sin(w) * math.sin(s) / 0.04) ** 2)
	unten = 1.55
	teile = [blech("kappe", f, 0.0, unten, lambda s, w: A + spitze(s, w), d=0.003, nu=34, nw=96)]
	r = g.Teil("rand")
	pts, zu = g.rand_punkte(f, unten, lambda s, w: A + spitze(s, w), n=96)
	g.zug(r, pts, 0.009, "rand", zu=zu, flach=0.4)
	for k in range(4):
		w = k * PI / 2 + PI / 4
		pts = [f.punkt(unten * (1 - j / 16), w, A + spitze(unten * (1 - j / 16), w) + 0.001) for j in range(17)]
		g.zug(r, pts, 0.009, "rand", flach=0.3, aussen=lambda p: (p - f.c).normalized())
	for k in range(16):
		w = 2 * PI * k / 16
		g.niete(r, f.punkt(unten - 0.05, w, A + 0.002), f.normale(unten - 0.05, w, A), 0.0055)
	# Brille: Ringe um die Augen, Nasal bis über die Nase
	br = g.Teil("brille")
	for sg in (1, -1):
		pts = []
		for k in range(40):
			a = 2 * PI * k / 40
			s = AUGE_S + 0.11 * math.sin(a)
			w = sg * AUGE_W + 0.3 * math.cos(a)
			if s < unten:
				s = unten - 0.005
			pts.append(f.punkt(s, w, A + 0.012 + 0.012 * g.weich(s, unten, AUGE_S + 0.1)))
		g.zug(br, pts, 0.014, "platte", flach=0.25, aussen=lambda p: (p - f.c).normalized(), zu=True)
	nas = [f.punkt(s, 0.0, A + 0.008 + 0.02 * g.weich(s, 1.6, 1.95)) for s in np.linspace(unten - 0.05, 1.98, 16)]
	g.zug(br, nas, 0.016, "platte", flach=0.25, aussen=lambda p: (p - f.c).normalized())
	teile.append(br.objekt())
	# Kettenbehang hinten und seitlich bis auf die Schultern
	kt = g.Teil("behang")
	g.platte(kt, f, unten + 0.01, 2.48, lambda s, w: 0.018 + 0.025 * g.weich(s, 1.9, 2.45), nu=26, nw=60,
		w_von=1.15, w_bis=2 * PI - 1.15, material_name="kette")
	teile.append(obj(kt, 60, 0.003))
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def axe_brust(K):
	ob = ir.schwer_brust(K, fauld=2, unter=dict(material="kette", unten_z=0.64, weite=0.05, abstand=0.012,
		aermel_bis=0.8, aermel_abstand=0.009), name="x", halsberge=False)
	teile = [ob]
	r = g.Teil("dornen")
	for seite in (1, -1):
		teile += _grobe_schulter(K, seite, r)
	# Brustgrat mit Dornreihe und Stachel am Brustbein
	f = ir.rumpf_feld(K)
	for s in (0.42, 0.5):
		stachel(r, f.punkt(s, 0.0, 0.04), f.normale(s, 0.0, 0.04), 0.025, 0.008)
	# Fellumhang über Rücken und Schultern
	fw = ir.wams_feld(K)
	oben = tabelle([(0, 0.0), (1.3, 0.66), (PI / 2, 0.69), (PI, 0.68)])
	fell = lambda s, w: 0.085 + 0.04 * g.weich(-s, -(1.2 - ZW), -(0.7 - ZW)) + 0.003 * math.sin(w * 17 + s * 41 + math.sin(w * 7) * 3)
	t = g.Teil("umhang")
	g.platte(t, fw, lambda w: 0.62 - ZW + 0.04 * math.sin(w * 5), lambda w: oben(w) + 0.795 - ZW, fell, nu=50, nw=60,
		w_von=1.35, w_bis=2 * PI - 1.35, material_name="fell")
	teile.append(obj(t, 60, 0.008))
	pts, zu = g.rand_punkte(fw, lambda w: 1.47 - ZW, lambda s, w: 0.085, n=60, w_von=1.25, w_bis=2 * PI - 1.25)
	pelzrand(r, pts, False, 0.034)
	# Tuch vorne und hinten unter dem Gürtel, Beintaschen (Tassetten) darüber
	for mitte in (0.0, PI):
		tt = g.Teil("tuch")
		g.platte(tt, fw, lambda w: 0.52 - ZW + 0.015 * math.sin(w * 13), 0.95 - ZW, 0.06, nu=24, nw=20,
			w_von=mitte - 0.42, w_bis=mitte + 0.42, material_name="leder")
		teile.append(obj(tt, 60, 0.004))
	for sg in (1, -1):
		w0 = sg * 0.95
		tas = lambda s, w: 0.075 + 0.02 * g.weich(-s, -(0.9 - ZW), -(0.66 - ZW))
		teile.append(blech("tassette", fw, 0.66 - ZW, 0.94 - ZW, tas, d=0.0035, nu=12, nw=16, w_von=w0 - 0.5, w_bis=w0 + 0.5))
		pts, _ = g.rand_punkte(fw, 0.66 - ZW, tas, w_von=w0 - 0.5, w_bis=w0 + 0.5, n=16)
		g.zug(r, pts, 0.005, "rand")
		stachel(r, fw.punkt(0.72 - ZW, w0, tas(0.72 - ZW, w0)), fw.normale(0.72 - ZW, w0, 0.08) + Vector((0, 0, -0.5)), 0.03, 0.009)
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.97, 0.07, 0.07, "leder")
	return g.vereinen(teile, "x")


def axe_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder", 0.003, 0.05))
		teile += unterarm(K, seite, 0.014, 0.024, von_zus=0.12, bis_zus=0.05)
		fa, l_ober, l_ges = ir.arm_feld(K, seite)
		r = g.Teil("wickel")
		wickel(r, fa, l_ober + 0.02, l_ober + 0.1, 0.01, n=3, material="leder_dunkel", breite=0.01)
		aussen = 3 * PI / 2 if seite > 0 else PI / 2
		for s in (l_ober + 0.16, l_ober + 0.21):
			stachel(r, fa.punkt(s, aussen, 0.018), fa.normale(s, aussen, 0.018), 0.025, 0.008)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Großschwert: Söldner aus Leder und Kette (nach den Vorlagen)


def axe_beine(K):
	ob = ir.schwer_beine(K, "leder_dunkel")
	teile = [ob]
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("dorn")
		stachel(r, fb.punkt(l_knie, 0.0, 0.04), fb.normale(l_knie, 0.0, 0.04), 0.045, 0.014)
		for k in range(3):
			s = 0.06 + 0.03 * k
			pts, zu = g.rand_punkte(fb, s, 0.012, n=40)
			g.zug(r, pts, 0.006, "leder", zu=zu, flach=0.3)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def axe_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.009, 0.24))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("fell")
		pts, zu = g.rand_punkte(fb, l_ges - 0.27, 0.02, n=48)
		pelzrand(r, pts, zu, 0.017)
		wickel(r, fb, l_ges - 0.2, l_ges - 0.06, 0.014, n=4, material="leder_dunkel", breite=0.008, neigung=0.02)
		teile.append(r.objekt())
		ff = ir.fuss_feld(K, seite)
		L = ff.achse.laenge()
		teile.append(blech("kappe", ff, L - 0.06, L, 0.016, nu=8, nw=24, w_von=-1.5, w_bis=1.5))
	return g.vereinen(teile, "x")


# ---------------- Leerenmagie: Kampfmagier (M/S/M/S/M)


def void_kopf(K):
	"""Tiefe Kapuze mit Halbmaske aus Eisen vor Mund und Kinn."""
	teile, f, weit = kapuze(K, "stoff_dunkel", A=0.028, gesicht=0.85, tief=0.04, saum="rand",
		kragen_unten=tabelle([(0, 0.52), (0.9, 0.55), (PI / 2, 0.55), (PI, 0.48)]))
	A = 0.018
	mo = lambda w: AUGE_S + 0.13 + 0.1 * (g.wdiff(w, 0) / 1.2) ** 2
	maske = lambda s, w: A + 0.012 * math.exp(-(g.wdiff(w, 0) / 0.5) ** 2) * g.weich(s, 1.5, 1.8)
	teile.append(blech("maske", f, mo, 2.36, maske, d=0.0025, nu=20, nw=40, w_von=-1.15, w_bis=1.15))
	r = g.Teil("rand")
	pts, _ = g.rand_punkte(f, mo, maske, w_von=-1.15, w_bis=1.15, n=40)
	g.zug(r, pts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, 2.36, maske, w_von=-1.15, w_bis=1.15, n=40)
	g.zug(r, pts, 0.004, "rand")
	# Luftschlitze
	for k in range(5):
		w = -0.4 + 0.2 * k
		pts = [f.punkt(s, w, maske(s, w) + 0.0008) for s in np.linspace(1.72, 1.95, 8)]
		g.zug(r, pts, 0.004, "stoff_dunkel", flach=0.3, aussen=lambda p: (p - f.c).normalized())
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def void_brust(K):
	ob = ir.schwer_brust(K, fauld=2, arme=True, halsberge=True, unter=dict(material="stoff_dunkel", unten_z=0.86,
		aermel_bis=1.0, steppung=0.0), name="x")
	teile = [ob]
	# kurzer, vorne offener Mantel hinter der Platte (Schöße bis zum Knie)
	f = ir.wams_feld(K)
	t = g.Teil("mantel")
	flare = lambda s, w: 0.075 + 0.05 * g.weich(-s, -(0.95 - ZW), -(0.5 - ZW))
	g.platte(t, f, lambda w: 0.52 - ZW + 0.1 * math.cos(g.wdiff(w, PI) / 2) ** 2 * 0, 1.0 - ZW, flare, nu=40, nw=72,
		w_von=0.55, w_bis=2 * PI - 0.55, material_name="stoff_dunkel")
	teile.append(obj(t, 60, 0.004))
	r = g.Teil("saum")
	pts, _ = g.rand_punkte(f, 0.52 - ZW, lambda s, w: flare(s, w) + 0.003, w_von=0.55, w_bis=2 * PI - 0.55, n=72)
	g.zug(r, pts, 0.005, "rand", flach=0.5)
	for w in (0.55, 2 * PI - 0.55):
		pts = [f.punkt(s, w, flare(s, w) + 0.003) for s in np.linspace(0.52 - ZW, 1.0 - ZW, 20)]
		g.zug(r, pts, 0.005, "rand", flach=0.5)
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.97, 0.05, 0.085)
	return g.vereinen(teile, "x")


def void_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder_dunkel", 0.003, 0.05))
		teile += ir.armschiene_leder(K, seite, 0.011, True)
		hf, rw = hand_feld(K, seite)
		teile.append(blech("handplatte", hf, 0.012, hf.achse.laenge() - 0.005, 0.008, d=0.002, nu=6, nw=14,
			w_von=rw - 1.0, w_bis=rw + 1.0))
	return g.vereinen(teile, "x")


def void_beine(K):
	return ir.schwer_beine(K, "stoff_dunkel", name="x")


def void_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.009, 0.30))
		teile += schienbein(K, seite, 0.019, 0.85, hoch=0.29)
		ff = ir.fuss_feld(K, seite)
		L = ff.achse.laenge()
		teile.append(blech("kappe", ff, L - 0.07, L, 0.016, nu=8, nw=24, w_von=-1.6, w_bis=1.6))
	return g.vereinen(teile, "x")


# ================================================================ MITTEL


def steppnaht(abstand=0.05, tiefe=0.003):
	"""bein_extra für gesteppte Hosen: waagrechte Nähte."""
	return lambda s, w, lk, lg: -tiefe * (1 - abs(math.cos(s * PI / abstand))) ** 6


def stulpenhandschuh(K, seite, material="leder", glocke=0.026, laenge=0.12, platte=False):
	teile = [ir.handschuh(K, seite, material, 0.0028, 0.05)]
	fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.8)
	gl = lambda s, w: glocke * g.weich(-s, -(l_ges - 0.02), -(l_ges - laenge))
	st = g.Teil("stulpe")
	g.platte(st, fa, l_ges - laenge - 0.01, l_ges - 0.015, lambda s, w: 0.009 + gl(s, w), nu=10, nw=48, material_name=material)
	teile.append(obj(st, 50, 0.003))
	r = g.Teil("naht")
	ring(r, fa, l_ges - laenge - 0.01, 0.009, 0.003, "leder_dunkel", flach=0.6, n=48, extra=gl)
	if platte:
		hf, rw = hand_feld(K, seite)
		teile.append(blech("handplatte", hf, 0.012, hf.achse.laenge() - 0.005, 0.008, d=0.002, nu=6, nw=14,
			w_von=rw - 1.0, w_bis=rw + 1.0))
	teile.append(r.objekt())
	return teile


# ---------------- Großschwert: Söldner


def greatsword_kopf(K):
	"""Kettenhaube mit Lederkappe und Lederband."""
	f = ir.kopf_feld(K)
	A = 0.012
	t = g.Teil("kettenhaube")
	g.platte(t, f, 0.0, 1.45, A, nu=24, nw=96, material_name="kette")
	g.platte(t, f, 1.45, 2.45, A, nu=26, nw=60, w_von=0.9, w_bis=2 * PI - 0.9, material_name="kette")
	g.platte(t, f, 2.18, 2.45, A, nu=8, nw=24, w_von=-0.92, w_bis=0.92, material_name="kette")
	teile = [obj(t, 60, 0.003)]
	fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	kt = g.Teil("kettenkragen")
	flare = lambda s, w: 0.02 * g.weich(-s, -0.66, -0.56)
	ku = tabelle([(0, 0.58), (0.9, 0.62), (PI / 2, 0.6), (2.3, 0.62), (PI, 0.59)])
	g.platte(kt, fr, ku, 0.78, 0.014, nu=16, nw=96, extra=flare, material_name="kette")
	teile.append(obj(kt, 60, 0.003))
	r = g.Teil("leder")
	pts, zu = g.rand_punkte(fr, ku, 0.014, n=120, extra=flare)
	g.zug(r, pts, 0.004, "leder", zu=zu, flach=0.5)
	gs = [f.punkt(s, -0.9, A + 0.002) for s in np.linspace(2.18, 1.45, 20)] + \
		[f.punkt(1.45, w, A + 0.002) for w in np.linspace(-0.9, 0.9, 20)[1:-1]] + \
		[f.punkt(s, 0.9, A + 0.002) for s in np.linspace(1.45, 2.18, 20)]
	g.zug(r, gs, 0.005, "leder", flach=0.6)
	# Lederkappe mit vier Nähten und Stirnband
	kp = g.Teil("lederkappe")
	g.platte(kp, f, 0.0, 1.25, 0.024, nu=20, nw=96, material_name="leder_dunkel")
	teile.append(obj(kp, 50, 0.005))
	ring(r, f, 1.25, 0.026, 0.009, "leder", flach=0.4, n=96)
	for k in range(4):
		w = k * PI / 2 + PI / 4
		pts = [f.punkt(s, w, 0.0245) for s in np.linspace(0.05, 1.22, 14)]
		g.zug(r, pts, 0.003, "leder", flach=0.5)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def greatsword_brust(K):
	# Gesteppter Waffenrock mit langem Schoß, darüber Kettenhemd
	teile, fw = ir.wams(K, "stoff", 0.008, unten_z=0.52, kragen_z=1.53, aermel_bis=1.0, steppung=0.005, weite=0.06,
		aermel_abstand=0.007)
	kette, _ = ir.wams(K, "kette", 0.016, unten_z=0.74, kragen_z=1.5, aermel_bis=0.45, weite=0.05, aermel_abstand=0.012,
		name="kettenhemd")
	teile += kette
	# Lederkürass vorne und hinten mit Kragen
	b, f = vernietet(K, 0.036, "leder_dunkel", unten_z=0.93, nieten=False)
	teile += b
	r = g.Teil("riemen")
	# Kreuzriemen auf der Brust (wie in der Vorlage), mit Schnallen
	for (s, w0, w1) in ((0.36, -0.55, 0.35), (0.3, -0.35, 0.55)):
		pts = [f.punkt(s + 0.08 * u, w0 + (w1 - w0) * u, 0.04) for u in np.linspace(0, 1, 12)]
		g.zug(r, pts, 0.012, "leder", flach=0.25, aussen=lambda p: (p - f.achse.punkt(p.z - Z0)).normalized())
	for sg in (1, -1):
		g.niete(r, f.punkt(0.4, sg * 0.12, 0.045), f.normale(0.4, sg * 0.12, 0.04), 0.009, "rand")
	# Seitliche Schnallen
	for sg in (1, -1):
		for z in (0.25, 0.4):
			p = f.punkt(z, sg * 1.5, 0.042)
			g.zug(r, [p + Vector((0, 0.015, 0)), p + Vector((0, -0.015, 0))], 0.009, "leder", flach=0.3)
			g.niete(r, p, f.normale(z, sg * 1.5, 0.04), 0.007, "rand")
	# Stehkragen aus Leder
	kr = lambda s, w: 0.03 + 0.012 * g.weich(s, 0.76, 0.86)
	teile.append(blech("kragen", f, 0.74, lambda w: 0.86 - 0.03 * (1 - g.wdiff(w, 0) / PI), kr, d=0.006, nu=8, nw=80,
		w_von=0.45, w_bis=2 * PI - 0.45, material_name="leder"))
	# Schwertgehänge schräg über die Brust
	t, vorne, fr = schraeg_riemen(K, 0.05, 0.02, "leder", links_oben=False)
	teile.append(t.objekt())
	# Linke Schulter aus Eisen (mit Lamellen), rechte aus Leder
	teile += ir._schulter(K, 1)
	fs = ir.schulter_feld(K, -1)
	aussen = 3 * PI / 2
	bis = lambda w: 0.95 + 0.55 * (1 - (g.wdiff(w, aussen) / PI) ** 2)
	teile.append(blech("lederschulter", fs, 0.0, bis, 0.035, d=0.006, nu=20, nw=72, material_name="leder"))
	pts, zu = g.rand_punkte(fs, bis, 0.035, n=120)
	g.zug(r, pts, 0.004, "leder_dunkel", zu=zu, flach=0.6)
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.96, 0.055, 0.055)
	return g.vereinen(teile, "x")


def greatsword_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder_dunkel", 0.003, 0.05))
		teile += ir.armschiene_leder(K, seite, 0.012, True)
		hf, rw = hand_feld(K, seite)
		teile.append(blech("handplatte", hf, 0.012, hf.achse.laenge() - 0.005, 0.009, d=0.002, nu=6, nw=14,
			w_von=rw - 1.0, w_bis=rw + 1.0))
	return g.vereinen(teile, "x")


def greatsword_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		# Lederbeinschienen vom Knie bis zum Rist, mit Riemen und Schnallen (Vorlage Lederrüstung)
		teile.append(blech("lederschiene", fb, l_knie - 0.07, l_ges - 0.13, 0.024, d=0.006, nu=24, nw=28,
			w_von=-1.55, w_bis=1.55, material_name="leder_dunkel"))
		r = g.Teil("riemen")
		pts, _ = g.rand_punkte(fb, l_knie - 0.07, 0.025, w_von=-1.55, w_bis=1.55, n=28)
		g.zug(r, pts, 0.004, "leder", flach=0.6)
		for k in range(4):
			s = l_knie - 0.03 + (l_ges - 0.2 - l_knie) * k / 3
			ring(r, fb, s, 0.02, 0.007, "leder", flach=0.35, n=48)
			aussen = 3 * PI / 2 if seite > 0 else PI / 2
			g.niete(r, fb.punkt(s, aussen, 0.027), fb.normale(s, aussen, 0.027), 0.008, "rand")
		# Nieten auf der Schiene
		for k in range(5):
			s = l_knie + 0.02 + (l_ges - 0.2 - l_knie) * k / 4
			g.nieten_reihe(r, fb, s, 0.025, [-0.9, -0.3, 0.3, 0.9], 0.005)
		teile.append(r.objekt())
		teile += kniekachel(K, seite, 0.03, 1.3, "leder")
	return g.vereinen(teile, "x")


def greatsword_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.008, 0.13))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("riemen")
		ring(r, fb, l_ges - 0.08, 0.014, 0.006, "leder", flach=0.35, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Speer: korinthischer (spartanischer) Helm


# ---------------- Speer: Wachsoldat


def spear_kopf(K):
	f = ir.kopf_feld(K)
	A = 0.024
	auge_o, auge_u = AUGE_S - 0.1, AUGE_S + 0.09
	glocke = lambda s, w: A + 0.012 * g.weich(-s, -1.2, -0.3)
	# Wangenstücke schwingen nach vorne zum Kinn
	wange = lambda s, w: 0.012 * g.weich(s, 1.8, 2.3) * math.exp(-(g.wdiff(w, 0) / 1.0) ** 2)
	ab = lambda s, w: glocke(s, w) + wange(s, w)
	teile = []
	t = g.Teil("helm")
	g.platte(t, f, 0.0, auge_o, ab, nu=36, nw=96)
	# Augenhöhe: nur Nasal und Seiten
	g.platte(t, f, auge_o, auge_u, ab, nu=8, nw=60, w_von=0.72, w_bis=2 * PI - 0.72)
	g.platte(t, f, auge_o, 1.98, ab, nu=12, nw=6, w_von=-0.09, w_bis=0.09)
	# Wangen bis zum Kinn, vorne ein schmaler Spalt für Mund und Kinn
	unten = lambda w: 2.42 - 0.12 * math.exp(-(g.wdiff(w, PI) / 0.9) ** 2)
	g.platte(t, f, auge_u, unten, ab, nu=26, nw=72, w_von=0.2, w_bis=2 * PI - 0.2)
	teile.append(obj(t, 30, 0.003))
	r = g.Teil("rand")
	# Randwülste um die T-Öffnung
	kontur = [f.punkt(s, 0.2, ab(s, 0.2)) for s in np.linspace(2.4, auge_u, 16)]
	kontur += [f.punkt(auge_u, w, ab(auge_u, w)) for w in np.linspace(0.2, 0.72, 10)[1:]]
	kontur += [f.punkt(s, 0.72, ab(s, 0.72)) for s in np.linspace(auge_u, auge_o, 8)[1:]]
	kontur += [f.punkt(auge_o, w, ab(auge_o, w)) for w in np.linspace(0.72, 0.09, 12)[1:]]
	kontur += [f.punkt(s, 0.09, ab(s, 0.09)) for s in np.linspace(auge_o, 1.98, 12)[1:]]
	kontur += [f.punkt(1.98, w, ab(1.98, w)) for w in np.linspace(0.09, -0.09, 4)[1:]]
	links = kontur
	rechts = []
	for p in reversed(kontur[:-3]):
		q = p.copy()
		q.x = -q.x
		rechts.append(q)
	g.zug(r, links + rechts, 0.004, "rand")
	pts, _ = g.rand_punkte(f, unten, ab, w_von=0.2, w_bis=2 * PI - 0.2, n=96)
	g.zug(r, pts, 0.005, "rand")
	# Helmbusch: Kamm aus Rosshaar von der Stirn bis in den Nacken
	busch = g.Teil("busch")
	for k in range(5):
		dx = 0.006 * (k - 2)
		mitte, hoehen = [], []
		for u in np.linspace(0, 1, 44):
			phi = -0.95 + 2.6 * u          # negativer Winkel = Stirnseite, positiver = Nacken
			s, w = (abs(phi), 0.0) if phi < 0 else (phi, PI)
			h = (0.012 + 0.07 * math.sin(min(1.0, u * 1.05) * PI) ** 0.5) * (1 - 0.15 * abs(k - 2))
			basis = f.punkt(s, w, ab(s, w) + 0.006)
			n = (basis - f.c).normalized()
			mitte.append(basis + n * h * 0.5 + Vector((dx, 0, 0)))
			hoehen.append(h * 0.5)
		hh = hoehen
		pts = mitte
		links, rechts = [], []
		for i, p in enumerate(pts):
			n = (p - f.c).normalized()
			links.append(busch.vert(p + n * hh[i]))
			rechts.append(busch.vert(p - n * hh[i]))
		for i in range(len(pts) - 1):
			busch.flaeche([links[i], rechts[i], rechts[i + 1], links[i + 1]], "stoff_akzent")
	teile.append(obj(busch, 60, 0.004))
	# Halter des Busches
	pts = []
	for u in np.linspace(0, 1, 30):
		phi = -0.9 + 2.5 * u
		s, w = (abs(phi), 0.0) if phi < 0 else (phi, PI)
		pts.append(f.punkt(s, w, ab(s, w) + 0.004))
	g.zug(r, pts, 0.008, "rand", flach=0.6, aussen=lambda p: Vector((1, 0, 0)))
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Eismagie: Robe wie die anderen Elementarmagier, Schulterplatte und Metallgürtel


def schuppen(hoehe=0.03, anzahl=36, tiefe=0.0055):
	def e(s, w):
		reihe = math.floor(s / hoehe)
		u = s / hoehe - reihe
		v = (w / (2 * PI) * anzahl + 0.5 * (reihe % 2)) % 1.0
		bogen = (2 * v - 1) ** 2
		return tiefe * max(0.0, 1.0 - u - 0.45 * bogen) ** 0.7
	return e


def spear_brust(K):
	teile, _ = ir.wams(K, "stoff", 0.006, unten_z=0.66, kragen_z=1.53, aermel_bis=1.0, steppung=0.003, weite=0.04,
		aermel_abstand=0.005)
	f = ir.wams_feld(K)
	sch = schuppen()
	t = g.Teil("schuppenpanzer")
	weite = lambda s, w: 0.04 * g.weich(-s, -(0.92 - ZW), -(0.68 - ZW))
	g.platte(t, f, 0.68 - ZW, 1.47 - ZW, lambda s, w: 0.018 + weite(s, w) + sch(s, w), nu=170, nw=216, material_name="schuppen")
	o = obj(t, 60)
	o["max_fl"] = 60000
	teile.append(o)
	# kurze Schuppenärmel
	for seite in (1, -1):
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
		at = g.Teil("schuppenaermel")
		g.platte(at, fa, -0.02, l_ober * 0.55, lambda s, w: 0.014 + schuppen(0.028, 24)(s, w), nu=50, nw=96,
			material_name="schuppen")
		teile.append(obj(at, 60))
	r = g.Teil("rand")
	ring(r, f, 0.68 - ZW, lambda s, w: 0.02 + weite(s, w), 0.004, "leder_dunkel", flach=0.6, n=96)
	ring(r, f, 1.47 - ZW, 0.02, 0.006, "leder_dunkel", flach=0.6, n=96)
	teile.append(r.objekt())
	teile += ir.guertel(K, 0.98, 0.05, 0.05)
	ob = g.vereinen(teile, "x")
	ob["max_fl"] = 45000
	return ob


def spear_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder", 0.003, 0.05))
		teile += ir.armschiene_leder(K, seite, 0.011, False)
	return g.vereinen(teile, "x")


def spear_beine(K):
	teile = ir.hose(K, "stoff", 0.006)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		teile.append(blech("oberschenkel", fb, 0.2, l_knie - 0.065, 0.016, nu=16, nw=24, w_von=-1.0, w_bis=1.0))
		r = g.Teil("riemen")
		ring(r, fb, 0.2, 0.016, 0.004, w_von=-1.0, w_bis=1.0, n=24)
		for s in (0.26, l_knie - 0.12):
			pts, _ = g.rand_punkte(fb, s, 0.009, w_von=1.0, w_bis=2 * PI - 1.0, n=40)
			g.zug(r, pts, 0.007, "leder_dunkel", flach=0.35)
		teile.append(r.objekt())
		teile += kniekachel(K, seite, 0.017, 1.3)
	return g.vereinen(teile, "x")


def spear_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.008, 0.24))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("schnuerung")
		schnuerung(r, fb, l_ges - 0.24, l_ges - 0.05, 0.012, 0.0, 0.08, 7)
		teile.append(r.objekt())
		teile += schienbein(K, seite, 0.02, 0.75, hoch=0.25)
	return g.vereinen(teile, "x")


# ---------------- Eismagie: Wintermagier


def ice_kopf(K):
	teile, f, weit = kapuze(K, "stoff", A=0.026, gesicht=0.9, tief=0.025, saum="futter",
		kragen_unten=tabelle([(0, 0.5), (PI / 2, 0.52), (PI, 0.46)]))
	return g.vereinen(teile, "x")


def ice_brust(K):
	teile, f = ir.wams(K, "stoff", 0.02, unten_z=0.10, kragen_z=1.54, aermel_bis=1.0, weite=0.07, z0=0.08,
		aermel_abstand=0.01, manschette=0.03, rock_ab=0.95)
	r = g.Teil("saum")
	pts, zu = g.rand_punkte(f, 0.105 - ZW, lambda s, w: 0.02 + 0.07 + 0.003, n=120)
	g.zug(r, pts, 0.008, "futter", zu=zu, flach=0.5)
	for seite in (1, -1):
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
		pts, zu = g.rand_punkte(fa, l_ges - 0.004, 0.04 + 0.002, n=48)
		g.zug(r, pts, 0.007, "futter", zu=zu, flach=0.5)
	teile.append(r.objekt())
	# Eiserne Schulterplatte links (mit Lamellen)
	teile += ir._schulter(K, 1)
	# Breiter Metallgürtel aus Platten
	fw = ir.wams_feld(K)
	A = 0.04
	gt = g.Teil("metallguertel")
	teile.append(blech("guertel", fw, 0.93 - ZW, 1.05 - ZW, A, d=0.004, nu=6, nw=96))
	ring(gt, fw, 0.93 - ZW, A + 0.002, 0.005, n=96)
	ring(gt, fw, 1.05 - ZW, A + 0.002, 0.005, n=96)
	for k in range(12):
		w = 2 * PI * k / 12
		for z in (0.96, 1.02):
			g.niete(gt, fw.punkt(z - ZW, w, A + 0.001), fw.normale(z - ZW, w, A), 0.006)
	# Schnallenplatte vorne
	teile.append(blech("schliesse", fw, 0.92 - ZW, 1.06 - ZW, A + 0.008, d=0.004, nu=4, nw=8, w_von=-0.28, w_bis=0.28))
	teile.append(gt.objekt())
	return g.vereinen(teile, "x")


def ice_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhandschuh(K, seite, "leder", 0.012, 0.09, platte=True)
	return g.vereinen(teile, "x")


def ice_beine(K):
	return g.vereinen(ir.hose(K, "stoff_dunkel", 0.004), "x")


def ice_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.009, 0.24))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("riemen")
		ring(r, fb, l_ges - 0.1, 0.015, 0.006, "leder_dunkel", flach=0.35, n=48)
		ring(r, fb, l_ges - 0.2, 0.014, 0.006, "leder_dunkel", flach=0.35, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Degen, Muskete ohne Feder; Armbrust mit Lederkapuze


# ================================================================ LEICHT BIS MITTEL (L/M/L/M/L)


def puffhose(hoehe=0.035):
	return lambda s, w, lk, lg: hoehe * math.sin(min(1.0, max(0.0, (s - 0.04) / (lk - 0.02))) * PI) ** 1.3


def lederschutz(K, seite, material="leder"):
	fb, l_knie, l_ges = ir.bein_feld(K, seite)
	teile = [blech("oberschenkelleder", fb, 0.14, l_knie - 0.07, 0.013, d=0.005, nu=14, nw=28, w_von=-1.5, w_bis=1.5,
		material_name=material)]
	r = g.Teil("naht")
	pts, _ = g.rand_punkte(fb, 0.14, 0.013, w_von=-1.5, w_bis=1.5, n=28)
	g.zug(r, pts, 0.004, "leder_dunkel", flach=0.6)
	for s in (0.2, l_knie - 0.12):
		pts, _ = g.rand_punkte(fb, s, 0.008, w_von=1.5, w_bis=2 * PI - 1.5, n=24)
		g.zug(r, pts, 0.006, "leder_dunkel", flach=0.35)
	teile.append(r.objekt())
	return teile


def hut(K, material="stoff_dunkel", hoehe=0.06, breite=0.08, hoch_links=0.0, feder_an=True, band="leder_dunkel"):
	"""Krempenhut: zylindrischer Kopf mit runder Kante, Hutband, Krempe (links hochgeschlagen), Feder."""
	f = ir.kopf_feld(K)
	ab, H, R = topf_flaeche(f, 0.016, rund=0.03, hoeher=hoehe, weiter=0.008)
	s_r = 1.12
	teile = [blech("hut", f, 0.0, s_r, ab, d=0.004, nu=36, nw=96, material_name=material)]
	r = g.Teil("krempe")
	hoch = (lambda w: hoch_links * max(0.0, math.cos(w - PI / 2)) ** 2) if hoch_links else None
	aussen = krempe(r, f, s_r, ab, breite, material, neigung=0.12, n=96, hoch=hoch, stufen=5)
	teile.append(obj(r, 50, 0.004))
	rr = g.Teil("band")
	pts, zu = g.rand_punkte(f, lambda w: s_r - 0.07, lambda s, w: ab(s, w) + 0.002, n=96)
	g.zug(rr, pts, 0.013, band, zu=zu, flach=0.2, aussen=lambda p: (p - f.c).normalized())
	if feder_an:
		p0 = f.punkt(s_r - 0.12, PI / 2 + 0.5, ab(s_r - 0.12, PI / 2 + 0.5) + 0.004)
		feder(rr, p0, Vector((0.25, 0.9, 0.35)), Vector((0.4, 0, 1)), 0.24, 0.028)
	teile.append(rr.objekt())
	return g.vereinen(teile, "x")


# ---------------- Degen: Duellant


def rapier_kopf(K):
	f = ir.kopf_feld(K)
	puff = lambda s, w: 0.012 + 0.05 * math.sin(min(1.0, s / 1.12) * PI) ** 0.8 * (0.75 + 0.35 * math.cos(w - PI / 2))
	flach = lambda s, w: puff(s, w) - 0.035 * max(0.0, 1 - s / 0.5) ** 2
	teile = [blech("barett", f, 0.0, 1.12, flach, d=0.004, nu=30, nw=96, material_name="stoff_akzent")]
	r = g.Teil("band")
	ring(r, f, 1.1, 0.012, 0.009, "stoff_dunkel", flach=0.5, n=96)
	p0 = f.punkt(0.95, PI / 2 + 0.3, 0.05)
	g.niete(r, p0, Vector((1, 0, 0.2)), 0.012, "rand")
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def rapier_brust(K):
	teile, _ = ir.wams(K, "futter", 0.006, unten_z=0.92, kragen_z=1.53, aermel_bis=1.0, weite=0.0, aermel_abstand=0.006,
		puff=0.035, manschette=0.01, aermel_material="stoff_akzent")
	b, f = brustplatte_vorne(K, 0.03, 1.0)
	teile += b
	teile += ir.guertel(K, 0.98, 0.04, 0.04)
	# weißer Kragen
	r = g.Teil("kragen")
	pts, zu = g.rand_punkte(ir.wams_feld(K), 1.52 - ZW, 0.016, n=72)
	g.zug(r, pts, 0.014, "futter", zu=zu, flach=0.4)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def rapier_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhandschuh(K, seite, "leder", 0.034, 0.14)
	return g.vereinen(teile, "x")


def rapier_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.006)
	for seite in (1, -1):
		teile += lederschutz(K, seite)
		teile += kniekachel(K, seite, 0.014, 1.2, "leder")
	return g.vereinen(teile, "x")


def rapier_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.013, 0.40, weite=0.03))
		teile.append(umschlag(K, seite, 0.40, 0.042, "leder", 0.07, 0.012))
	return g.vereinen(teile, "x")


# ---------------- Bogen: Waldläufer


def bow_kopf(K):
	teile, f, weit = kapuze(K, "stoff", A=0.024, gesicht=0.92, saum="leder",
		kragen_unten=tabelle([(0, 0.36), (0.9, 0.36), (PI / 2, 0.34), (2.4, 0.3), (PI, 0.28)]), kragen_weite=0.05)
	return g.vereinen(teile, "x")


def bow_brust(K):
	teile, _ = ir.wams(K, "stoff", 0.006, unten_z=0.70, kragen_z=1.52, aermel_bis=1.0, weite=0.04, aermel_abstand=0.005)
	b, f = vernietet(K, 0.022, "leder", unten_z=0.90, offen=0.0)
	teile += b
	t, vorne, fr = schraeg_riemen(K, 0.034, 0.016, "leder_dunkel", links_oben=False)
	g.niete(t, vorne[18], fr.normale(0.5, 0.0, 0.03), 0.012, "rand")
	teile.append(t.objekt())
	teile += ir.guertel(K, 0.97, 0.045, 0.04)
	return g.vereinen(teile, "x")


def bow_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder", 0.0028, 0.05))
		if seite > 0:   # Armschutz am Bogenarm
			teile += ir.armschiene_leder(K, seite, 0.01, False)
		else:
			teile += stulpenhandschuh(K, seite, "leder", 0.012, 0.09)[1:]
	return g.vereinen(teile, "x")


def bow_beine(K):
	teile = ir.hose(K, "leder", 0.006)
	for seite in (1, -1):
		teile += kniekachel(K, seite, 0.013, 1.2, "leder_dunkel")
	return g.vereinen(teile, "x")


def bow_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.008, 0.32))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("wickel")
		wickel(r, fb, l_ges - 0.3, l_ges - 0.2, 0.016, n=3, material="leder_dunkel", breite=0.007, neigung=0.02)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Armbrust: Armbruster


def crossbow_kopf(K):
	teile, f, weit = kapuze(K, "leder", A=0.022, gesicht=0.92, saum="leder_dunkel",
		kragen_unten=tabelle([(0, 0.56), (PI / 2, 0.58), (PI, 0.54)]))
	return g.vereinen(teile, "x")


# ---------------- Lebensmagie: weiße Robe mit Überwurf (Vorlage Heiler)


def crossbow_brust(K):
	teile, f = ir.wams(K, "stoff", 0.012, unten_z=0.66, kragen_z=1.54, aermel_bis=1.0, steppung=0.005, weite=0.05,
		aermel_abstand=0.008)
	b, fr = brustplatte_vorne(K, 0.045, 1.02)
	teile += b
	teile += ir.guertel(K, 0.97, 0.05, 0.05)
	# Bolzentasche rechts an der Hüfte
	r = g.Teil("tasche")
	w = -1.25
	p = f.punkt(0.9 - ZW, w, 0.08)
	n = f.normale(0.9 - ZW, w, 0.05)
	g.zug(r, [p + Vector((0, 0, 0.08)), p + Vector((0, 0, -0.1))], 0.04, "leder", seg=10, flach=0.6, aussen=lambda q: n)
	for k in range(6):
		q = p + Vector((0, 0, 0.09)) + n.cross(Vector((0, 0, 1))).normalized() * (k - 2.5) * 0.011
		g.zug(r, [q, q + Vector((0, 0, 0.05))], 0.003, "holz", seg=6)
		g.zug(r, [q + Vector((0, 0, 0.05)), q + Vector((0, 0, 0.065))], 0.005, "feder", seg=4, flach=0.25)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def crossbow_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhandschuh(K, seite, "leder_dunkel", 0.012, 0.09)
	return g.vereinen(teile, "x")


def crossbow_beine(K):
	teile = ir.hose(K, "stoff", 0.008, bein_extra=steppnaht(0.04, 0.003))
	for seite in (1, -1):
		teile += kniekachel(K, seite, 0.019, 1.4)
	return g.vereinen(teile, "x")


def crossbow_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.008, 0.15))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("riemen")
		ring(r, fb, l_ges - 0.1, 0.014, 0.006, "leder", flach=0.35, n=48)
		g.niete(r, fb.punkt(l_ges - 0.1, -PI / 2 * seite, 0.018), fb.normale(l_ges - 0.1, -PI / 2 * seite, 0.018), 0.008, "rand")
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Muskete: Musketier


def musket_kopf(K):
	return hut(K, "stoff_dunkel", 0.065, 0.095, hoch_links=0.07, feder_an=False)


def musket_brust(K):
	teile, f = ir.wams(K, "leder", 0.016, unten_z=0.60, kragen_z=1.52, aermel_bis=1.0, weite=0.09, aermel_abstand=0.007,
		aermel_material="futter", puff=0.012, manschette=0.012)
	t, vorne, fr = schraeg_riemen(K, 0.036, 0.018, "leder_dunkel", links_oben=True)
	# Pulverflaschen am Bandelier
	for k in range(5):
		p = vorne[6 + 4 * k]
		flasche(t, p + Vector((0, -0.022, -0.012)), 0.03, "holz")
	teile.append(t.objekt())
	teile += ir.guertel(K, 0.96, 0.05, 0.045)
	r = g.Teil("kragen")
	fw = ir.wams_feld(K)
	pts, zu = g.rand_punkte(fw, 1.5 - ZW, 0.03, n=72)
	g.zug(r, pts, 0.03, "futter", zu=zu, flach=0.18, aussen=lambda p: Vector((0, 0, 1)))
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def musket_haende(K):
	teile = []
	for seite in (1, -1):
		teile += stulpenhandschuh(K, seite, "leder", 0.04, 0.15)
	return g.vereinen(teile, "x")


def musket_beine(K):
	teile = ir.hose(K, "stoff_akzent", 0.006, unten=0.3, bein_extra=puffhose(0.026))
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("band")
		ring(r, fb, l_knie + (l_ges - l_knie) * 0.3 - 0.035, 0.012, 0.009, "stoff_dunkel", flach=0.4, n=48)
		teile.append(r.objekt())
		# Strümpfe darunter
		t = g.Teil("strumpf")
		g.platte(t, fb, l_knie, l_ges - 0.02, 0.003, nu=20, nw=40, material_name="futter")
		teile.append(obj(t, 60, 0.002))
	return g.vereinen(teile, "x")


def musket_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.013, 0.42, weite=0.04))
		teile.append(umschlag(K, seite, 0.42, 0.05, "leder_dunkel", 0.09, 0.02))
	return g.vereinen(teile, "x")


# ---------------- Lebensmagie: Heiler


def life_kopf(K):
	"""Zurückgeschlagene Kapuze und Schaltuch um Hals und Schultern."""
	fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	teile = []
	# Schaltuch: weite Rolle um den Hals
	r = g.Teil("schal")
	for k in range(3):
		pts, zu = g.rand_punkte(fr, lambda w, k=k: 0.68 + 0.035 * k - 0.06 * math.cos(w) ** 2 * (w % (2 * PI) < PI / 2 or w % (2 * PI) > 3 * PI / 2),
			lambda s, w, k=k: 0.035 + 0.012 * k, n=96)
		g.zug(r, pts, 0.026 - 0.004 * k, "futter", zu=zu, seg=10, flach=0.7)
	teile.append(r.objekt())
	# zurückgeschlagene Kapuze liegt im Nacken
	fw = ir.wams_feld(K)
	t = g.Teil("kapuze_liegend")
	bauch = lambda s, w: 0.05 + 0.05 * math.sin(min(1.0, max(0.0, (s - (1.24 - ZW)) / 0.28)) * PI) * math.cos(min(1.0, g.wdiff(w, PI) / 0.75) * PI / 2) ** 0.7
	g.platte(t, fw, lambda w: 1.24 - ZW + 0.08 * (g.wdiff(w, PI) / 0.75) ** 2, 1.52 - ZW, bauch, nu=16, nw=24, w_von=PI - 0.75, w_bis=PI + 0.75, material_name="futter")
	teile.append(obj(t, 60, 0.004))
	rr = g.Teil("saum")
	pts, _ = g.rand_punkte(fw, lambda w: 1.24 - ZW + 0.08 * (g.wdiff(w, PI) / 0.75) ** 2, lambda s, w: bauch(s, w) + 0.002, w_von=PI - 0.75, w_bis=PI + 0.75, n=24)
	g.zug(rr, pts, 0.005, "stoff_akzent", flach=0.5)
	teile.append(rr.objekt())
	return g.vereinen(teile, "x")


def life_brust(K):
	teile, f = ir.wams(K, "futter", 0.02, unten_z=0.10, kragen_z=1.54, aermel_bis=1.0, weite=0.06, z0=0.08,
		aermel_abstand=0.01, manschette=0.025, rock_ab=0.95)
	r = g.Teil("saum")
	pts, zu = g.rand_punkte(f, 0.105 - ZW, lambda s, w: 0.02 + 0.06 + 0.003, n=120)
	g.zug(r, pts, 0.008, "stoff_akzent", zu=zu, flach=0.5)
	# Überwurf: Mantel über den Schultern, vorne offen, fällt bis unter das Knie
	fw = ir.wams_feld(K, 0.38)
	weite = lambda s, w: 0.04 + 0.1 * g.weich(-(s + 0.12) - ZW, -0.95, -0.40)
	oben = tabelle([(0, 1.44), (1.0, 1.5), (PI / 2, 1.53), (PI, 1.52)])
	t = g.Teil("ueberwurf")
	g.platte(t, fw, lambda w: 0.42 - ZW + 0.06 * math.cos(g.wdiff(w, PI) / 2) ** 2, lambda w: oben(w) - ZW, weite, nu=56,
		nw=80, w_von=0.42, w_bis=2 * PI - 0.42, material_name="futter")
	teile.append(obj(t, 60, 0.004))
	for w in (0.42, 2 * PI - 0.42):
		pts = [fw.punkt(s, w, weite(s, w) + 0.003) for s in np.linspace(0.44 - ZW, oben(w) - ZW, 40)]
		g.zug(r, pts, 0.008, "stoff_akzent", flach=0.4)
	pts, _ = g.rand_punkte(fw, lambda w: 0.42 - ZW + 0.06 * math.cos(g.wdiff(w, PI) / 2) ** 2,
		lambda s, w: weite(s, w) + 0.003, w_von=0.42, w_bis=2 * PI - 0.42, n=80)
	g.zug(r, pts, 0.008, "stoff_akzent", flach=0.4)
	# Ärmelsäume
	for seite in (1, -1):
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
		pts, zu = g.rand_punkte(fa, l_ges - 0.004, 0.035 + 0.002, n=48)
		g.zug(r, pts, 0.007, "stoff_akzent", zu=zu, flach=0.5)
	# Medaillon an einer Kordel
	fr = ir.rumpf_feld(K)
	pts = [fr.punkt(0.74 - 0.3 * (1 - u * u), u * 0.9, 0.03) for u in np.linspace(-1, 1, 30)]
	g.zug(r, pts, 0.003, "leder_dunkel")
	g.niete(r, fr.punkt(0.43, 0.0, 0.035), fr.normale(0.43, 0.0, 0.03), 0.022, "rand")
	teile.append(r.objekt())
	# Gürtel mit großer Umhängetasche und kleinen Taschen
	teile += ir.guertel(K, 0.97, 0.05, 0.05, "leder")
	tt = g.Teil("taschen")
	fg = ir.wams_feld(K)
	tasche(tt, fg.punkt(0.86 - ZW, -0.45, 0.09), fg.normale(0.86 - ZW, -0.45, 0.08), 0.15, 0.13, 0.05)
	for w in (0.75, 1.3):
		tasche(tt, fg.punkt(0.9 - ZW, w, 0.075), fg.normale(0.9 - ZW, w, 0.07), 0.06, 0.07, 0.028)
	flasche(tt, fg.punkt(0.93 - ZW, 1.75, 0.08), 0.028, "rand")
	teile.append(tt.objekt())
	return g.vereinen(teile, "x")


def life_haende(K):
	teile = []
	for seite in (1, -1):
		teile += ir.armschiene_leder(K, seite, 0.012, False)
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.8)
		r = g.Teil("wickel")
		wickel(r, fa, l_ges - 0.04, l_ges + 0.01, 0.006, n=3, material="futter", breite=0.008)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def life_beine(K):
	return g.vereinen(ir.hose(K, "stoff", 0.004), "x")


def life_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.009, 0.24, weite=0.012))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("falten")
		for k in range(3):
			s = l_ges - 0.2 + 0.045 * k
			pts, zu = g.rand_punkte(fb, lambda w, s=s: s + 0.01 * math.sin(w * 2 + k), 0.016, n=48)
			g.zug(r, pts, 0.006, "leder", zu=zu, flach=0.5)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Messer: Kragen über den Riemen; Feuer: keine Wickel unter den Ärmeln


# ================================================================ LEICHT


# ---------------- Messer: Meuchler


def knife_kopf(K):
	teile, f, weit = kapuze(K, "stoff_dunkel", A=0.022, gesicht=0.9, saum="stoff_dunkel",
		kragen_unten=tabelle([(0, 0.5), (PI / 2, 0.52), (PI, 0.48)]), tief=0.015, kragen_ab=0.018)
	tuch = lambda s, w: 0.008 + 0.006 * g.weich(s, 1.9, 2.3)
	o = lambda w: AUGE_S + 0.1 + 0.15 * (g.wdiff(w, 0) / 1.0) ** 2
	teile.append(blech("tuch", f, o, 2.45, tuch, d=0.003, nu=16, nw=40, w_von=-1.0, w_bis=1.0, material_name="stoff_dunkel"))
	return g.vereinen(teile, "x")


def scheide(t, p, richtung, n, laenge=0.17):
	d = Vector(richtung).normalized()
	g.zug(t, [p, p + d * laenge], 0.017, "leder_dunkel", seg=8, flach=0.3, aussen=lambda q: n)
	g.zug(t, [p - d * 0.01, p - d * 0.08], 0.008, "leder", seg=8)
	g.zug(t, [p - d * 0.003, p - d * 0.012], 0.02, "rand", seg=8, flach=0.3, aussen=lambda q: n)


def knife_brust(K):
	teile, f = ir.wams(K, "leder_dunkel", 0.005, unten_z=0.90, kragen_z=1.54, aermel_bis=1.0, weite=0.0, aermel_abstand=0.004)
	t1, v1, fr = schraeg_riemen(K, 0.018, 0.012, "leder", links_oben=True)
	t2, v2, _ = schraeg_riemen(K, 0.022, 0.012, "leder", links_oben=False)
	for vs, tt in ((v1, t1), (v2, t2)):
		for i in (14, 21):
			p = vs[i]
			n = (p - fr.achse.punkt(p.z - Z0)).normalized()
			scheide(tt, p + n * 0.014, (vs[i - 3] - vs[i + 3]).normalized(), n, 0.12)
	teile += [t1.objekt(), t2.objekt()]
	teile += ir.guertel(K, 0.96, 0.045, 0.02)
	return g.vereinen(teile, "x")


def knife_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(fingerlos(K, seite, "leder_dunkel"))
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.8)
		r = g.Teil("wickel")
		wickel(r, fa, l_ges - 0.2, l_ges - 0.04, 0.007, n=8, material="stoff_dunkel", breite=0.009, neigung=0.015)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def knife_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.004)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite, konvex=0.6)
		r = g.Teil("wickel")
		wickel(r, fb, l_knie + 0.05, l_ges - 0.12, 0.01, n=9, material="stoff_dunkel", breite=0.011)
		ring(r, fb, 0.2, 0.008, 0.008, "leder", flach=0.35, n=40)
		teile.append(r.objekt())
		# Messer am Oberschenkel
		tt = g.Teil("scheide")
		w = 3 * PI / 2 if seite > 0 else PI / 2
		p = fb.punkt(0.2, w, 0.02)
		scheide(tt, p, Vector((0, 0, -1)), fb.normale(0.2, w, 0.02), 0.14)
		teile.append(tt.objekt())
	return g.vereinen(teile, "x")


def knife_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.006, 0.22))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("wickel")
		wickel(r, fb, l_ges - 0.2, l_ges - 0.08, 0.013, n=4, material="stoff_dunkel", breite=0.008, neigung=0.02)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Feuermagie: Feuermagier


def fire_kopf(K):
	teile, f, weit = kapuze(K, "stoff_akzent", A=0.03, gesicht=0.85, tief=0.035, saum="stoff_dunkel",
		kragen_unten=tabelle([(0, 0.48), (PI / 2, 0.5), (PI, 0.44)]))
	return g.vereinen(teile, "x")


def fire_brust(K):
	teile, f = ir.wams(K, "stoff_akzent", 0.02, unten_z=0.10, kragen_z=1.54, aermel_bis=1.0, weite=0.07, z0=0.08,
		aermel_abstand=0.01, manschette=0.035, rock_ab=0.95)
	r = g.Teil("saum")
	pts, zu = g.rand_punkte(f, 0.105 - ZW, lambda s, w: 0.02 + 0.07 + 0.003, n=120)
	g.zug(r, pts, 0.008, "stoff_dunkel", zu=zu, flach=0.5)
	for seite in (1, -1):
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.5)
		pts, zu = g.rand_punkte(fa, l_ges - 0.004, 0.045 + 0.002, n=48)
		g.zug(r, pts, 0.007, "stoff_dunkel", zu=zu, flach=0.5)
	teile.append(r.objekt())
	# Schärpe mit hängenden Enden
	teile += ir.guertel(K, 0.98, 0.07, 0.03, "stoff_dunkel", schnalle=False)
	s = g.Teil("schaerpe")
	fw = ir.wams_feld(K)
	w0 = -0.45
	p = fw.punkt(0.98 - ZW, w0, 0.045)
	n = fw.normale(0.98 - ZW, w0, 0.04)
	pts = [p + Vector((0.01 * k, 0, -0.045 * k)) + n * (0.004 * k) for k in range(9)]
	blatt(s, pts, lambda u: 0.03, n, "stoff_dunkel")
	pts = [p + Vector((-0.03 + 0.004 * k, 0, -0.04 * k)) + n * (0.006 + 0.004 * k) for k in range(7)]
	blatt(s, pts, lambda u: 0.028, n, "stoff_dunkel")
	g.zug(s, [p + Vector((-0.02, 0, 0.02)), p + Vector((0.02, 0, -0.02))], 0.02, "stoff_dunkel", flach=0.5, aussen=lambda q: n)
	teile.append(obj(s, 60, 0.003))
	return g.vereinen(teile, "x")


def fire_haende(K):
	teile = []
	for seite in (1, -1):
		hf, rw = hand_feld(K, seite)
		r = g.Teil("wickel")
		L = hf.achse.laenge()
		wickel(r, hf, 0.0, L - 0.01, 0.004, n=6, material="futter", breite=0.008, neigung=0.012)
		teile.append(r.objekt())
		teile.append(fingerlos(K, seite, "futter", 0.002, 0.03))
	return g.vereinen(teile, "x")


def fire_beine(K):
	return g.vereinen(ir.hose(K, "stoff_dunkel", 0.004), "x")


def fire_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder", 0.006, 0.06))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("riemen")
		von, bis = l_ges - 0.24, l_ges - 0.04
		for k in range(6):
			s = von + (bis - von) * k / 5
			pts, zu = g.rand_punkte(fb, lambda w, s=s: s + 0.03 * math.sin(w + k * 0.9), 0.006, n=48)
			g.zug(r, pts, 0.006, "leder", zu=zu, flach=0.35)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


# ---------------- Blitzmagie: Sturmmagier


def lightning_kopf(K):
	teile, f, weit = kapuze(K, "stoff_dunkel", A=0.022, gesicht=0.95, kragen=False, saum="rand")
	fr = ir.rumpf_feld(K, glatt=(4, 3), konvex=1.0)
	# hoher Stehkragen, vorne offen
	kr = lambda s, w: 0.045 + 0.05 * g.weich(s, 0.66, 0.9)
	teile.append(blech("stehkragen", fr, lambda w: 0.62, lambda w: 0.86 - 0.05 * (1 - g.wdiff(w, 0) / PI), kr, d=0.005,
		nu=14, nw=80, w_von=0.5, w_bis=2 * PI - 0.5, material_name="leder_dunkel"))
	r = g.Teil("rand")
	pts, _ = g.rand_punkte(fr, lambda w: 0.86 - 0.05 * (1 - g.wdiff(w, 0) / PI), kr, w_von=0.5, w_bis=2 * PI - 0.5, n=80)
	g.zug(r, pts, 0.004, "rand")
	for w in np.linspace(0.8, 2 * PI - 0.8, 9):
		g.niete(r, fr.punkt(0.7, w, kr(0.7, w) + 0.002), fr.normale(0.7, w, kr(0.7, w)), 0.005)
	teile.append(r.objekt())
	return g.vereinen(teile, "x")


def lightning_brust(K):
	teile, _ = ir.wams(K, "futter", 0.005, unten_z=0.80, kragen_z=1.53, aermel_bis=0.0, weite=0.0)
	mantel, f = ir.wams(K, "stoff_dunkel", 0.02, unten_z=0.64, kragen_z=1.5, aermel_bis=1.0, weite=0.08,
		aermel_abstand=0.008, offen=0.22, manschette=0.012)
	teile += mantel
	r = g.Teil("beschlag")
	for w in (0.22, 2 * PI - 0.22):
		pts = [f.punkt(s, w, 0.02 + 0.08 * g.weich(-s - ZW, -0.95, -0.64) + 0.003) for s in np.linspace(0.64 - ZW, 1.46 - ZW, 30)]
		g.zug(r, pts, 0.006, "rand", flach=0.4)
	for k in range(5):
		s = 1.38 - ZW - 0.08 * k
		for w in (0.3, -0.3):
			p0 = f.punkt(s, w, 0.025)
			g.zug(r, [p0, f.punkt(s, 0.0, 0.03), f.punkt(s, -w, 0.025)], 0.003, "rand")
			g.niete(r, p0, f.normale(s, w, 0.025), 0.007)
	teile.append(r.objekt())
	# kleine Schulterbeschläge
	for seite in (1, -1):
		fs = ir.schulter_feld(K, seite)
		aussen = PI / 2 if seite > 0 else 3 * PI / 2
		bis = lambda w: 0.55 + 0.35 * (1 - (g.wdiff(w, aussen) / PI) ** 2)
		teile.append(blech("schulter", fs, 0.0, bis, 0.04, d=0.003, nu=14, nw=48))
		rr = g.Teil("rand")
		pts, zu = g.rand_punkte(fs, bis, 0.04, n=72)
		g.zug(rr, pts, 0.004, "rand", zu=zu)
		teile.append(rr.objekt())
	teile += ir.guertel(K, 0.98, 0.04, 0.03)
	return g.vereinen(teile, "x")


def lightning_haende(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.handschuh(K, seite, "leder_dunkel", 0.0028, 0.06))
		hf, rw = hand_feld(K, seite)
		L = hf.achse.laenge()
		r = g.Teil("nieten")
		n = "Left" if seite > 0 else "Right"
		for fname, pts_f in ir.finger_achsen(K, seite).items():
			if fname == "Thumb":
				continue
			ach = g.Achse(pts_f)
			fa2 = g.Feld(K.bvh([n + fname], 0.5), ach, ringe=16, seg=24, r_max=0.05, konvex_anteil=1.0, glatt=(1, 1))
			rw2 = ir._handruecken_winkel(K, seite, ach)
			for s in (0.004, 0.03):
				g.niete(r, fa2.punkt(s, rw2, 0.004), fa2.normale(s, rw2, 0.004), 0.0055)
		fa, l_ober, l_ges = ir.arm_feld(K, seite, konvex=0.8)
		ring(r, fa, l_ges - 0.05, 0.006, 0.005, "rand", flach=0.5, n=48)
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def lightning_beine(K):
	teile = ir.hose(K, "stoff_dunkel", 0.004)
	for seite in (1, -1):
		fb, l_knie, l_ges = ir.bein_feld(K, seite, konvex=0.6)
		r = g.Teil("riemen")
		for s in (0.16, 0.3, l_knie - 0.07):
			ring(r, fb, s, 0.006, 0.006, "leder", flach=0.35, n=40)
			w = 3 * PI / 2 if seite > 0 else PI / 2
			g.niete(r, fb.punkt(s, w, 0.009), fb.normale(s, w, 0.009), 0.006, "rand")
		teile.append(r.objekt())
	return g.vereinen(teile, "x")


def lightning_fuesse(K):
	teile = []
	for seite in (1, -1):
		teile.append(ir.stiefel(K, seite, "leder_dunkel", 0.007, 0.27))
		fb, l_knie, l_ges = ir.bein_feld(K, seite)
		r = g.Teil("schnuerung")
		schnuerung(r, fb, l_ges - 0.27, l_ges - 0.05, 0.011, 0.0, 0.07, 8, "rand")
		teile.append(r.objekt())
		ff = ir.fuss_feld(K, seite)
		L = ff.achse.laenge()
		teile.append(blech("kappe", ff, L - 0.05, L, 0.014, nu=8, nw=24, w_von=-1.5, w_bis=1.5))
	return g.vereinen(teile, "x")


def stachel(t, p, n, laenge=0.03, r=0.009, material="platte", seg=8, kanten=4):
	"""Kegel (Dorn) auf der Fläche bei p in Richtung n; kanten = Grate (grob, kantig)."""
	n = Vector(n).normalized()
	q = n.orthogonal().normalized()
	q2 = n.cross(q)
	ring = []
	for j in range(seg):
		a = 2 * PI * j / seg
		rr = r * (1.0 if (j * kanten // seg) % 1 == 0 and j % (seg // kanten) == 0 else 0.72)
		ring.append(t.vert(p + (q * math.cos(a) + q2 * math.sin(a)) * rr - n * 0.004))
	sp = t.vert(p + n * laenge)
	c = t.vert(p - n * 0.004)
	for j in range(seg):
		k = (j + 1) % seg
		t.flaeche([ring[j], ring[k], sp], material)
		t.flaeche([ring[k], ring[j], c], material)


def _grobe_schulter(K, seite, t_stachel):
	"""Kantige Schulterkappe über dem Harnisch, mit Graten und Dornen."""
	f = ir.schulter_feld(K, seite)
	aussen = PI / 2 if seite > 0 else 3 * PI / 2
	bis = lambda w: 0.95 + 0.7 * (1 - (g.wdiff(w, aussen) / PI) ** 2)
	grat = lambda s, w: 0.018 * math.exp(-(g.wdiff(w, aussen) / 0.18) ** 2) * g.weich(-s, -1.4, -0.2)
	teile = []
	for k in range(2):
		A = 0.055 + 0.012 * k
		b = (lambda w, k=k: bis(w) - 0.28 * k)
		teile.append(blech("grobe_schulter", f, 0.0, b, lambda s, w, A=A: A + grat(s, w), d=0.0035, nu=18, nw=72))
		pts, zu = g.rand_punkte(f, b, lambda s, w, A=A: A + grat(s, w), n=96)
		g.zug(t_stachel, pts, 0.005, "rand", zu=zu)
	for k, s in enumerate((0.25, 0.55, 0.85)):
		p = f.punkt(s, aussen, 0.067 + grat(s, aussen))
		stachel(t_stachel, p, f.normale(s, aussen, 0.067) + Vector((0, 0, 0.6)), 0.05 - 0.008 * k, 0.012)
	return teile


# ================================================================ Zuordnung


def _satz(**fn):
	return fn


BAU = {
	"sword_shield": _satz(kopf=sus_kopf, brust=sus_brust, haende=ir.schwer_haende, beine=sus_beine, fuesse=ir.schwer_fuesse),
	"hammer": _satz(kopf=hammer_kopf, brust=hammer_brust, haende=hammer_haende, beine=hammer_beine, fuesse=hammer_fuesse),
	"axe": _satz(kopf=axe_kopf, brust=axe_brust, haende=axe_haende, beine=axe_beine, fuesse=axe_fuesse),
	"void_magic": _satz(kopf=void_kopf, brust=void_brust, haende=void_haende, beine=void_beine, fuesse=void_fuesse),
}
for _w in ("greatsword", "spear", "ice_magic", "rapier", "bow", "crossbow", "musket", "life_magic", "knife", "fire_magic",
		"lightning_magic"):
	_k = _w.replace("_magic", "")
	BAU[_w] = {slot: globals()[_k + "_" + slot] for slot in SLOTS}
