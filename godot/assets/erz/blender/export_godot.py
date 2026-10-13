"""Exportiert Brocken (5 Größen), Kristalle und Schutt als .glb für Godot.
Aufruf: python export_godot.py -- <zielordner/modelle>"""
import bpy, bmesh, sys, os, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formen import rock_shape
from tiers import SIZES, crystal_cluster
from schutt import rubble_layout

F = 0.75                                      # Blender-Einheit -> Meter im Spiel
TRIS = [2500, 3500, 5000, 6000, 7000]         # Ziel-Dreiecke je Größe (Godot erzeugt LODs automatisch)

def obj_from_bm(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def scale_mesh(ob, s):
    for v in ob.data.vertices: v.co *= s

def decimated(ob, tris):
    cur = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = min(1.0, tris / cur)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); old = ob.data; ob.data = me; bpy.data.meshes.remove(old)
    return ob

def finish(ob, angle=50):
    for p in ob.data.polygons: p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(angle))

def export(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_materials="NONE", export_apply=True)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print(f"  {os.path.basename(path)}: {tris} Dreiecke")

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for i, (form, s) in enumerate(SIZES):
        g = i + 1; seed = 99 + form
        rock = obj_from_bm(f"erz_groesse_{g}", rock_shape(seed))
        bpy.context.view_layer.update()
        kr = crystal_cluster(rock, seed, clusters=2 if s < 1.2 else 3)
        kr.parent = None; kr.name = f"kristalle_groesse_{g}"
        for ob in (rock, kr): scale_mesh(ob, s * F)
        decimated(rock, TRIS[i]); finish(rock)
        for p in kr.data.polygons: p.use_smooth = False
        export(rock, os.path.join(out, f"erz_groesse_{g}.glb"))
        export(kr, os.path.join(out, f"kristalle_groesse_{g}.glb"))
    # Schutt: ein Objekt aus allen kleinen Brocken
    bm = bmesh.new()
    for p, s, rot, seed in rubble_layout():
        rb = rock_shape(seed, subdiv=3); m = rot.to_matrix().to_4x4()
        for v in rb.verts: v.co = (m @ (v.co * s) + p + Vector((0, 0, -s * 0.25))) * F
        tmp = bpy.data.meshes.new("tmp"); rb.to_mesh(tmp); rb.free(); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    sch = obj_from_bm("schutt", bm); finish(sch, 60)
    export(sch, os.path.join(out, "schutt.glb"))
