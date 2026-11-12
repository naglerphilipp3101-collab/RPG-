"""Baut alle Iron-Teile, speichert Vorschaubilder je Klasse und exportiert sie (GLB für die Browser-Vorschau)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import rgeo as g, vorschau, iron

AUS = sys.argv[sys.argv.index("--") + 1]
KLASSEN = sys.argv[sys.argv.index("--") + 2].split(",") if len(sys.argv) > sys.argv.index("--") + 2 else ["schwer", "mittel", "leicht"]
MAX = int(os.environ.get("MAX_FL", "14000"))
SLOTS = ["kopf", "brust", "haende", "beine", "fuesse"]
os.makedirs(AUS, exist_ok=True)
for klasse in KLASSEN:
	bpy.ops.wm.read_factory_settings(use_empty=True)
	K = g.Koerper()
	koerper = K.objekt()
	obs = []
	for slot in SLOTS:
		ob = getattr(iron, klasse + "_" + slot)(K)
		ob.name = "iron_%s_%s" % (klasse, slot)
		g.verringern(ob, MAX)
		g.box_uv(ob)
		obs.append(ob)
		print(ob.name, len(ob.data.vertices), "Punkte", len(ob.data.polygons), "Flächen")
	vorschau.bilder(os.path.join(AUS, "iron_" + klasse), hoehe=(-0.02, 1.9), groesse=(400, 620),
		ansichten=[(0, "v"), (90, "s"), (180, "h"), (35, "vs")])
	for ob in obs + [koerper]:
		bpy.ops.object.select_all(action="DESELECT")
		ob.select_set(True)
		bpy.context.view_layer.objects.active = ob
		bpy.ops.export_scene.gltf(filepath=os.path.join(AUS, ob.name + ".glb"), use_selection=True,
			export_format="GLB", export_materials="EXPORT", export_yup=True, export_apply=True)
