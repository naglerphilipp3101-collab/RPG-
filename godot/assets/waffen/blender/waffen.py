"""Erzeugt die modularen Waffenteile als .glb für Godot.
Aufruf: python waffen.py -- <zielordner> [modulart ...]
Ergebnis: <zielordner>/<modulart>/t<tier>_<form>.glb. Ohne Angabe werden alle Modularten gebaut."""
import bpy, sys, os, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import *

# Waffen sind modular und bestehen aus Modulen verschiedener Modularten (Schwertklinge, Knauf, Stiel …).
# Jedes Tier (1 Iron bis 6 Darksteel) bringt eigene Module in seinem Stil mit; Stil und Metall eines Moduls
# gehören zu seinem Tier. Geteilte Modularten (Knauf, Parierstange, Einhandgriff …) werden einmal gebaut und in
# Godot je Waffe verschoben/skaliert (waffen_modell.gd, WAFFEN). Die Liste aller Modularten mit den Zahlen je Tier
# steht im Dokument "Waffenmodule – Liste zum Bearbeiten". Die Module sind nur Aussehen.
import schwert, stangen
from schwert import KL, GLATT, _je_tier


def skaliert(bauen, mitte, s, ziel):
	"""Baut ein Modul und skaliert alles Neue um 'mitte' mit Faktoren s=(x, y, z), dann nach 'ziel' verschoben."""
	def f(t, form):
		n0 = anzahl(t)
		bauen(t, form)
		mitte_v, ziel_v = Vector(mitte), Vector(ziel)
		for v in neue_verts(t, n0):
			d = v.co - mitte_v
			v.co = ziel_v + Vector((d.x * s[0], d.y * s[1], d.z * s[2]))
	return f


def _skaliert_je_tier(fns, mitte, s, ziel):
	return [skaliert(f, mitte, s, ziel) for f in fns]


def _zweihand(f):
	return lambda t, form: f(t, form, -0.12, 0.16)


# Modulart -> Tier -> (Anzahl Module, Baufunktion(t, form))
ARTEN = {
	# Schwertfamilie
	"schwertklinge": _je_tier(schwert.KLINGEN, 3),
	"grossschwertklinge": _je_tier(_skaliert_je_tier(schwert.KLINGEN, (0, 0, KL), (1.25, 1.3, 1.6), (0, 0, 0.2)), 3),
	"degenklinge": _je_tier(_skaliert_je_tier(schwert.KLINGEN, (0, 0, KL), (0.45, 0.85, 1.22), (0, 0, KL)), 3),
	"messerklinge": _je_tier(_skaliert_je_tier(schwert.KLINGEN, (0, 0, KL), (0.72, 0.85, 0.34), (0, 0, 0.086)), 3),
	"parierstange": _je_tier(schwert.PARIER, 2),
	"knauf": _je_tier(schwert.KNAEUFE, 2),
	"einhandgriff": _je_tier(schwert.GRIFFE, 2),
	"zweihandgriff": _je_tier([_zweihand(f) for f in schwert.GRIFFE], 2),
	"korb": _je_tier(schwert.KOERBE, 2),
	# Stangenwaffen
	**stangen.ARTEN,
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
	arten = args[1:] or list(ARTEN)
	for art in arten:
		ordner = os.path.join(ziel, art)
		os.makedirs(ordner, exist_ok=True)
		for f in os.listdir(ordner):
			if f.endswith(".glb"):
				os.remove(os.path.join(ordner, f))
		for tier, (anzahl_module, bauen) in ARTEN[art].items():
			for form in range(1, anzahl_module + 1):
				bpy.ops.wm.read_factory_settings(use_empty=True)
				t = Teil(f"{art}_t{tier}_{form}", GLATT[tier])
				bauen(t, form)
				exportieren(t.objekt(), os.path.join(ordner, f"t{tier}_{form}.glb"))
