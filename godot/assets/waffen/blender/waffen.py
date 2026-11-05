"""Erzeugt die modularen Waffenteile als .glb für Godot.
Aufruf: python waffen.py -- <zielordner> [waffe ...]
Ergebnis: <zielordner>/<waffe>/<teil>_t<tier>_<form>.glb. Ohne Angabe werden alle Waffen gebaut."""
import bpy, sys, os, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import *

# Waffen sind modular: jede Waffe besteht aus Teilen (z. B. Klinge, Parierstange, Griff, Knauf).
# Jedes Tier (1 Iron bis 6 Darksteel) bringt eigene Module in seinem Stil mit; Stil und Metall eines Moduls
# gehören zu seinem Tier. Alle Teile einer Waffe liegen im selben Koordinatensystem (Griffmitte am Ursprung),
# deshalb passt jedes Modul auf jedes andere, auch über Tiers hinweg. Die Teile sind nur Aussehen.
import schwert

# Waffe -> Modul-Tabelle (Teil -> Tier -> (Anzahl Formen, Baufunktion)) und Kantenhärte je Tier
WAFFEN = {
	"schwert": (schwert.MODULE, schwert.GLATT),
}


# ---------------------------------------------------------------- Export


def exportieren(ob, pfad):
	# Länge entlang +Z -> Klinge zeigt in Godot nach -Z
	ob.data.transform(Matrix.Rotation(math.radians(-90), 4, "X"))
	bpy.ops.object.select_all(action="DESELECT")
	ob.select_set(True)
	bpy.context.view_layer.objects.active = ob
	bpy.ops.export_scene.gltf(filepath=pfad, export_format="GLB", use_selection=True,
							  export_materials="EXPORT", export_apply=True, export_normals=True)
	tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
	print(f"  {os.path.basename(pfad)}: {tris} Dreiecke, Materialien {[m.name for m in ob.data.materials]}")


if __name__ == "__main__":
	args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
	ziel = args[0]
	waffen = args[1:] or list(WAFFEN)
	for waffe in waffen:
		module, glatt = WAFFEN[waffe]
		ordner = os.path.join(ziel, waffe)
		os.makedirs(ordner, exist_ok=True)
		for f in os.listdir(ordner):
			if f.endswith(".glb"):
				os.remove(os.path.join(ordner, f))
		for teil, tiers in module.items():
			for tier, (anzahl_formen, bauen) in tiers.items():
				for form in range(1, anzahl_formen + 1):
					bpy.ops.wm.read_factory_settings(use_empty=True)
					t = Teil(f"{waffe}_{teil}_t{tier}_{form}", glatt[tier])
					bauen(t, form)
					exportieren(t.objekt(), os.path.join(ordner, f"{teil}_t{tier}_{form}.glb"))
