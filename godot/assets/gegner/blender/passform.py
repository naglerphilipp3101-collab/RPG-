"""Passt die um den Standard-Mann gebauten Teile an einen anderen Körper an (gleiche Rechnung wie die Rüstung,
tools/ruestung/anpassen.py) und baut den sichtbaren Körper ohne verdeckte Haut."""
import bmesh
import bpy
import numpy as np

import anpassen as ap
from kleidung import g


def _dreiecke(ob):
	bm = bmesh.new()
	bm.from_mesh(ob.data)
	bmesh.ops.triangulate(bm, faces=bm.faces)
	bm.to_mesh(ob.data)
	bm.free()
	p = np.array([v.co[:] for v in ob.data.vertices])
	dr = np.array([pl.vertices[:] for pl in ob.data.polygons], np.int64).reshape(-1, 3)
	return p, dr


def anpassen(K, obs, aussehen):
	"""Verschiebt obs auf den Körper 'aussehen', legt den Körper an und gibt seine Höhe (m) zurück."""
	k0 = ap.Koerper(K.m)
	k = ap.Koerper(K.m, aussehen)
	weg = np.zeros(len(k.p), bool)
	for ob in obs:
		p_bl, dr = _dreiecke(ob)
		p = g.bl_zu_mh(p_bl)
		bind = ap.bindung(p, k0.p)
		weg |= ap.verdeckt(k0.p, k0.n, k0.dreiecke, p, dr)
		neu = g.mh_zu_bl(ap.anwenden(p, bind, k0.p, k.p))
		ob.data.vertices.foreach_set("co", neu.astype(np.float32).ravel())
		ob.data.update()
	sichtbar = ~weg[k.dreiecke].all(1)
	me = bpy.data.meshes.new("Koerper")
	me.from_pydata(g.mh_zu_bl(k.p).tolist(), [], k.dreiecke[sichtbar].tolist())
	me.update()
	me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
	me.materials.append(g.material("haut"))
	ob = bpy.data.objects.new("Koerper", me)
	bpy.context.scene.collection.objects.link(ob)
	return float(g.mh_zu_bl(k.p)[:, 2].max())
