"""Schnelle Vorschaubilder (Workbench) von Körper + Rüstung: vorne, seitlich, hinten."""
import math, os, bpy
from mathutils import Vector


def bilder(pfad, objekte=None, ansichten=((0, "vorne"), (90, "seite"), (180, "hinten")), hoehe=(0.0, 1.85),
		groesse=(420, 700), ziel_z=None, abstand=None, mitte_x=0.0):
	sc = bpy.context.scene
	sc.render.engine = "BLENDER_WORKBENCH"
	sh = sc.display.shading
	sh.light = "STUDIO"
	sh.color_type = "MATERIAL"
	sh.show_specular_highlight = True
	sh.show_cavity = True
	sh.cavity_type = "BOTH"
	sc.display.shading.show_object_outline = False
	sc.render.resolution_x, sc.render.resolution_y = groesse
	sc.render.film_transparent = False
	if sc.world is None:
		sc.world = bpy.data.worlds.new("w")
	sc.world.color = (0.32, 0.33, 0.35)
	cam = bpy.data.objects.get("VorschauKamera")
	if cam is None:
		cam = bpy.data.objects.new("VorschauKamera", bpy.data.cameras.new("VorschauKamera"))
		sc.collection.objects.link(cam)
	sc.camera = cam
	cam.data.type = "ORTHO"
	h0, h1 = hoehe
	cam.data.ortho_scale = (h1 - h0) * 1.05 * max(1.0, groesse[0] / groesse[1]) / min(1.0, groesse[0] / groesse[1]) if groesse[0] > groesse[1] else (h1 - h0) * 1.05
	mz = (h0 + h1) / 2 if ziel_z is None else ziel_z
	dateien = []
	from PIL import Image
	teile = []
	for winkel, name in ansichten:
		w = math.radians(winkel)
		cam.location = Vector((math.sin(w) * 4 + mitte_x, -math.cos(w) * 4, mz))
		cam.rotation_euler = (math.pi / 2, 0, w)
		f = pfad + "_" + name + ".png"
		sc.render.filepath = f
		bpy.ops.render.render(write_still=True)
		teile.append(Image.open(f).convert("RGB"))
		os.remove(f)
	gesamt = Image.new("RGB", (sum(t.width for t in teile), teile[0].height))
	x = 0
	for t in teile:
		gesamt.paste(t, (x, 0))
		x += t.width
	gesamt.save(pfad + ".png")
	return pfad + ".png"
