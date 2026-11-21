"""Bausteine für Tiermodelle: Körper als weiche Vereinigung einfacher Formen (Kapseln, Ellipsoide),
abgetastet als Abstandsfeld und mit Marching Cubes zu einem geschlossenen Netz gemacht.
Danach Fellsträhnen (Verschiebung entlang der Normalen), Fellfarbe als Punktfarbe und ein Skelett mit automatischen Gewichten.

Koordinaten wie bei den Menschen: Blender, Z oben, Blick nach -Y, Meter, Boden bei z = 0.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector, noise
from skimage.measure import marching_cubes


def _smin(a, b, k):
	if k <= 0:
		return np.minimum(a, b)
	h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
	return b * (1 - h) + a * h - k * h * (1 - h)


def _smax(a, b, k):
	return -_smin(-a, -b, k)


class Form:
	"""Sammlung von Formen. Jede Form: (sdf-Funktion, k, abziehen, bbox)."""

	def __init__(self):
		self.teile = []

	def kapsel(self, a, b, ra, rb=None, k=0.03, weg=False):
		a, b = np.array(a, float), np.array(b, float)
		rb = ra if rb is None else rb

		def f(P):
			ba = b - a
			t = np.clip(((P - a) @ ba) / max(1e-9, ba @ ba), 0.0, 1.0)
			q = a + t[:, None] * ba
			return np.linalg.norm(P - q, axis=1) - (ra + (rb - ra) * t)
		m = max(ra, rb)
		self.teile.append((f, k, weg, np.minimum(a, b) - m, np.maximum(a, b) + m))

	def kette(self, punkte, radien, k=0.03):
		for i in range(len(punkte) - 1):
			self.kapsel(punkte[i], punkte[i + 1], radien[i], radien[i + 1], k)

	def ellipsoid(self, c, r, k=0.03, weg=False, kipp=0.0):
		"""Ellipsoid um c mit Halbachsen r, um die x-Achse gekippt (Bogenmaß, positiv = Vorderseite hoch)."""
		c, r = np.array(c, float), np.array(r, float)
		cs, sn = math.cos(kipp), math.sin(kipp)

		def f(P):
			d = P - c
			y = d[:, 1] * cs - d[:, 2] * sn
			z = d[:, 1] * sn + d[:, 2] * cs
			q = np.stack([d[:, 0], y, z], 1) / r
			l0 = np.linalg.norm(q, axis=1)
			l1 = np.linalg.norm(q / r, axis=1)
			return l0 * (l0 - 1.0) / np.maximum(l1, 1e-9)
		m = r.max()
		self.teile.append((f, k, weg, c - m, c + m))

	def spiegeln(self, fn, *args, **kw):
		"""Ruft fn für x und -x auf (Beine, Ohren, Augen). args mit Punkten [x, y, z] werden gespiegelt."""
		fn(*args, **kw)
		gesp = []
		for a in args:
			if isinstance(a, (list, tuple)) and len(a) and isinstance(a[0], (list, tuple)):
				gesp.append([[-p[0], p[1], p[2]] for p in a])
			elif isinstance(a, (list, tuple)) and len(a) == 3 and all(isinstance(v, (int, float)) for v in a):
				gesp.append([-a[0], a[1], a[2]])
			else:
				gesp.append(a)
		fn(*gesp, **kw)

	def netz(self, name, raster=0.006):
		lo = np.min([t[3] for t in self.teile], 0) - 0.03
		hi = np.max([t[4] for t in self.teile], 0) + 0.03
		n = np.ceil((hi - lo) / raster).astype(int) + 1
		d = np.full(tuple(n), 1e3)
		for f, k, weg, a, b in self.teile:
			# nur im Umfeld der Form rechnen (außerhalb ändert sie die Fläche nicht)
			r = k + 2 * raster + 0.01
			i0 = np.clip(np.floor((a - r - lo) / raster).astype(int), 0, n - 1)
			i1 = np.clip(np.ceil((b + r - lo) / raster).astype(int) + 1, 1, n)
			xs = [lo[j] + raster * np.arange(i0[j], i1[j]) for j in range(3)]
			G = np.stack(np.meshgrid(*xs, indexing="ij"), -1).reshape(-1, 3)
			blk = d[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]
			fd = f(G).reshape(blk.shape)
			d[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]] = _smax(blk, -fd, k) if weg else _smin(blk, fd, k)
		d = d.reshape(n)
		v, fl, _, _ = marching_cubes(d, 0.0, spacing=(raster,) * 3)
		v += lo
		me = bpy.data.meshes.new(name)
		me.from_pydata(v.tolist(), [], fl[:, ::-1].tolist())
		me.update()
		ob = bpy.data.objects.new(name, me)
		bpy.context.scene.collection.objects.link(ob)
		bm = bmesh.new()
		bm.from_mesh(me)
		bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=raster * 0.05)
		bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
		bm.to_mesh(me)
		bm.free()
		return ob


def glaetten(ob, schritte=2, faktor=0.5):
	m = ob.modifiers.new("glatt", "SMOOTH")
	m.factor, m.iterations = faktor, schritte
	bpy.context.view_layer.objects.active = ob
	bpy.ops.object.modifier_apply(modifier=m.name)


def verringern(ob, flaechen):
	n = len(ob.data.polygons)
	if n > flaechen:
		m = ob.modifiers.new("dec", "DECIMATE")
		m.ratio = flaechen / n
		bpy.context.view_layer.objects.active = ob
		bpy.ops.object.modifier_apply(modifier=m.name)


def fell(ob, staerke_fn, richtung=Vector((0, 1, -0.4)), saat=0, laenge=0.035):
	"""Fellsträhnen: Verschiebung nach außen, Rauschen gestreckt entlang der Wuchsrichtung.
	staerke_fn(p) -> Meter (Fellhöhe an diesem Punkt)."""
	me = ob.data
	me.update()
	n = len(me.vertices)
	P = np.empty(n * 3)
	N = np.empty(n * 3)
	me.vertices.foreach_get("co", P)
	me.vertices.foreach_get("normal", N)   # vorher lesen: jedes Ändern von co macht die Normalen ungültig
	P, N = P.reshape(-1, 3), N.reshape(-1, 3)
	r = richtung.normalized()
	o = Vector((saat * 3.1, saat * 7.7, saat * 1.3))
	for i in range(n):
		p = Vector(P[i])
		s = staerke_fn(p)
		if s <= 0:
			continue
		# Koordinaten quer zur Wuchsrichtung fein, entlang grob -> Strähnen
		entlang = p.dot(r)
		quer = p - r * entlang
		q = Vector((quer.x / 0.006, quer.y / 0.006 + entlang / laenge, quer.z / 0.006)) * 0.25 + o
		# Grate statt Buckel: 1 - |Rauschen| ergibt schmale Strähnen
		n1 = 1.0 - abs(noise.noise(q))
		n2 = 1.0 - abs(noise.noise(q * 2.1 + o))
		h = s * (0.35 + 0.45 * n1 ** 2 + 0.2 * n2 ** 2)
		P[i] += N[i] * max(0.0, h)
	me.vertices.foreach_set("co", P.ravel())
	me.update()


def farben(ob, farb_fn, name="Col"):
	"""Punktfarbe aus farb_fn(p, n) -> (r, g, b)."""
	me = ob.data
	attr = me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
	for i, v in enumerate(me.vertices):
		c = farb_fn(v.co, v.normal)
		attr.data[i].color = (c[0] ** 2.2, c[1] ** 2.2, c[2] ** 2.2, 1.0)   # sRGB -> linear
	me.color_attributes.active_color = attr
	return attr


def material(name, farbe=(0.5, 0.5, 0.5), rau=0.85, punktfarbe=False):
	m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
	m.diffuse_color = (*farbe, 1.0)
	m.roughness = rau
	m.use_nodes = True
	nt = m.node_tree
	bsdf = nt.nodes.get("Principled BSDF")
	bsdf.inputs["Base Color"].default_value = (*farbe, 1.0)
	bsdf.inputs["Roughness"].default_value = rau
	if punktfarbe:
		attr = nt.nodes.new("ShaderNodeVertexColor")
		attr.layer_name = "Col"
		nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
	return m


def kugel(name, c, r, mat, seg=16):
	bm = bmesh.new()
	bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
	for v in bm.verts:
		v.co += Vector(c)
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	for p in me.polygons:
		p.use_smooth = True
	me.materials.append(mat)
	ob = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(ob)
	return ob


def skelett(name, knochen):
	"""knochen: Liste (name, kopf, ende, eltern). Gibt das Armature-Objekt zurück."""
	arm = bpy.data.armatures.new(name)
	ob = bpy.data.objects.new(name, arm)
	bpy.context.scene.collection.objects.link(ob)
	bpy.context.view_layer.objects.active = ob
	bpy.ops.object.mode_set(mode="EDIT")
	eb = {}
	for n, kopf, ende, eltern in knochen:
		b = arm.edit_bones.new(n)
		b.head, b.tail = Vector(kopf), Vector(ende)
		if eltern:
			b.parent = eb[eltern]
			b.use_connect = (Vector(kopf) - eb[eltern].tail).length < 1e-4
		eb[n] = b
	bpy.ops.object.mode_set(mode="OBJECT")
	return ob


def binden(netz_obs, arm):
	"""Automatische Gewichte (Wärmeverteilung) für alle Netze."""
	bpy.ops.object.select_all(action="DESELECT")
	for o in netz_obs:
		o.select_set(True)
	arm.select_set(True)
	bpy.context.view_layer.objects.active = arm
	bpy.ops.object.parent_set(type="ARMATURE_AUTO")


def bilder(pfad, objekte, groesse=(560, 420), ansichten=((90, "s"), (35, "vs"), (0, "v"), (215, "hs")), farbe_punkte=True):
	"""Workbench-Bilder mit Punktfarben aus mehreren Richtungen, nebeneinander zu einem Bild."""
	from PIL import Image
	import os
	sc = bpy.context.scene
	sc.render.engine = "BLENDER_WORKBENCH"
	sh = sc.display.shading
	sh.light = "STUDIO"
	sh.color_type = "VERTEX" if farbe_punkte else "MATERIAL"
	sh.show_cavity = True
	sh.cavity_type = "BOTH"
	sh.show_specular_highlight = False
	sc.render.resolution_x, sc.render.resolution_y = groesse
	if sc.world is None:
		sc.world = bpy.data.worlds.new("w")
	sc.world.color = (0.32, 0.33, 0.35)
	bpy.context.view_layer.update()
	pts = np.concatenate([np.array([o.matrix_world @ v.co for v in o.data.vertices]) for o in objekte])
	lo, hi = pts.min(0), pts.max(0)
	mitte = Vector(((lo + hi) / 2).tolist())
	ausdehnung = float(np.linalg.norm(hi - lo))
	cam = bpy.data.objects.new("Kamera", bpy.data.cameras.new("Kamera"))
	sc.collection.objects.link(cam)
	sc.camera = cam
	cam.data.type = "ORTHO"
	breit = float(max(hi[0] - lo[0], hi[1] - lo[1]))
	cam.data.ortho_scale = max(breit, float(hi[2] - lo[2]) * groesse[0] / groesse[1]) * 1.1
	teile = []
	for winkel, n in ansichten:
		w = math.radians(winkel)
		cam.location = mitte + Vector((math.sin(w) * 5, -math.cos(w) * 5, 0.9))
		cam.rotation_euler = (math.pi / 2 - math.atan2(0.9, 5), 0, w)
		f = pfad + "_" + n + ".png"
		sc.render.filepath = f
		bpy.ops.render.render(write_still=True)
		teile.append(Image.open(f).convert("RGB"))
		os.remove(f)
	g = Image.new("RGB", (sum(t.width for t in teile), teile[0].height))
	x = 0
	for t in teile:
		g.paste(t, (x, 0))
		x += t.width
	g.save(pfad + ".png")
	return pfad + ".png"
