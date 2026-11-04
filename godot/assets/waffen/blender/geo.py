"""Bausteine für die Waffenmodelle: Querschnitte entlang einer Achse (Loft), Drehkörper, Wicklungen.

Alle Maße in Metern. Gebaut wird mit der Länge entlang +Z (Griff am Ursprung, Klinge nach oben),
Breite entlang X, Dicke entlang Y. Beim Export wird um X gedreht, damit die Klinge in Godot nach -Z zeigt.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix


class Teil:
	"""Sammelt Flächen je Material in einem bmesh. Am Ende wird daraus ein Objekt mit Materialplätzen."""

	def __init__(self, name):
		self.name = name
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

	def objekt(self, glatt_winkel=35.0):
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


def klingen_schnitt(w, d, hohlkehle=0.0, kehl_breite=0.35, schneide=0.18, n_halb=7):
	"""Querschnitt einer Klinge: Breite w (halb), Dicke d (halb). Linsenform mit Schneidenfase und optionaler Hohlkehle.
	Gibt eine geschlossene Punktliste zurück (2*n_halb Punkte)."""
	oben = []
	for i in range(n_halb):
		x = -w + 2 * w * i / (n_halb - 1)
		u = abs(x) / max(w, 1e-6)
		if u > 1 - schneide:  # Schneidenfase: läuft spitz zu
			y = d * (1 - u) / schneide * 0.55
		else:
			y = d * (0.55 + 0.45 * (1 - (u / (1 - schneide)) ** 2))
		if hohlkehle > 0 and u < kehl_breite:
			y -= hohlkehle * d * (1 - (u / kehl_breite) ** 2)
		oben.append((x, max(y, d * 0.06) if 0 < u < 1 else (y if u < 1 else 0.0)))
	unten = [(x, -y) for x, y in reversed(oben[1:-1])]
	return oben + unten


def klinge(t, z0, laenge, breite, dicke, material="klinge", hohlkehle=0.45, kehl_laenge=0.7, spitze=0.18,
		   verjuengung=0.75, n_halb=9, schritte=20, breite_fn=None, krumm=0.0):
	"""Gerade Klinge entlang +Z ab z0. breite = volle Breite am Heft. spitze = Anteil der Länge für die Spitze.
	breite_fn(u) kann die Breite (0..1 entlang der Klinge) frei vorgeben."""
	schnitte = []
	for k in range(schritte + 1):
		u = k / schritte
		if breite_fn:
			w = breite_fn(u) * breite / 2
		else:
			w = breite / 2 * (1 - (1 - verjuengung) * u)
			if u > 1 - spitze:
				s = (u - (1 - spitze)) / spitze
				w *= math.cos(s * math.pi / 2) ** 0.8
		if u >= 1.0:
			break
		d = dicke / 2 * (1 - 0.45 * u)
		kehle = hohlkehle if u < kehl_laenge else hohlkehle * max(0.0, 1 - (u - kehl_laenge) / 0.08)
		pts = klingen_schnitt(max(w, 0.002), d, kehle, n_halb=n_halb)
		x_off = krumm * u * u
		schnitte.append((z0 + laenge * u, [(x + x_off, y) for x, y in pts]))
	loft(t, schnitte, material, spitze_oben=Vector((krumm, 0, z0 + laenge)))


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
	a = Vector((0, 1, 0)) if achse == "y" else (Vector((1, 0, 0)) if achse == "x" else Vector((0, 0, 1)))
	rot = a.to_track_quat("Z", "Y").to_matrix().to_4x4()
	m = Matrix.Translation(mitte) @ rot
	schnitte = [(m @ Matrix.Translation((0, 0, -r * 0.35)), kreis(r, n)),
				(m @ Matrix.Translation((0, 0, r * 0.15)), kreis(r * 0.6, n))]
	loft(t, schnitte, material, kappe_oben=True, spitze_unten=m @ Vector((0, 0, -r * 0.9)))


def ring(t, z, r, hoehe, material="beschlag", n=14, wulst=0.15):
	profil = [(r, z - hoehe / 2), (r * (1 + wulst), z), (r, z + hoehe / 2)]
	drehkoerper(t, profil, material, n=n)
