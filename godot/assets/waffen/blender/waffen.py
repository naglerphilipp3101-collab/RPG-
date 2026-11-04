"""Erzeugt die Waffenmodelle als .glb für Godot (eine Datei je Form, Tiers nur über Materialien).
Aufruf: python waffen.py -- <zielordner> [form ...]
Ohne Formangabe werden alle Formen gebaut."""
import bpy, sys, os, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import *

# Jede Waffe hat eine Form; das Tier (Iron bis Darksteel) ändert in Godot nur die Materialien (waffen_modell.gd).


# ---------------------------------------------------------------- Formen


def schwert():
	"""Einhandschwert: Griff um den Ursprung, Klinge 0,78 m."""
	t = Teil("schwert")
	wicklung(t, -0.07, 0.075, 0.0155)
	ring(t, -0.07, 0.017, 0.012)
	ring(t, 0.075, 0.017, 0.012)
	knauf(t, -0.07, 0.024, form="tropfen")
	parierstange(t, 0.09, 0.21, 0.024, 0.032, form="geschwungen")
	# Fehlschärfe (Hülse) zwischen Parierstange und Klinge
	quader(t, (0, 0, 0.108), (0.05, 0.014, 0.018), "beschlag", fase=0.004)
	klinge(t, 0.112, 0.78, 0.052, 0.009, hohlkehle=0.45, kehl_laenge=0.72)
	for s in (1, -1):
		edelstein(t, Vector((0, s * 0.017, 0.093)), 0.008, "stein")
	return t


def _zacke(t, p, seite, laenge=0.02, material="klinge"):
	"""Kleiner Widerhaken an der Klingenkante."""
	a = t.vert(p + Vector((0, 0.003, -0.012)))
	b = t.vert(p + Vector((0, -0.003, -0.012)))
	c = t.vert(p + Vector((0, 0, 0.006)))
	s = t.vert(p + Vector((seite * laenge * 0.6, 0, -0.018)))
	for f in ([a, b, s], [b, c, s], [c, a, s]):
		t.flaeche(f if seite > 0 else list(reversed(f)), material)


FORMEN = {
	"sword": schwert,
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
	formen = args[1:] or list(FORMEN)
	os.makedirs(ziel, exist_ok=True)
	for form in formen:
		bpy.ops.wm.read_factory_settings(use_empty=True)
		ob = FORMEN[form]().objekt()
		ob.name = form
		exportieren(ob, os.path.join(ziel, f"{form}.glb"))
