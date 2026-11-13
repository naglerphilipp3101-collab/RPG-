"""Vorschaubild eines Satzes auf einem beliebigen Körper (angepasst, verdeckte Haut ausgeblendet).

python3 passform_bild.py -- <glb-ordner> <satz> <ausgabe-ohne-endung> ['{"geschlecht":0}'] ['{"h":[1.3,1.7]}']
"""
import json
import os
import sys

import bpy
import numpy as np

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.join(HIER, "..", "..", "assets", "ruestung", "blender"))
import anpassen as ap  # noqa: E402
from mensch_lesen import Mensch  # noqa: E402

SLOTS = ["kopf", "brust", "haende", "beine", "fuesse"]


def netz(name, p_mh, dr, mats):
	import rgeo
	p = np.stack([p_mh[:, 0], -p_mh[:, 2], p_mh[:, 1]], 1)       # MakeHuman/glTF -> Blender
	me = bpy.data.meshes.new(name)
	me.from_pydata(p.tolist(), [], dr.tolist())
	me.update()
	namen = list(dict.fromkeys(mats))
	for n in namen:
		me.materials.append(rgeo.material(n))
	mi = np.array([namen.index(m) for m in mats])
	me.polygons.foreach_set("material_index", mi)
	me.polygons.foreach_set("use_smooth", np.ones(len(dr), bool))
	import bmesh
	bm = bmesh.new()
	bm.from_mesh(me)
	bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)      # UV-Nähte zusammenführen (sonst kantige Schattierung)
	bm.to_mesh(me)
	bm.free()
	me.set_sharp_from_angle(angle=0.6)
	ob = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(ob)
	return ob


_CACHE = {}


def satz_auf_koerper(ordner, satz, aussehen, m=None, k0=None, slots=SLOTS):
	m = m or Mensch()
	k0 = k0 or ap.Koerper(m)
	k = ap.Koerper(m, aussehen)
	weg = np.zeros(len(k.p), bool)
	for slot in slots:
		pf = os.path.join(ordner, "iron_%s_%s.glb" % (satz, slot))
		if pf not in _CACHE:
			p, dr, mat, _ = ap.glb_netz(pf)
			_CACHE[pf] = (p, dr, mat, ap.bindung(p, k0.p), ap.verdeckt(k0.p, k0.n, k0.dreiecke, p, dr))
		p, dr, mat, bind, verd = _CACHE[pf]
		pos = ap.anwenden(p, bind, k0.p, k.p)
		weg |= verd
		netz("iron_%s_%s" % (satz, slot), pos, dr, mat)
	sichtbar = ~weg[k.dreiecke].all(1)
	netz("Koerper", k.p, k.dreiecke[sichtbar], [os.environ.get("HAUT", "haut")] * int(sichtbar.sum()))
	return k


def main():
	a = sys.argv[sys.argv.index("--") + 1:]
	ordner, satz, aus = a[:3]
	aussehen = json.loads(a[3]) if len(a) > 3 else {}
	opt = json.loads(a[4]) if len(a) > 4 else {}
	bpy.ops.wm.read_factory_settings(use_empty=True)
	satz_auf_koerper(ordner, satz, aussehen, slots=opt.get("slots", SLOTS))
	import vorschau
	vorschau.bilder(aus, hoehe=tuple(opt.get("h", (-0.02, 1.9))), groesse=tuple(opt.get("g", (360, 560))),
		mitte_x=opt.get("x", 0.0), ansichten=[tuple(x) for x in opt.get("a", [(0, "v"), (90, "s"), (180, "h"), (35, "vs")])])


if __name__ == "__main__":
	main()
