"""Blender-Demo: drei Low-Poly-Modelle bauen, als GLB exportieren und eine Vorschau rendern.
Aufruf: blender --background --factory-startup --python demo.py -- <ausgabeordner>
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
random.seed(4)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, rough=0.85, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def finish(obj, material, jitter=0.0, flat=True):
    """Ecken leicht verschieben (organischer Look) und flach schattieren (Low-Poly)."""
    if jitter > 0:
        for v in obj.data.vertices:
            v.co += Vector((random.uniform(-jitter, jitter) for _ in range(3)))
    obj.data.materials.append(material)
    for p in obj.data.polygons:
        p.use_smooth = not flat
    return obj


def cone(name, r1, r2, depth, z, verts=7, material=None, jitter=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=(0, 0, z))
    o = bpy.context.object
    o.name = name
    return finish(o, material, jitter)


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    return obj


def export(obj, filename):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, filename), use_selection=True, export_format="GLB")


# --- Kiefer ---------------------------------------------------------------
bark = mat("Rinde", (0.25, 0.14, 0.07))
needles = mat("Nadeln", (0.09, 0.26, 0.11))
parts = [cone("Stamm", 0.28, 0.18, 2.2, 1.1, 6, bark, 0.03)]
for i, (r, h, z) in enumerate([(1.9, 2.0, 2.4), (1.5, 1.8, 3.5), (1.05, 1.6, 4.5), (0.6, 1.3, 5.4)]):
    c = cone(f"Krone{i}", r, 0.05, h, z, 8, needles, 0.12)
    c.rotation_euler.z = random.uniform(0, math.pi)
    parts.append(c)
tree = join(parts, "Kiefer")
export(tree, "kiefer.glb")
tree.location.x = -3.8

# --- Felsen mit Kupferader ---------------------------------------------------
stone = mat("Stein", (0.36, 0.35, 0.34))
copper = mat("Kupfer", (0.85, 0.42, 0.18), rough=0.35, metal=0.7, emit=0.4)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(0, 0, 0.55))
rock = bpy.context.object
rock.scale = (1.3, 1.0, 0.75)
finish(rock, stone, jitter=0.18)
pieces = [rock]
for i in range(9):
    # Kristallgruppen ragen deutlich aus der Felsoberfläche heraus
    d = Vector((random.uniform(-1, 1), random.uniform(-1, 0.2), random.uniform(0.2, 0.9))).normalized()
    bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.2, radius2=0.0, depth=0.8,
                                    location=(d.x * 1.35, d.y * 1.05, 0.55 + d.z * 0.8))
    crystal = bpy.context.object
    crystal.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    finish(crystal, copper)
    pieces.append(crystal)
vein = join(pieces, "Kupferader")
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
export(vein, "kupferader.glb")
vein.location.x = 0.4

# --- Schwert -----------------------------------------------------------------
steel = mat("Stahl", (0.78, 0.8, 0.84), rough=0.25, metal=0.9)
leather = mat("Leder", (0.3, 0.17, 0.08))
gold = mat("Messing", (0.85, 0.65, 0.25), rough=0.3, metal=0.9)
bm = bmesh.new()
# Klinge: flaches Sechseck im Querschnitt, spitz zulaufend
section = [(0, 0.045), (0.012, 0.0), (0, -0.045), (-0.012, 0.0)]
rings = [(0.0, 1.0), (0.85, 0.85), (1.0, 0.0)]
verts_by_ring = []
for z, s in rings:
    verts_by_ring.append([bm.verts.new((x * (1 if s > 0 else 0.0), y * s, z)) for x, y in section])
for a, b in zip(verts_by_ring, verts_by_ring[1:]):
    for i in range(4):
        bm.faces.new((a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]))
bm.faces.new(verts_by_ring[0][::-1])
me = bpy.data.meshes.new("Klinge")
bm.to_mesh(me)
blade = bpy.data.objects.new("Klinge", me)
scene.collection.objects.link(blade)
bpy.ops.object.select_all(action="DESELECT")
blade.select_set(True)
bpy.context.view_layer.objects.active = blade
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.remove_doubles()
bpy.ops.object.mode_set(mode="OBJECT")
finish(blade, steel)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.02))
guard = finish(bpy.context.object, gold)
guard.scale = (0.05, 0.28, 0.04)
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.028, depth=0.22, location=(0, 0, -0.15))
grip = finish(bpy.context.object, leather)
bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=5, radius=0.045, location=(0, 0, -0.28))
pommel = finish(bpy.context.object, gold)
sword = join([blade, guard, grip, pommel], "Schwert")
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
export(sword, "schwert.glb")
sword.scale = (2.2, 2.2, 2.2)
sword.location = (2.6, 0, 0.75)
sword.rotation_euler = (0, math.radians(-20), math.radians(90))

# --- Vorschau-Render -------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
finish(bpy.context.object, mat("Boden", (0.22, 0.34, 0.14)))
sun_data = bpy.data.lights.new("Sonne", "SUN")
sun_data.energy = 3.5
sun = bpy.data.objects.new("Sonne", sun_data)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("Himmel")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.7, 0.9, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
scene.world = world
cam_data = bpy.data.cameras.new("Kamera")
cam = bpy.data.objects.new("Kamera", cam_data)
cam.location = (-0.3, -13.5, 4.6)
cam.rotation_euler = (math.radians(77), 0, 0)
scene.view_settings.view_transform = "Standard" # kräftigere Farben wie im Spiel
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = os.path.join(out, "vorschau.png")
bpy.ops.render.render(write_still=True)
print("FERTIG", out)
