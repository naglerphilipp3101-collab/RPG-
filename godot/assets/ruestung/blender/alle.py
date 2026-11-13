"""Baut Iron-Teile, speichert Vorschaubilder je Satz und exportiert jedes Teil als GLB.

python3 alle.py -- <ausgabe> [schwer,mittel,leicht]      Grundsätze (Klassen)
python3 alle.py -- <ausgabe> waffen [axe,bow,...]         Waffensätze (ohne Liste: alle 15)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import rgeo as g, vorschau, iron, waffensaetze as ws, nachbearbeitung as nb

ARG = sys.argv[sys.argv.index("--") + 1:]
AUS = ARG[0]
WAFFEN = len(ARG) > 1 and ARG[1] == "waffen"
if WAFFEN:
	SAETZE = ARG[2].split(",") if len(ARG) > 2 else list(ws.SAETZE)
else:
	SAETZE = ARG[1].split(",") if len(ARG) > 1 else ["schwer", "mittel", "leicht"]
MAX = int(os.environ.get("MAX_FL", "14000"))
SLOTS = ["kopf", "brust", "haende", "beine", "fuesse"]
os.makedirs(AUS, exist_ok=True)
for satz in SAETZE:
	bpy.ops.wm.read_factory_settings(use_empty=True)
	K = g.Koerper()
	koerper = K.objekt()
	obs = []
	if WAFFEN:
		teile = ws.bauen(K, satz)
	else:
		teile = {slot: getattr(iron, satz + "_" + slot)(K) for slot in SLOTS}
	for slot in SLOTS:
		ob = teile[slot]
		ob.name = ob.data.name = "iron_%s_%s" % (satz, slot)
		if os.environ.get("NACH", "1") == "1":
			nb.bearbeiten(ob, K, slot)
		g.verringern(ob, max(MAX * (2 if slot in ("brust", "beine") else 1), int(ob.get("max_fl", 0))))
		g.box_uv(ob)
		obs.append(ob)
		# Ausreißer-Prüfung: nichts darf weit außerhalb des Körpers liegen
		p = np.array([v.co for v in ob.data.vertices])
		if p[:, 2].min() < -0.05 or p[:, 2].max() > 2.05 or np.abs(p[:, :2]).max() > 1.0:
			print("WARNUNG Ausreißer in", ob.name, p.min(0), p.max(0))
		print(ob.name, len(ob.data.vertices), "Punkte", len(ob.data.polygons), "Flächen")
	vorschau.bilder(os.path.join(AUS, "iron_" + satz), hoehe=(-0.02, 1.9), groesse=(400, 620),
		ansichten=[(0, "v"), (90, "s"), (180, "h"), (35, "vs")])
	for ob in obs + [koerper]:
		bpy.ops.object.select_all(action="DESELECT")
		ob.select_set(True)
		bpy.context.view_layer.objects.active = ob
		bpy.ops.export_scene.gltf(filepath=os.path.join(AUS, ob.name + ".glb"), use_selection=True,
			export_format="GLB", export_materials="EXPORT", export_yup=True, export_apply=True)
