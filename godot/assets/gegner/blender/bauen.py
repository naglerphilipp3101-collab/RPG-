"""Baut menschliche Gegnertypen aus gegner_typen.py, rendert Vorschaubilder und exportiert (mit GLB=1) je Slot ein GLB.

python3 bauen.py -- <ausgabe> [typ,typ,...]      ohne Liste: alle Typen
Bild: <ausgabe>/<typ>.png (vorne, schräg, hinten). GLB: <ausgabe>/<typ>_<slot>.glb
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import kleidung as kl  # noqa: E402
import gegner_typen as gt  # noqa: E402
from kleidung import g  # noqa: E402
import vorschau  # noqa: E402
import nachbearbeitung as nb  # noqa: E402
import passform  # noqa: E402

ARG = sys.argv[sys.argv.index("--") + 1:]
AUS = ARG[0]
TYPEN = ARG[1].split(",") if len(ARG) > 1 else list(gt.TYPEN)
os.makedirs(AUS, exist_ok=True)
MAX = int(os.environ.get("MAX_FL", "14000"))


def farben(werte):
	for m in bpy.data.materials:
		if m.name in werte:
			c = werte[m.name]
			m.diffuse_color = (*c, 1.0)
			if m.node_tree and m.node_tree.nodes.get("Principled BSDF"):
				m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*c, 1.0)


for typ in TYPEN:
	d = gt.TYPEN[typ]
	bpy.ops.wm.read_factory_settings(use_empty=True)
	aussehen = dict(gt.GRUND)
	aussehen.update(d.get("aussehen", {}))
	K = g.Koerper()   # gebaut wird wie die Rüstung um den Standard-Mann, angepasst wird danach
	obs = []
	for slot in gt.SLOTS:
		bau = d["slots"].get(slot)
		if bau is None:
			continue
		teile = bau(K)
		if d.get("zerreissen"):
			kl.zerreissen(teile, saat=hash(typ + slot) % 97, **d["zerreissen"])
		ob = g.vereinen(teile, "%s_%s" % (typ, slot))
		if os.environ.get("NACH", "1") == "1":
			nb.bearbeiten(ob, K, slot)
		g.verringern(ob, MAX * (2 if slot in ("brust", "beine") else 1))
		g.box_uv(ob)
		obs.append(ob)
		print(ob.name, len(ob.data.polygons), "Flächen")
	hoehe = passform.anpassen(K, obs, aussehen)
	farben({"haut": gt.HAUT[d.get("haut", "normal")]})
	farben(d.get("farben", {}))
	vorschau.bilder(os.path.join(AUS, typ), hoehe=(-0.02, max(1.98, hoehe + 0.06)), groesse=(360, 580),
		ansichten=[(0, "v"), (35, "vs"), (180, "h")])
	if os.environ.get("GLB") == "1":
		for ob in obs:
			bpy.ops.object.select_all(action="DESELECT")
			ob.select_set(True)
			bpy.context.view_layer.objects.active = ob
			bpy.ops.export_scene.gltf(filepath=os.path.join(AUS, ob.name + ".glb"), use_selection=True,
				export_format="GLB", export_materials="EXPORT", export_yup=True, export_apply=True)
