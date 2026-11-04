"""Erzeugt die modularen Waffenteile als .glb für Godot.
Aufruf: python waffen.py -- <zielordner> [waffe ...]
Ergebnis: <zielordner>/<waffe>/<teil>_<form>.glb. Ohne Angabe werden alle Waffen gebaut."""
import bpy, sys, os, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import *

# Waffen sind modular: jede Waffe besteht aus Teilen (z. B. Klinge, Parierstange, Griff, Knauf),
# von jedem Teil gibt es mehrere Formen. Alle Teile einer Waffe liegen im selben Koordinatensystem
# (Griffmitte am Ursprung), deshalb passt jede Form auf jede andere. Das Tier (Iron bis Darksteel)
# vergibt Godot pro Teil über das Material (waffen_modell.gd), die Teile sind nur Aussehen.


def spitze(u, anteil):
	"""Breitenfaktor, der im letzten 'anteil' der Klinge rund zur Spitze ausläuft."""
	if u <= 1 - anteil:
		return 1.0
	return math.cos((u - (1 - anteil)) / anteil * math.pi / 2) ** 0.8


# ---------------------------------------------------------------- Schwert
# Griff von -0,07 bis 0,075 · Parierstange bei 0,09 · Klinge ab 0,112 · Knauf unter -0,07

S_KLINGE = 0.112


def schwert_klinge(form):
	t = Teil("klinge")
	if form == 1:  # Langklinge: schlank, gleichmäßig verjüngt
		klinge(t, S_KLINGE, 0.78, 0.052, 0.009, hohlkehle=0.45, kehl_laenge=0.72)
	elif form == 2:  # Breitklinge: fast parallel, kurze Spitze
		klinge(t, S_KLINGE, 0.74, 0.062, 0.010, hohlkehle=0.4, kehl_laenge=0.8,
			   breite_fn=lambda u: (1 - 0.12 * u) * spitze(u, 0.11))
	elif form == 3:  # Blattklinge: wird zum vorderen Drittel breiter
		klinge(t, S_KLINGE, 0.72, 0.05, 0.009, hohlkehle=0.35, kehl_laenge=0.55,
			   breite_fn=lambda u: (0.85 + 0.38 * math.sin(u * math.pi * 0.82)) * spitze(u, 0.28))
	elif form == 4:  # Säbelklinge: leicht gebogen, vorne breiter
		klinge(t, S_KLINGE, 0.76, 0.05, 0.009, hohlkehle=0.3, kehl_laenge=0.6, krumm=0.045,
			   breite_fn=lambda u: (1 + 0.25 * u) * spitze(u, 0.2))
	elif form == 5:  # Dornklinge: schmal, rautenförmig, für Stiche
		klinge(t, S_KLINGE, 0.8, 0.04, 0.011, hohlkehle=0.0, schritte=10,
			   breite_fn=lambda u: (1 - 0.55 * u) * spitze(u, 0.3))
	return t


def schwert_parier(form):
	t = Teil("parier")
	# Hülse zwischen Parierstange und Klinge
	quader(t, (0, 0, 0.108), (0.05, 0.014, 0.018), "beschlag", fase=0.004)
	art = {1: "gerade", 2: "geschwungen", 3: "kralle", 4: "flamme"}[form]
	parierstange(t, 0.09, 0.21 if form < 3 else 0.23, 0.024, 0.032, form=art)
	if form >= 3:
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.017, 0.093)), 0.008, "stein")
	return t


def schwert_griff(form):
	t = Teil("griff")
	z0, z1 = -0.07, 0.075
	if form == 1:  # Lederwicklung
		wicklung(t, z0, z1, 0.0155)
	elif form == 2:  # Drahtwicklung aus Metall
		wicklung(t, z0, z1, 0.0148, material="beschlag", windungen=16, tiefe=0.0012, n=10)
	elif form == 3:  # Leder mit Mittelring
		wicklung(t, z0, -0.004, 0.0155)
		wicklung(t, 0.004, z1, 0.0155)
		ring(t, 0.0, 0.0158, 0.01)
	elif form == 4:  # Holz mit Rillen
		profil = []
		for k in range(13):
			z = z0 + (z1 - z0) * k / 12
			profil.append((0.0158 if k % 3 else 0.0143, z))
		drehkoerper(t, profil, "holz", n=12)
	ring(t, z0, 0.017, 0.012)
	ring(t, z1, 0.017, 0.012)
	return t


def schwert_knauf(form):
	t = Teil("knauf")
	art = {1: "scheibe", 2: "kugel", 3: "tropfen", 4: "spitz", 5: "kugel"}[form]
	knauf(t, -0.076, 0.026 if art != "spitz" else 0.022, form=art)
	if form == 5:  # Kugel mit Stein auf beiden Seiten
		for s in (1, -1):
			edelstein(t, Vector((0, s * 0.024, -0.102)), 0.011, "stein")
	return t


# Waffe -> Teil -> Anzahl Formen, Baufunktion
TEILE = {
	"schwert": {
		"klinge": (5, schwert_klinge),
		"parier": (4, schwert_parier),
		"griff": (4, schwert_griff),
		"knauf": (5, schwert_knauf),
	},
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
	waffen = args[1:] or list(TEILE)
	for waffe in waffen:
		ordner = os.path.join(ziel, waffe)
		os.makedirs(ordner, exist_ok=True)
		for teil, (anzahl_formen, bauen) in TEILE[waffe].items():
			for form in range(1, anzahl_formen + 1):
				bpy.ops.wm.read_factory_settings(use_empty=True)
				ob = bauen(form).objekt()
				ob.name = f"{waffe}_{teil}_{form}"
				exportieren(ob, os.path.join(ordner, f"{teil}_{form}.glb"))
