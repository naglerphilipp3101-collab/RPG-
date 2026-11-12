"""Bausteine für Rüstungen auf dem MakeHuman-Körper (bpy 5.2).

Koordinaten wie in Blender: Z oben, Blick nach -Y, Meter. Links der Figur = +X.
Der Körper kommt aus godot/tools/ruestung/mensch_lesen.py (gleiche Rechnung wie im Spiel).

Grundidee: Rüstungsteile sind Röhren um eine Achse (Rumpf, Arm, Bein, Kopf). Für jeden Ring
wird die Körperoberfläche per Strahl abgetastet, wahlweise zur konvexen Hülle geglättet
(Platten), um einen Abstand aufgeblasen und mit Ebenen sauber beschnitten.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "ruestung"))
from mensch_lesen import Mensch  # noqa: E402

PI_HALB = math.pi / 2
VORNE = Vector((0, -1, 0))
OBEN = Vector((0, 0, 1))

FARBEN = {
	"platte": (0.62, 0.63, 0.66), "rand": (0.5, 0.5, 0.52), "niete": (0.35, 0.33, 0.3),
	"kette": (0.45, 0.46, 0.48), "leder": (0.36, 0.22, 0.12), "leder_dunkel": (0.17, 0.11, 0.07),
	"stoff": (0.55, 0.47, 0.36), "stoff_akzent": (0.42, 0.16, 0.12), "futter": (0.7, 0.64, 0.52),
	"haut": (0.8, 0.62, 0.5),
}


def material(name):
	m = bpy.data.materials.get(name)
	if m is None:
		m = bpy.data.materials.new(name)
		c = FARBEN.get(name, (0.5, 0.5, 0.5))
		m.diffuse_color = (*c, 1.0)
		m.use_nodes = True
		bsdf = m.node_tree.nodes.get("Principled BSDF")
		if bsdf:
			bsdf.inputs["Base Color"].default_value = (*c, 1.0)
			metall = name in ("platte", "rand", "niete", "kette")
			bsdf.inputs["Metallic"].default_value = 0.9 if metall else 0.0
			bsdf.inputs["Roughness"].default_value = 0.35 if metall else 0.8
		m.metallic = 0.9 if name in ("platte", "rand", "niete", "kette") else 0.0
		m.roughness = 0.35 if name in ("platte", "rand", "niete", "kette") else 0.8
	return m


def mh_zu_bl(p):
	p = np.asarray(p)
	return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


def bl_zu_mh(p):
	p = np.asarray(p)
	return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


class Koerper:
	"""Der Bezugskörper (Standard-Mann), an dem die Rüstung gebaut wird."""

	def __init__(self, aussehen=None):
		self.m = Mensch()
		self.mh = self.m.form_berechnen(aussehen)
		self.p = mh_zu_bl(self.mh)
		self.dreiecke = self.m.koerper_dreiecke
		self.knochen = {}
		for k in self.m.meta["knochen"]:
			self.knochen[k["name"]] = (Vector(self.p[k["kopf"]].mean(0)), Vector(self.p[k["ende"]].mean(0)))
		self._bvh = {}

	def gelenk(self, name, ende=False):
		return self.knochen[name][1 if ende else 0].copy()

	def anteil(self, namen):
		return self.m.knochen_anteil(namen)

	def bvh(self, namen, schwelle=0.35, extra=None):
		"""BVH aus den Körperdreiecken, deren Punkte überwiegend an den genannten Knochen hängen."""
		schl = (tuple(namen), schwelle)
		if schl in self._bvh:
			return self._bvh[schl]
		a = self.anteil(namen)
		ok = (a[self.dreiecke] >= schwelle).any(axis=1)
		if extra is not None:
			ok &= extra(self.p[self.dreiecke].mean(axis=1))
		dr = self.dreiecke[ok]
		b = BVHTree.FromPolygons([Vector(v) for v in self.p], dr.tolist())
		self._bvh[schl] = b
		return b

	def bvh_bereich(self, fn, schl):
		"""BVH aus allen Körperdreiecken, deren Mittelpunkt fn(x, y, z) erfüllt (numpy, vektoriell)."""
		if schl in self._bvh:
			return self._bvh[schl]
		c = self.p[self.dreiecke].mean(axis=1)
		dr = self.dreiecke[fn(c[:, 0], c[:, 1], c[:, 2])]
		b = BVHTree.FromPolygons([Vector(v) for v in self.p], dr.tolist())
		self._bvh[schl] = b
		return b

	def objekt(self, name="Koerper"):
		me = bpy.data.meshes.new(name)
		me.from_pydata(self.p.tolist(), [], self.dreiecke.tolist())
		me.update()
		for poly in me.polygons:
			poly.use_smooth = True
		me.materials.append(material("haut"))
		ob = bpy.data.objects.new(name, me)
		bpy.context.scene.collection.objects.link(ob)
		return ob


# ---------------------------------------------------------------- Röhren


def _hull(pts):
	pts = sorted(set(map(tuple, pts)))
	if len(pts) < 3:
		return pts

	def kreuz(o, a, b):
		return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
	unten, oben = [], []
	for p in pts:
		while len(unten) >= 2 and kreuz(unten[-2], unten[-1], p) <= 0:
			unten.pop()
		unten.append(p)
	for p in reversed(pts):
		while len(oben) >= 2 and kreuz(oben[-2], oben[-1], p) <= 0:
			oben.pop()
		oben.append(p)
	return unten[:-1] + oben[:-1]


def _strahl_polygon(poly, winkel):
	"""Abstand vom Ursprung bis zum Rand eines konvexen Polygons in Richtung winkel."""
	d = np.array([math.cos(winkel), math.sin(winkel)])
	best = 0.0
	n = len(poly)
	for i in range(n):
		a = np.array(poly[i])
		b = np.array(poly[(i + 1) % n])
		e = b - a
		m = np.array([[d[0], -e[0]], [d[1], -e[1]]])
		det = np.linalg.det(m)
		if abs(det) < 1e-12:
			continue
		t, s = np.linalg.solve(m, a)
		if t > 0 and -1e-6 <= s <= 1 + 1e-6:
			best = max(best, t)
	return best


def _glaetten_1d(a, n, zyklisch=False):
	a = a.copy()
	for _ in range(n):
		if zyklisch:
			a = 0.25 * np.roll(a, 1, axis=0) + 0.5 * a + 0.25 * np.roll(a, -1, axis=0)
		else:
			b = a.copy()
			b[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
			a = b
	return a


class Achse:
	"""Gebogene Achse aus Punkten; Ringe stehen senkrecht darauf, Winkel 0 zeigt nach 'vorne'."""

	def __init__(self, punkte, vorne=VORNE):
		self.pk = [Vector(p) for p in punkte]
		self.vorne = Vector(vorne)
		l = [0.0]
		for a, b in zip(self.pk, self.pk[1:]):
			l.append(l[-1] + (b - a).length)
		self.l = l

	def laenge(self):
		return self.l[-1]

	def punkt(self, s):
		s = min(max(s, 0.0), self.l[-1])
		for i in range(len(self.pk) - 1):
			if s <= self.l[i + 1] or i == len(self.pk) - 2:
				t = (s - self.l[i]) / max(1e-9, self.l[i + 1] - self.l[i])
				return self.pk[i].lerp(self.pk[i + 1], t)

	def tangente(self, s, weich=0.04):
		a = self.punkt(max(0.0, s - weich))
		b = self.punkt(min(self.l[-1], s + weich))
		return (b - a).normalized()

	def rahmen(self, s):
		t = self.tangente(s)
		v = self.vorne - t * self.vorne.dot(t)
		if v.length < 1e-4:
			v = OBEN - t * OBEN.dot(t)
		n = v.normalized()
		b = t.cross(n)
		return self.punkt(s), t, n, b


def roehre_abtasten(koerper_bvh, achse, ringe, segmente, r_max=0.45, s0=0.0, s1=None):
	"""Radius der Körperoberfläche je Ring und Winkel (von außen abgetastet). Rückgabe r[ring, seg], Rahmen."""
	s1 = achse.laenge() if s1 is None else s1
	r = np.full((ringe, segmente), np.nan)
	rahmen = []
	for i in range(ringe):
		s = s0 + (s1 - s0) * i / max(1, ringe - 1)
		c, t, n, b = achse.rahmen(s)
		rahmen.append((c, t, n, b))
		for j in range(segmente):
			w = 2 * math.pi * j / segmente
			d = n * math.cos(w) + b * math.sin(w)
			start = c + d * r_max
			treffer = koerper_bvh.ray_cast(start, -d, r_max)
			if treffer[0] is not None:
				r[i, j] = r_max - treffer[3]
	return r, rahmen


def lueckenfuellen(r, standard=0.02):
	r = r.copy()
	for i in range(r.shape[0]):
		zeile = r[i]
		ok = ~np.isnan(zeile)
		if ok.sum() == 0:
			continue
		if ok.sum() < len(zeile):
			idx = np.arange(len(zeile))
			zeile[~ok] = np.interp(idx[~ok], np.concatenate([idx[ok] - len(zeile), idx[ok], idx[ok] + len(zeile)]),
				np.concatenate([zeile[ok]] * 3))
		r[i] = zeile
	# leere Ringe von den Nachbarn
	leer = np.isnan(r).all(axis=1)
	if leer.all():
		r[:] = standard
	elif leer.any():
		idx = np.arange(r.shape[0])
		for j in range(r.shape[1]):
			r[leer, j] = np.interp(idx[leer], idx[~leer], r[~leer, j])
	return r


def konvex(r, anteil=1.0):
	"""Je Ring zur konvexen Hülle glätten (Platten überbrücken Mulden)."""
	ringe, seg = r.shape
	w = 2 * np.pi * np.arange(seg) / seg
	out = r.copy()
	for i in range(ringe):
		pts = np.stack([np.cos(w) * r[i], np.sin(w) * r[i]], 1)
		h = _hull([tuple(p) for p in np.round(pts, 6)])
		if len(h) < 3:
			continue
		hr = np.array([_strahl_polygon(h, x) for x in w])
		out[i] = r[i] + (np.maximum(hr, r[i]) - r[i]) * anteil
	return out


def glaetten(r, axial=2, rund=2):
	r = _glaetten_1d(r, axial)
	r = _glaetten_1d(r.T, rund, zyklisch=True).T
	return r


def aufwaerts_monoton(r, richtung=1):
	"""Radius soll in Achsrichtung nicht wieder wachsen (z. B. Helmkuppel)."""
	r = r.copy()
	rng = range(1, r.shape[0]) if richtung > 0 else range(r.shape[0] - 2, -1, -1)
	for i in rng:
		vor = i - richtung
		r[i] = np.minimum(r[i], r[vor])
	return r


def roehre_mesh(t, rahmen, r, material_name, kappe_anfang=None, kappe_ende=None, seg_material=None):
	"""Baut das Gitter in ein Teil t (bmesh-Sammler). kappe_*: None, 'flach' oder 'spitz' (Punkt auf der Achse)."""
	ringe, seg = r.shape
	vs = []
	for i in range(ringe):
		c, _, n, b = rahmen[i]
		ring = []
		for j in range(seg):
			w = 2 * math.pi * j / seg
			ring.append(t.vert(c + (n * math.cos(w) + b * math.sin(w)) * r[i, j]))
		vs.append(ring)
	for i in range(ringe - 1):
		for j in range(seg):
			k = (j + 1) % seg
			m = material_name if seg_material is None else seg_material(i, j)
			t.flaeche([vs[i][j], vs[i][k], vs[i + 1][k], vs[i + 1][j]], m)
	for kappe, i, umk in ((kappe_anfang, 0, True), (kappe_ende, ringe - 1, False)):
		if kappe is None:
			continue
		c = rahmen[i][0]
		if kappe == "spitz":
			c = c + rahmen[i][1] * (0.0 if umk else 0.0)
		mitte = t.vert(c)
		for j in range(seg):
			k = (j + 1) % seg
			f = [vs[i][j], vs[i][k], mitte] if not umk else [vs[i][k], vs[i][j], mitte]
			t.flaeche(f, material_name)
	return vs


# ---------------------------------------------------------------- Teil (bmesh je Materialien)


class Teil:
	def __init__(self, name):
		self.name = name
		self.bm = bmesh.new()
		self.slots = []

	def slot(self, m):
		if m not in self.slots:
			self.slots.append(m)
		return self.slots.index(m)

	def vert(self, co):
		return self.bm.verts.new(co)

	def flaeche(self, verts, m):
		f = self.bm.faces.new(verts)
		f.material_index = self.slot(m)
		return f

	def objekt(self, glatt_winkel=40.0):
		bm = self.bm
		bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
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


# ---------------------------------------------------------------- Objekt-Werkzeuge


def anwenden(ob, mod_typ, **werte):
	"""Modifikator anlegen und sofort in das Netz übernehmen (ohne Operator-Kontext)."""
	mod = ob.modifiers.new("m", mod_typ)
	for k, v in werte.items():
		setattr(mod, k, v)
	dg = bpy.context.evaluated_depsgraph_get()
	ev = ob.evaluated_get(dg)
	me = bpy.data.meshes.new_from_object(ev)
	alt = ob.data
	ob.modifiers.clear()
	ob.data = me
	bpy.data.meshes.remove(alt)
	return ob


def dicke(ob, d, versatz=1.0, rand=True):
	return anwenden(ob, "SOLIDIFY", thickness=d, offset=versatz, use_rim=rand, use_even_offset=True)


def fase(ob, breite, segmente=2, winkel=35.0):
	return anwenden(ob, "BEVEL", width=breite, segments=segmente, limit_method="ANGLE",
		angle_limit=math.radians(winkel), harden_normals=False)


def unterteilen(ob, stufen=1):
	return anwenden(ob, "SUBSURF", levels=stufen, render_levels=stufen)


def schneiden(ob, punkt, normale, weg_aussen=True):
	"""Schneidet mit einer Ebene; entfernt die Seite, in die die Normale zeigt (weg_aussen)."""
	bm = bmesh.new()
	bm.from_mesh(ob.data)
	geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
	bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(punkt), plane_no=Vector(normale).normalized(),
		clear_outer=weg_aussen, clear_inner=not weg_aussen, dist=1e-5)
	bm.to_mesh(ob.data)
	bm.free()
	return ob


def schneiden_fn(ob, behalten):
	"""Entfernt Flächen, deren Mittelpunkt behalten(Vector) = False liefert."""
	bm = bmesh.new()
	bm.from_mesh(ob.data)
	weg = [f for f in bm.faces if not behalten(f.calc_center_median())]
	bmesh.ops.delete(bm, geom=weg, context="FACES")
	bm.to_mesh(ob.data)
	bm.free()
	return ob


def verformen(ob, fn):
	"""fn(Vector) -> Vector für jeden Punkt."""
	for v in ob.data.vertices:
		v.co = fn(v.co.copy())
	ob.data.update()
	return ob


def spiegeln_x(ob):
	"""Kopie gespiegelt an X (linke -> rechte Seite)."""
	neu = ob.copy()
	neu.data = ob.data.copy()
	bpy.context.scene.collection.objects.link(neu)
	me = neu.data
	for v in me.vertices:
		v.co.x = -v.co.x
	bm = bmesh.new()
	bm.from_mesh(me)
	bmesh.ops.reverse_faces(bm, faces=bm.faces)
	bm.to_mesh(me)
	bm.free()
	return neu


def vereinen(obs, name):
	obs = [o for o in obs if o is not None]
	bm = bmesh.new()
	slots = []
	for o in obs:
		mats = [m.name for m in o.data.materials]
		for m in mats:
			if m not in slots:
				slots.append(m)
		tmp = bmesh.new()
		tmp.from_mesh(o.data)
		tmp.transform(o.matrix_world)
		for f in tmp.faces:
			f.material_index = slots.index(mats[f.material_index]) if mats else 0
		me = bpy.data.meshes.new("tmp")
		tmp.to_mesh(me)
		tmp.free()
		bm.from_mesh(me)
		bpy.data.meshes.remove(me)
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	for m in slots:
		me.materials.append(material(m))
	ob = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(ob)
	for o in obs:
		bpy.data.objects.remove(o)
	return ob


def material_setzen(ob, name):
	ob.data.materials.clear()
	ob.data.materials.append(material(name))
	for p in ob.data.polygons:
		p.material_index = 0
	return ob


def glatt(ob, winkel=40.0):
	for p in ob.data.polygons:
		p.use_smooth = True
	ob.data.set_sharp_from_angle(angle=math.radians(winkel))
	return ob


def roehre_objekt(name, rahmen, r, material_name, **kw):
	t = Teil(name)
	roehre_mesh(t, rahmen, r, material_name, **kw)
	return t.objekt()


# ---------------------------------------------------------------- Kleinteile


def niete(t, punkt, normale, r=0.006, material_name="niete"):
	"""Halbkugel-Niete auf einer Fläche."""
	n = Vector(normale).normalized()
	a = n.orthogonal().normalized()
	b = n.cross(a)
	ringe = [(0.0, r), (0.4, r * 0.92), (0.75, r * 0.65), (0.95, r * 0.3)]
	seg = 8
	vs = []
	for h, rr in ringe:
		ring = []
		for j in range(seg):
			w = 2 * math.pi * j / seg
			ring.append(t.vert(Vector(punkt) + n * (h * r * 0.8) + (a * math.cos(w) + b * math.sin(w)) * rr))
		vs.append(ring)
	for i in range(len(vs) - 1):
		for j in range(seg):
			k = (j + 1) % seg
			t.flaeche([vs[i][j], vs[i][k], vs[i + 1][k], vs[i + 1][j]], material_name)
	spitze = t.vert(Vector(punkt) + n * r * 0.85)
	for j in range(seg):
		t.flaeche([vs[-1][j], vs[-1][(j + 1) % seg], spitze], material_name)


def oberflaeche(ob, start, richtung, weite=0.5):
	"""Strahl gegen ein Objekt: (Punkt, Normale) oder None."""
	bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
	hit = bvh.ray_cast(Vector(start), Vector(richtung).normalized(), weite)
	if hit[0] is None:
		return None
	return hit[0], hit[1]


# ---------------------------------------------------------------- Radiusfeld und Platten


class Feld:
	"""Abgetastete Körperoberfläche um eine Achse, geglättet und wahlweise konvex.
	radius(s, w): Radius an Achsposition s (Meter) und Winkel w (0 = vorne)."""

	def __init__(self, koerper_bvh, achse, ringe=60, seg=64, r_max=0.45, konvex_anteil=1.0, glatt=(3, 2),
			s0=0.0, s1=None, monoton=0):
		self.achse = achse
		self.s0 = s0
		self.s1 = achse.laenge() if s1 is None else s1
		r, _ = roehre_abtasten(koerper_bvh, achse, ringe, seg, r_max, self.s0, self.s1)
		r = lueckenfuellen(r)
		roh = r.copy()
		if konvex_anteil > 0:
			r = konvex(r, konvex_anteil)
		r = glaetten(r, *glatt)
		# nie unter die abgetastete Haut (Glätten senkt Spitzen ab)
		for _ in range(3):
			r = np.maximum(r, roh)
			r = np.maximum(r, glaetten(r, 1, 1))
		if monoton:
			r = aufwaerts_monoton(r, monoton)
		self.r = r
		self.ringe, self.seg = r.shape

	def radius(self, s, w):
		u = (s - self.s0) / max(1e-9, self.s1 - self.s0) * (self.ringe - 1)
		u = min(max(u, 0.0), self.ringe - 1.0)
		i0 = int(math.floor(u))
		i1 = min(i0 + 1, self.ringe - 1)
		fu = u - i0
		v = (w % (2 * math.pi)) / (2 * math.pi) * self.seg
		j0 = int(math.floor(v)) % self.seg
		j1 = (j0 + 1) % self.seg
		fv = v - math.floor(v)
		r = self.r
		return (r[i0, j0] * (1 - fu) * (1 - fv) + r[i1, j0] * fu * (1 - fv) + r[i0, j1] * (1 - fu) * fv
			+ r[i1, j1] * fu * fv)

	def punkt(self, s, w, extra=0.0):
		c, t, n, b = self.achse.rahmen(s)
		d = n * math.cos(w) + b * math.sin(w)
		return c + d * (self.radius(s, w) + extra)

	def normale(self, s, w, extra=0.0, h=0.004):
		p = self.punkt(s, w, extra)
		ps = self.punkt(s + h, w, extra) - self.punkt(s - h, w, extra)
		pw = self.punkt(s, w + h * 4, extra) - self.punkt(s, w - h * 4, extra)
		n = pw.cross(ps)
		c, t, nn, b = self.achse.rahmen(s)
		d = nn * math.cos(w) + b * math.sin(w)
		if n.dot(d) < 0:
			n = -n
		return n.normalized()


def _wert(f, *a):
	return f(*a) if callable(f) else f


def platte(t, feld, s_von, s_bis, abstand=0.0, nu=16, nw=64, w_von=0.0, w_bis=2 * math.pi, extra=None,
		material_name="platte", kappe_bis=False, kappe_von=False):
	"""Fläche auf dem Feld zwischen s_von(w) und s_bis(w) (Zahlen oder Funktionen von w).
	Volle Runde (w_bis - w_von = 2π) wird geschlossen. extra(s, w) addiert Radius (Grate, Wülste)."""
	zu = abs((w_bis - w_von) - 2 * math.pi) < 1e-6
	spalten = nw if zu else nw + 1
	gitter = []
	for j in range(spalten):
		w = w_von + (w_bis - w_von) * j / nw
		a, b = _wert(s_von, w), _wert(s_bis, w)
		zeile = []
		for i in range(nu + 1):
			s = a + (b - a) * i / nu
			e = (abstand(s, w) if callable(abstand) else abstand) + (extra(s, w) if extra else 0.0)
			zeile.append(t.vert(feld.punkt(s, w, e)))
		gitter.append(zeile)
	for j in range(nw):
		k = (j + 1) % spalten
		for i in range(nu):
			t.flaeche([gitter[j][i], gitter[j][i + 1], gitter[k][i + 1], gitter[k][i]], material_name)
	if kappe_bis:
		c = t.vert(feld.achse.punkt(_wert(s_bis, 0.0)))
		for j in range(nw):
			k = (j + 1) % spalten
			t.flaeche([gitter[j][nu], c, gitter[k][nu]], material_name)
	if kappe_von:
		c = t.vert(feld.achse.punkt(_wert(s_von, 0.0)))
		for j in range(nw):
			k = (j + 1) % spalten
			t.flaeche([gitter[k][0], c, gitter[j][0]], material_name)
	return gitter


def rand_punkte(feld, s_fn, abstand, w_von=0.0, w_bis=2 * math.pi, n=96, extra=None):
	pts = []
	zu = abs((w_bis - w_von) - 2 * math.pi) < 1e-6
	for j in range(n if zu else n + 1):
		w = w_von + (w_bis - w_von) * j / n
		s = _wert(s_fn, w)
		e = (abstand(s, w) if callable(abstand) else abstand) + (extra(s, w) if extra else 0.0)
		pts.append(feld.punkt(s, w, e))
	return pts, zu


def zug(t, pts, radius, material_name="rand", zu=False, seg=8, flach=1.0, aussen=None):
	"""Rohr entlang einer Punktfolge (Wulst, Riemen, Naht). flach < 1 drückt das Rohr flach (Riemen).
	aussen: Funktion Punkt -> Richtung nach außen, damit Riemen auf der Fläche liegen."""
	n = len(pts)
	ringe = []
	for i in range(n):
		if zu:
			a, b = pts[(i - 1) % n], pts[(i + 1) % n]
		else:
			a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
		tg = (b - a).normalized()
		if aussen is not None:
			o = aussen(pts[i])
			o = (o - tg * o.dot(tg)).normalized()
		else:
			o = tg.orthogonal().normalized()
		q = tg.cross(o)
		ring = []
		for j in range(seg):
			w = 2 * math.pi * j / seg
			ring.append(t.vert(pts[i] + o * math.cos(w) * radius * flach + q * math.sin(w) * radius))
		ringe.append(ring)
	for i in range(n if zu else n - 1):
		r0, r1 = ringe[i], ringe[(i + 1) % n]
		for j in range(seg):
			k = (j + 1) % seg
			t.flaeche([r0[j], r1[j], r1[k], r0[k]], material_name)
	if not zu:
		for ring, umk in ((ringe[0], True), (ringe[-1], False)):
			c = t.vert(sum((v.co for v in ring), Vector()) / seg)
			for j in range(seg):
				k = (j + 1) % seg
				t.flaeche([ring[k], ring[j], c] if not umk else [ring[j], ring[k], c], material_name)
	return ringe


def nieten_reihe(t, feld, s_fn, abstand, w_liste, r=0.006, material_name="niete", extra=None):
	for w in w_liste:
		s = _wert(s_fn, w)
		e = abstand + (extra(s, w) if extra else 0.0)
		niete(t, feld.punkt(s, w, e), feld.normale(s, w, e), r, material_name)


def weich(x, a, b):
	"""Glatter Übergang 0 -> 1 zwischen a und b."""
	t = min(max((x - a) / (b - a), 0.0), 1.0)
	return t * t * (3 - 2 * t)


def wdiff(w, ziel):
	"""Kleinster Winkelabstand."""
	d = (w - ziel + math.pi) % (2 * math.pi) - math.pi
	return abs(d)


class Kugelfeld:
	"""Körperoberfläche von einem Mittelpunkt aus abgetastet (Helm, Schulterkappe, Knie, Ellbogen).
	s = Winkel vom Pol (0 … π), w = Winkel um den Pol (0 = vorne)."""

	def __init__(self, koerper_bvh, mitte, pol, vorne=VORNE, ringe=48, seg=72, r_max=0.4, phi_max=PI_HALB * 2,
			huelle=6, glatt=(2, 2), r_min=0.0):
		self.c = Vector(mitte)
		self.t = Vector(pol).normalized()
		v = Vector(vorne) - self.t * Vector(vorne).dot(self.t)
		self.n = v.normalized()
		self.b = self.t.cross(self.n)
		self.s0, self.s1 = 0.0, phi_max
		r = np.full((ringe, seg), np.nan)
		for i in range(ringe):
			phi = phi_max * i / (ringe - 1)
			for j in range(seg):
				d = self.richtung(phi, 2 * math.pi * j / seg)
				hit = koerper_bvh.ray_cast(self.c + d * r_max, -d, r_max)
				if hit[0] is not None:
					r[i, j] = r_max - hit[3]
		r = lueckenfuellen(r, 0.1)
		r = np.maximum(r, r_min)
		for _ in range(huelle):
			r = np.maximum(r, glaetten(r, 2, 2))
		self.r = glaetten(r, *glatt)
		self.ringe, self.seg = self.r.shape

	def richtung(self, phi, w):
		quer = self.n * math.cos(w) + self.b * math.sin(w)
		return self.t * math.cos(phi) + quer * math.sin(phi)

	radius = Feld.radius

	def punkt(self, s, w, extra=0.0):
		return self.c + self.richtung(s, w) * (self.radius(s, w) + extra)

	def normale(self, s, w, extra=0.0, h=0.01):
		ps = self.punkt(s + h, w, extra) - self.punkt(s - h, w, extra)
		pw = self.punkt(s, w + h, extra) - self.punkt(s, w - h, extra)
		n = pw.cross(ps)
		if n.dot(self.richtung(s, w)) < 0:
			n = -n
		return n.normalized()


def huelle_aus_koerper(K, namen, schwelle, abstand, name, material_name, behalten=None, glatt_schritte=3):
	"""Körperfläche (Hand, Fuß) um 'abstand' entlang geglätteter Normalen aufblasen.
	behalten(Punkt) filtert Dreiecke (z. B. nur bis zum Handgelenk)."""
	a = K.anteil(namen)
	dr = K.dreiecke
	ok = (a[dr] >= schwelle).all(axis=1)
	if behalten is not None:
		ok &= np.array([behalten(Vector(c)) for c in K.p[dr].mean(axis=1)])
	dr = dr[ok][:, [0, 2, 1]]   # Körperdreiecke sind im Godot-Umlaufsinn gespeichert
	idx, inv = np.unique(dr, return_inverse=True)
	p = K.p[idx].copy()
	f = inv.reshape(-1, 3)
	# Normalen je Punkt
	fn = np.cross(p[f[:, 1]] - p[f[:, 0]], p[f[:, 2]] - p[f[:, 0]])
	nrm = np.zeros_like(p)
	for k in range(3):
		np.add.at(nrm, f[:, k], fn)
	# Nachbarschaft für Glättung
	nb = [set() for _ in range(len(p))]
	for a_, b_, c_ in f:
		nb[a_] |= {b_, c_}
		nb[b_] |= {a_, c_}
		nb[c_] |= {a_, b_}
	nb = [list(x) for x in nb]
	for _ in range(glatt_schritte):
		nrm = np.array([nrm[i] + nrm[n].sum(0) * 0.5 for i, n in enumerate(nb)])
	nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
	q = p + nrm * (abstand if not callable(abstand) else np.array([abstand(Vector(x)) for x in p])[:, None])
	me = bpy.data.meshes.new(name)
	me.from_pydata(q.tolist(), [], f.tolist())
	me.update()
	me.materials.append(material(material_name))
	ob = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(ob)
	glatt(ob, 70)
	return ob


def box_uv(ob, massstab=1.0):
	"""UVs per Würfelprojektion (1 UV-Einheit = 1/massstab Meter), für Kacheltexturen (Kette, Stoff, Leder)."""
	bm = bmesh.new()
	bm.from_mesh(ob.data)
	uv = bm.loops.layers.uv.verify()
	for f in bm.faces:
		n = f.normal
		ax = max(range(3), key=lambda i: abs(n[i]))
		for l in f.loops:
			c = l.vert.co
			if ax == 0:
				l[uv].uv = (c.y * massstab, c.z * massstab)
			elif ax == 1:
				l[uv].uv = (c.x * massstab, c.z * massstab)
			else:
				l[uv].uv = (c.x * massstab, c.y * massstab)
	bm.to_mesh(ob.data)
	bm.free()
	return ob


def verringern(ob, max_flaechen=14000):
	n = len(ob.data.polygons)
	if n > max_flaechen:
		anwenden(ob, "DECIMATE", ratio=max_flaechen / n, use_collapse_triangulate=True)
	return ob
