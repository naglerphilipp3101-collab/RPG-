"""Bausteine für die Waffenmodelle: Querschnitte entlang einer Achse (Loft), Drehkörper, Wicklungen.

Alle Maße in Metern. Gebaut wird mit der Länge entlang +Z (Griff am Ursprung, Klinge nach oben),
Breite entlang X, Dicke entlang Y. Beim Export wird um X gedreht, damit die Klinge in Godot nach -Z zeigt.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix


class Teil:
	"""Sammelt Flächen je Material in einem bmesh. Am Ende wird daraus ein Objekt mit Materialplätzen."""

	def __init__(self, name, glatt=35.0):
		self.name = name
		self.glatt = glatt  # Kantenwinkel: darüber bleibt die Kante hart
		self.bm = bmesh.new()
		self.slots = []  # Materialnamen in Reihenfolge der Plätze

	def slot(self, material):
		if material not in self.slots:
			self.slots.append(material)
		return self.slots.index(material)

	def flaeche(self, verts, material):
		f = self.bm.faces.new(verts)
		f.material_index = self.slot(material)
		return f

	def vert(self, co):
		return self.bm.verts.new(co)

	def objekt(self, glatt_winkel=None):
		glatt_winkel = self.glatt if glatt_winkel is None else glatt_winkel
		bm = self.bm
		bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
		bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
		me = bpy.data.meshes.new(self.name)
		bm.to_mesh(me)
		bm.free()
		for m in self.slots:
			me.materials.append(material(m))
		for p in me.polygons:
			p.use_smooth = True
		me.set_sharp_from_angle(angle=math.radians(glatt_winkel))
		ob = bpy.data.objects.new(self.name, me)
		bpy.context.scene.collection.objects.link(ob)
		return ob


_MATERIAL_FARBEN = {
	"klinge": (0.6, 0.6, 0.62), "beschlag": (0.45, 0.42, 0.38), "leder": (0.25, 0.14, 0.07),
	"holz": (0.4, 0.25, 0.12), "leucht": (0.4, 0.7, 1.0), "stein": (0.8, 0.1, 0.1), "stoff": (0.7, 0.65, 0.55),
	"sehne": (0.85, 0.82, 0.72), "kristall": (0.9, 0.5, 0.2), "dunkel": (0.12, 0.12, 0.13),
}


def material(name):
	"""Platzhalter-Material mit festem Namen. Die echten Materialien vergibt Godot nach diesem Namen."""
	m = bpy.data.materials.get(name)
	if m is None:
		m = bpy.data.materials.new(name)
		c = _MATERIAL_FARBEN.get(name, (0.5, 0.5, 0.5))
		m.diffuse_color = (*c, 1.0)
	return m


# ---------------------------------------------------------------- Loft


def loft(t, schnitte, material, kappe_unten=True, kappe_oben=True, spitze_oben=None, spitze_unten=None):
	"""Verbindet Querschnitte gleicher Punktzahl.
	schnitte: Liste von (z, [(x, y), ...]) oder (Matrix, [(x, y), ...]) für gebogene Achsen.
	spitze_oben/unten: Punkt (Vector), in dem das Ende zusammenläuft, statt einer flachen Kappe."""
	ringe = []
	for pos, pts in schnitte:
		if isinstance(pos, Matrix):
			ring = [t.vert(pos @ Vector((x, y, 0.0))) for x, y in pts]
		else:
			ring = [t.vert((x, y, pos)) for x, y in pts]
		ringe.append(ring)
	n = len(ringe[0])
	for a, b in zip(ringe, ringe[1:]):
		for i in range(n):
			j = (i + 1) % n
			t.flaeche([a[i], a[j], b[j], b[i]], material)
	if spitze_oben is not None:
		s = t.vert(spitze_oben)
		r = ringe[-1]
		for i in range(n):
			t.flaeche([r[i], r[(i + 1) % n], s], material)
	elif kappe_oben:
		t.flaeche(list(ringe[-1]), material)
	if spitze_unten is not None:
		s = t.vert(spitze_unten)
		r = ringe[0]
		for i in range(n):
			t.flaeche([r[(i + 1) % n], r[i], s], material)
	elif kappe_unten:
		t.flaeche(list(reversed(ringe[0])), material)
	return ringe


def kreis(r, n=12, rx=None, ry=None, phase=0.0):
	rx = r if rx is None else rx
	ry = r if ry is None else ry
	return [(math.cos(phase + 2 * math.pi * i / n) * rx, math.sin(phase + 2 * math.pi * i / n) * ry) for i in range(n)]


def drehkoerper(t, profil, material, n=16, achse_z=0.0, versatz=Vector((0, 0, 0)), phase=0.0):
	"""Drehkörper um die Z-Achse. profil: [(radius, z), ...] von unten nach oben. Radius 0 = Spitze."""
	schnitte = []
	unten = oben = None
	for r, z in profil:
		if r <= 1e-5:
			if not schnitte:
				unten = Vector((versatz.x, versatz.y, z + versatz.z))
			else:
				oben = Vector((versatz.x, versatz.y, z + versatz.z))
			continue
		pts = [(x + versatz.x, y + versatz.y) for x, y in kreis(r, n, phase=phase)]
		schnitte.append((z + versatz.z, pts))
	return loft(t, schnitte, material, spitze_oben=oben, spitze_unten=unten)


def quader(t, mitte, groesse, material, fase=0.0):
	"""Quader, optional mit abgeschrägten senkrechten Kanten (8-Eck-Querschnitt)."""
	sx, sy, sz = groesse[0] / 2, groesse[1] / 2, groesse[2] / 2
	if fase > 0:
		f = min(fase, sx * 0.9, sy * 0.9)
		pts = [(sx, -sy + f), (sx, sy - f), (sx - f, sy), (-sx + f, sy), (-sx, sy - f), (-sx, -sy + f), (-sx + f, -sy), (sx - f, -sy)]
	else:
		pts = [(sx, -sy), (sx, sy), (-sx, sy), (-sx, -sy)]
	pts = [(x + mitte[0], y + mitte[1]) for x, y in pts]
	return loft(t, [(mitte[2] - sz, pts), (mitte[2] + sz, pts)], material)


def transformieren(t, verts, matrix):
	for v in verts:
		v.co = matrix @ v.co


def neue_verts(t, vorher):
	"""Alle Punkte, die seit 'vorher' (Anzahl) dazugekommen sind."""
	t.bm.verts.ensure_lookup_table()
	return t.bm.verts[vorher:]


def anzahl(t):
	return len(t.bm.verts)


# ---------------------------------------------------------------- Waffenteile


def wicklung(t, z0, z1, r, material="leder", windungen=None, tiefe=None, n=14, ry=None):
	"""Griff mit schräg gewickeltem Lederband: der Radius schwankt entlang einer Spirale."""
	laenge = z1 - z0
	windungen = windungen or max(3, round(laenge / 0.022))
	tiefe = tiefe if tiefe is not None else r * 0.12
	ry = ry if ry is not None else r
	schritte = windungen * 6
	schnitte = []
	for k in range(schritte + 1):
		z = z0 + laenge * k / schritte
		pts = []
		for i in range(n):
			w = 2 * math.pi * i / n
			phase = (w / (2 * math.pi) + k / 6.0) % 1.0  # Spirale
			band = 0.5 - 0.5 * math.cos(phase * 2 * math.pi)
			band = band ** 0.5
			s = 1.0 - tiefe / r * (1.0 - band)
			# Enden leicht verdickt (Bandabschluss)
			ende = min(k, schritte - k) / 3.0
			if ende < 1.0:
				s += (1.0 - ende) * 0.06
			pts.append((math.cos(w) * r * s, math.sin(w) * ry * s))
		schnitte.append((z, pts))
	loft(t, schnitte, material)


def klingen_schnitt(w, d, hohlkehle=0.0, kehl_breite=0.35, schneide=0.18, n_halb=7, kehlen=None):
	"""Querschnitt einer Klinge: Breite w (halb), Dicke d (halb). Linsenform mit Schneidenfase und Hohlkehle(n).
	kehlen: [(mitte, halbe_breite)] als Anteil von w; Standard ist eine Kehle in der Mitte.
	Gibt eine geschlossene Punktliste zurück (2*n_halb - 2 Punkte)."""
	kehlen = kehlen if kehlen is not None else [(0.0, kehl_breite)]
	oben = []
	for i in range(n_halb):
		x = -w + 2 * w * i / (n_halb - 1)
		u = abs(x) / max(w, 1e-6)
		if u > 1 - schneide:  # Schneidenfase: läuft spitz zu
			y = d * (1 - u) / schneide * 0.55
		else:
			y = d * (0.55 + 0.45 * (1 - (u / (1 - schneide)) ** 2))
		if hohlkehle > 0:
			for mitte, kb in kehlen:
				a = abs(u - mitte) / kb
				if a < 1:
					y -= hohlkehle * d * (1 - a * a)
		oben.append((x, max(y, d * 0.06) if 0 < u < 1 else (y if u < 1 else 0.0)))
	unten = [(x, -y) for x, y in reversed(oben[1:-1])]
	return oben + unten


def sechskant(w, d, kante=0.5):
	"""Sechseckiger Querschnitt (gerade Flächen, keine Rundung) – für Mithril."""
	return [(w, 0), (w * kante, d), (-w * kante, d), (-w, 0), (-w * kante, -d), (w * kante, -d)]


def klinge(t, z0, laenge, breite, dicke, material="klinge", hohlkehle=0.45, kehl_laenge=0.7, spitze=0.18,
		   verjuengung=0.75, n_halb=9, schritte=20, breite_fn=None, krumm=0.0, dicke_fn=None, schnitt=None,
		   rauh=0.0, saat=1, spitze_x=0.0, kehlen=None, kehl_breite=0.35):
	"""Klinge entlang +Z ab z0. breite = volle Breite am Heft. spitze = Anteil der Länge für die Spitze.
	breite_fn(u) gibt die Breite (Anteil, 0..1 entlang der Klinge) vor, oder ein Paar (links, rechts) für
	ungleiche Schneiden. dicke_fn(u) entsprechend die Dicke. schnitt(w, d) ersetzt den Querschnitt.
	rauh > 0 verschiebt die Punkte zufällig (wie aus Stein geschlagen). spitze_x verschiebt die Spitze seitlich."""
	import random
	rng = random.Random(saat)
	schnitte = []
	kehl_info = {}  # z -> (halbe Breite, Mitte, Kehltiefe) für die Akzentfarbe in der Hohlkehle
	for k in range(schritte + 1):
		u = k / schritte
		if u >= 1.0:
			break
		if breite_fn:
			r = breite_fn(u)
			wl, wr = (r if isinstance(r, tuple) else (r, r))
			wl, wr = wl * breite / 2, wr * breite / 2
		else:
			wl = wr = breite / 2 * (1 - (1 - verjuengung) * u)
			if u > 1 - spitze:
				s = (u - (1 - spitze)) / spitze
				wl = wr = wl * math.cos(s * math.pi / 2) ** 0.8
		w = max((wl + wr) / 2, 0.002)
		mitte = (wr - wl) / 2
		d = dicke / 2 * (dicke_fn(u) if dicke_fn else (1 - 0.45 * u))
		kehle = hohlkehle if u < kehl_laenge else hohlkehle * max(0.0, 1 - (u - kehl_laenge) / 0.08)
		pts = schnitt(w, d) if schnitt else klingen_schnitt(w, d, kehle, n_halb=n_halb, kehlen=kehlen, kehl_breite=kehl_breite)
		if rauh > 0:
			pts = [(x * (1 + rng.uniform(-rauh, rauh)), y * (1 + rng.uniform(-rauh, rauh) * 2)) for x, y in pts]
		x_off = krumm * u * u + mitte
		schnitte.append((z0 + laenge * u, [(x + x_off, y) for x, y in pts]))
		kehl_info[round(z0 + laenge * u, 6)] = (w, x_off, kehle if not schnitt and rauh == 0 else 0.0)
	f0 = len(t.bm.faces)
	loft(t, schnitte, material, spitze_oben=Vector((krumm + spitze_x, 0, z0 + laenge)))
	if hohlkehle > 0 and material == "klinge":
		_kehle_als_akzent(t, f0, kehl_info, kehlen if kehlen is not None else [(0.0, kehl_breite)])


def _kehle_als_akzent(t, f0, kehl_info, kehlen):
	"""Flächen in der Hohlkehle bekommen das Akzent-Material (Zierlinie, wie die roten Linien einer Dämonenklinge)."""
	t.bm.faces.ensure_lookup_table()
	akzent = None
	for f in t.bm.faces[f0:]:
		drin = True
		for v in f.verts:
			info = kehl_info.get(round(v.co.z, 6))
			if info is None or info[2] <= 0:
				drin = False
				break
			w, x_off, _ = info
			ux = (v.co.x - x_off) / max(w, 1e-6)
			if not any(abs(ux - m) < kb * 0.8 or abs(-ux - m) < kb * 0.8 for m, kb in kehlen):
				drin = False
				break
		if drin:
			if akzent is None:
				akzent = t.slot("akzent")
			f.material_index = akzent


def strang(t, punkte, breite, dicke, material, n=8, quer=Vector((0, 1, 0)), kappen=True, eckig=False):
	"""Zieht einen Querschnitt entlang einer Punktliste (Schnörkel, Flügel, Stacheln, Hörner).
	breite/dicke: Zahl oder Funktion u -> Wert (volle Maße). quer = Richtung der Dicke.
	Breite 0 am Ende ergibt eine Spitze. eckig = Rauten- statt Ellipsenquerschnitt (bei n=4)."""
	bw = breite if callable(breite) else (lambda u, b=breite: b)
	dw = dicke if callable(dicke) else (lambda u, d=dicke: d)
	punkte = [Vector(p) for p in punkte]
	m = len(punkte)
	ringe = []
	spitze_oben = spitze_unten = None
	for i, p in enumerate(punkte):
		u = i / (m - 1)
		tang = (punkte[min(i + 1, m - 1)] - punkte[max(i - 1, 0)]).normalized()
		b = (quer - tang * quer.dot(tang))
		if b.length < 1e-6:
			b = Vector((1, 0, 0)) - tang * tang.x
		b.normalize()
		wv = b.cross(tang).normalized()
		w, d = bw(u) / 2, dw(u) / 2
		if w <= 1e-5:
			if i == 0:
				spitze_unten = p
			else:
				spitze_oben = p
			continue
		ring = []
		for k in range(n):
			a = 2 * math.pi * k / n + (math.pi / n if eckig and n == 4 else 0)
			if eckig and n == 4:
				a = math.pi / 2 * k
			ring.append(t.vert(p + wv * (math.cos(a) * w) + b * (math.sin(a) * d)))
		ringe.append(ring)
	for ra, rb in zip(ringe, ringe[1:]):
		for k in range(n):
			j = (k + 1) % n
			t.flaeche([ra[k], ra[j], rb[j], rb[k]], material)
	if spitze_oben is not None:
		s = t.vert(spitze_oben)
		for k in range(n):
			t.flaeche([ringe[-1][k], ringe[-1][(k + 1) % n], s], material)
	elif kappen:
		t.flaeche(list(ringe[-1]), material)
	if spitze_unten is not None:
		s = t.vert(spitze_unten)
		for k in range(n):
			t.flaeche([ringe[0][(k + 1) % n], ringe[0][k], s], material)
	elif kappen:
		t.flaeche(list(reversed(ringe[0])), material)


def spirale(mitte, r0, r1, windungen, n=16, start=0.0, ebene="xz", richtung=1):
	"""Punkte einer flachen Spirale (für Schnörkel/Voluten), von außen (r0) nach innen (r1)."""
	pts = []
	for i in range(n + 1):
		u = i / n
		a = start + richtung * u * windungen * 2 * math.pi
		r = r0 + (r1 - r0) * u
		if ebene == "xz":
			pts.append(Vector((mitte[0] + math.cos(a) * r, mitte[1], mitte[2] + math.sin(a) * r)))
		else:
			pts.append(Vector((mitte[0] + math.cos(a) * r, mitte[1] + math.sin(a) * r, mitte[2])))
	return pts


def bogen(p0, p1, hoehe, n=10, richtung=Vector((0, 0, 1))):
	"""Punkte auf einem Bogen von p0 nach p1, in der Mitte um 'hoehe' in 'richtung' ausgebaucht."""
	p0, p1 = Vector(p0), Vector(p1)
	return [p0.lerp(p1, i / n) + richtung * hoehe * math.sin(math.pi * i / n) for i in range(n + 1)]


def rune_streifen(t, z0, z1, breite, dicke, material="leucht", n=8):
	"""Leuchtender Streifen in der Hohlkehle (beidseitig), knapp über der Klingenoberfläche."""
	for seite in (1, -1):
		vs = []
		for k in range(n + 1):
			z = z0 + (z1 - z0) * k / n
			w = breite / 2 * (1 - 0.4 * k / n)
			vs.append((t.vert((-w, seite * dicke, z)), t.vert((w, seite * dicke, z))))
		for a, b in zip(vs, vs[1:]):
			q = [a[0], a[1], b[1], b[0]]
			t.flaeche(q if seite > 0 else list(reversed(q)), material)


def parierstange(t, z, breite, hoehe, tiefe, material="beschlag", form="gerade", n=10):
	"""Parierstange quer zur Klinge (entlang X). form: gerade, geschwungen, kralle, flamme."""
	schnitte = []
	for k in range(n + 1):
		u = -1 + 2 * k / n
		x = u * breite / 2
		au = abs(u)
		h = hoehe * (1 + 0.25 * (1 - au))  # Mitte etwas höher
		d = tiefe * (1 - 0.3 * au)
		dz = 0.0
		if form == "geschwungen":
			dz = hoehe * 1.4 * au ** 2.2
		elif form == "kralle":
			dz = hoehe * 2.5 * au ** 3
			h *= 1 - 0.5 * au ** 2
		elif form == "flamme":
			dz = -hoehe * 1.2 * au ** 2 + hoehe * 3.0 * au ** 6
		if au > 0.85:
			h *= 1 + (au - 0.85) * 3  # Enden verdickt
		m = Matrix.Translation((x, 0, z + dz)) @ Matrix.Rotation(math.radians(90), 4, "Y")
		pts = [(py, px) for px, py in [(-h / 2, -d / 2), (h / 2, -d / 2), (h / 2 + h * 0.15, 0), (h / 2, d / 2), (-h / 2, d / 2), (-h / 2 - h * 0.15, 0)]]
		schnitte.append((m, pts))
	loft(t, schnitte, material)


def knauf(t, z, r, material="beschlag", form="scheibe", n=16):
	"""Knauf unter dem Griff, oberes Ende bei z."""
	if form == "scheibe":
		profil = [(0, z - r * 1.1), (r * 0.55, z - r * 1.08), (r * 0.95, z - r * 0.85), (r, z - r * 0.5), (r * 0.9, z - r * 0.15), (r * 0.45, z)]
	elif form == "kugel":
		profil = [(0, z - r * 2.0)] + [(r * math.sin(a), z - r - r * math.cos(a)) for a in [0.4, 0.9, 1.4, 1.8, 2.3, 2.7]] + [(r * 0.35, z)]
	elif form == "tropfen":
		profil = [(0, z - r * 2.4), (r * 0.5, z - r * 2.2), (r * 0.85, z - r * 1.7), (r, z - r * 1.1), (r * 0.7, z - r * 0.5), (r * 0.45, z)]
	elif form == "spitz":
		profil = [(0, z - r * 2.6), (r * 0.45, z - r * 1.8), (r, z - r * 1.0), (r * 0.8, z - r * 0.4), (r * 0.45, z)]
	else:
		raise ValueError(form)
	drehkoerper(t, profil, material, n=n, phase=math.pi / n)


def edelstein(t, mitte, r, material="stein", achse="y", n=8):
	"""Geschliffener Stein (Doppelpyramide mit Tafel)."""
	if isinstance(achse, Vector):
		a = achse.normalized()
	else:
		a = Vector((0, 1, 0)) if achse == "y" else (Vector((1, 0, 0)) if achse == "x" else Vector((0, 0, 1)))
	rot = a.to_track_quat("Z", "Y").to_matrix().to_4x4()
	m = Matrix.Translation(mitte) @ rot
	schnitte = [(m @ Matrix.Translation((0, 0, -r * 0.35)), kreis(r, n)),
				(m @ Matrix.Translation((0, 0, r * 0.15)), kreis(r * 0.6, n))]
	loft(t, schnitte, material, kappe_oben=True, spitze_unten=m @ Vector((0, 0, -r * 0.9)))


def ring(t, z, r, hoehe, material="beschlag", n=14, wulst=0.15):
	profil = [(r, z - hoehe / 2), (r * (1 + wulst), z), (r, z + hoehe / 2)]
	drehkoerper(t, profil, material, n=n)


# ---------------------------------------------------------------- Zierteile


def kristall(t, basis, richtung, laenge, r, material="eis", n=6, spitze_anteil=0.3, drehung=0.0):
	"""Sechskantiger Kristall mit Spitze, wächst von basis in richtung."""
	richtung = Vector(richtung).normalized()
	basis = Vector(basis)
	quer = Vector((0, 1, 0)) if abs(richtung.y) < 0.9 else Vector((1, 0, 0))
	rot = Matrix.Rotation(drehung, 3, richtung)
	quer = rot @ quer
	pts = [basis, basis + richtung * laenge * (1 - spitze_anteil), basis + richtung * laenge]
	strang(t, pts, lambda u: 2 * r if u < 0.99 else 0.0, lambda u: 2 * r * 0.87 if u < 0.99 else 0.0, material, n=n, quer=quer)


def stachel(t, basis, spitze_pos, r, material="beschlag", n=4, kruemmung=None):
	"""Spitzer, kantiger Dorn von basis nach spitze_pos; kruemmung (Vector) biegt ihn in der Mitte."""
	basis, spitze_pos = Vector(basis), Vector(spitze_pos)
	pts = [basis.lerp(spitze_pos, i / 6) for i in range(7)]
	if kruemmung is not None:
		pts = [p + Vector(kruemmung) * math.sin(math.pi * i / 6) for i, p in enumerate(pts)]
	richtung = (spitze_pos - basis).normalized()
	quer = Vector((0, 1, 0)) if abs(richtung.y) < 0.9 else Vector((1, 0, 0))
	strang(t, pts, lambda u: 2 * r * (1 - u), lambda u: 2 * r * (1 - u), material, n=n, quer=quer, eckig=(n == 4))


def feder(t, basis, ende, breite, dicke, material="beschlag", bauch=0.0, quer=Vector((0, 1, 0))):
	"""Flache Feder (für Flügel): breit an der Wurzel, rundet zur Spitze hin ab."""
	basis, ende = Vector(basis), Vector(ende)
	richtung = (ende - basis).normalized()
	seite = quer.cross(richtung).normalized()
	pts = [basis.lerp(ende, i / 8) + seite * bauch * math.sin(math.pi * i / 8) for i in range(9)]
	bf = lambda u: breite * (0.65 + 0.6 * math.sin(math.pi * min(u, 0.999) * 0.9)) * (1 - u ** 3) if u < 1 else 0.0
	strang(t, pts, bf, lambda u: dicke * (1 - 0.6 * u) if u < 1 else 0.0, material, n=8, quer=quer)


def scheibe(t, mitte, r, dicke, material="beschlag", n=24, strahlen=0, strahl_laenge=0.3, wulst=0.85):
	"""Runde Scheibe, deren Fläche zur Seite (±Y) zeigt; mit Strahlen wie eine Sonne."""
	m = Matrix.Translation(mitte) @ Matrix.Rotation(math.radians(90), 4, "X")
	def umriss(f):
		pts = []
		for k in range(n):
			a = 2 * math.pi * k / n
			rr = r
			if strahlen:
				s = 0.5 + 0.5 * math.cos(a * strahlen)
				rr = r * (1 + strahl_laenge * s ** 3)
			pts.append((math.cos(a) * rr * f, math.sin(a) * rr * f))
		return pts
	schnitte = [(m @ Matrix.Translation((0, 0, -dicke / 2)), umriss(wulst)),
				(m @ Matrix.Translation((0, 0, 0)), umriss(1.0)),
				(m @ Matrix.Translation((0, 0, dicke / 2)), umriss(wulst))]
	loft(t, schnitte, material)


def rohling(t, mitte, groesse, material="eis", saat=1, rauh=0.25, n=6, schritte=4, achse="x"):
	"""Unregelmäßiger Brocken, wie aus dem Stein geschlagen (Länge entlang X, oder Y/Z bei achse="y"/"z")."""
	import random
	rng = random.Random(saat)
	sx, sy, sz = groesse
	schnitte = []
	for i in range(schritte + 1):
		u = i / schritte
		f = math.sin(math.pi * (0.15 + 0.7 * u)) ** 0.5
		if achse == "z":
			m = Matrix.Translation((mitte[0], mitte[1], mitte[2] - sx / 2 + sx * u)) @ Matrix.Rotation(math.radians(90), 4, "Z")
		elif achse == "y":
			m = Matrix.Translation((mitte[0], mitte[1] - sx / 2 + sx * u, mitte[2])) @ Matrix.Rotation(math.radians(90), 4, "X")
		else:
			m = Matrix.Translation((mitte[0] - sx / 2 + sx * u, mitte[1], mitte[2])) @ Matrix.Rotation(math.radians(90), 4, "Y")
		pts = []
		for k in range(n):
			a = 2 * math.pi * k / n + rng.uniform(-0.2, 0.2)
			j = 1 + rng.uniform(-rauh, rauh)
			pts.append((math.cos(a) * sz / 2 * f * j, math.sin(a) * sy / 2 * f * j))
		schnitte.append((m, pts))
	loft(t, schnitte, material)
