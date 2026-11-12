"""Vorschaubilder mit Cycles (CPU): jedes Modell einzeln vor neutralem Boden, Kamera schräg von vorne links.
Wird von props.py / baukasten.py aufgerufen (Option --vorschau <ordner>)."""
import bpy, math
from mathutils import Vector


def szene_vorbereiten(samples=32):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.0
    welt = bpy.data.worlds.new("himmel") if "himmel" not in bpy.data.worlds else bpy.data.worlds["himmel"]
    sc.world = welt
    welt.use_nodes = True
    nt = welt.node_tree
    bg = nt.nodes["Background"]
    if "Sky Texture" not in nt.nodes:
        sky = nt.nodes.new("ShaderNodeTexSky")
        try:
            sky.sky_type = "MULTIPLE_SCATTERING"
        except TypeError:
            sky.sky_type = "NISHITA"
        sky.sun_disc = False
        sky.sun_elevation = math.radians(38)
        sky.sun_rotation = math.radians(200)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.2
    if "vorschau_boden" not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=60)
        boden = bpy.context.active_object; boden.name = "vorschau_boden"
        m = bpy.data.materials.new("boden_mat"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.11, 0.10, 0.075, 1); b.inputs["Roughness"].default_value = 0.95
        boden.data.materials.append(m)
        sonne = bpy.data.lights.new("sonne", "SUN"); sonne.energy = 4.0; sonne.angle = math.radians(3)
        so = bpy.data.objects.new("sonne", sonne); sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(52), 0, math.radians(200))
        cam = bpy.data.cameras.new("kamera"); cam.lens = 50
        co = bpy.data.objects.new("kamera", cam); sc.collection.objects.link(co); sc.camera = co


def rendern(objekte, pfad, breite=480, hoehe=480, blick=(-35, 24), abstand=1.0):
    """Rendert nur die übergebenen Objekte (alle anderen Modelle werden ausgeblendet)."""
    sc = bpy.context.scene
    for ob in sc.objects:
        if ob.type == "MESH" and ob.name != "vorschau_boden":
            ob.hide_render = ob not in objekte
    pts = [ob.matrix_world @ Vector(c) for ob in objekte for c in ob.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    mitte = (lo + hi) * 0.5; radius = max((hi - lo).length * 0.5, 0.3)
    # Böden und Decken liegen mit der Oberkante auf 0: dann den Vorschau-Boden darunter legen
    bpy.data.objects["vorschau_boden"].location.z = lo.z - 0.002 if hi.z < 0.05 else 0.0
    cam = sc.camera
    fov = cam.data.angle
    d = radius / math.sin(fov * 0.5) * 1.02 * abstand
    az, el = math.radians(blick[0]), math.radians(blick[1])
    richtung = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = mitte + richtung * d
    cam.rotation_euler = (-richtung).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = d * 4
    sc.render.resolution_x = breite; sc.render.resolution_y = hoehe
    sc.render.filepath = pfad
    sc.render.image_settings.file_format = "JPEG"
    bpy.ops.render.render(write_still=True)
