"""Abgebauter Zustand: Streumuster kleiner Erzbrocken, ein Muster für alle Tiers.
Aufruf: python schutt.py -- <ausgabe.png>"""
import bpy, bmesh, math, sys, random, os
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formen import rock_shape
from tiers import TIERS, ore_material

def rubble_layout(seed=7, count=34, radius=0.85):
    """Positionen/Größen der Brocken: Mitte dicht, außen locker, ohne Überlappung."""
    rnd = random.Random(seed); out = []
    while len(out) < count:
        r = abs(rnd.gauss(0, radius * 0.38)); a = rnd.uniform(0, 2 * math.pi)
        p = Vector((math.cos(a) * r * 1.3, math.sin(a) * r, 0))
        s = rnd.uniform(0.07, 0.16) * (1.3 - 0.6 * min(1, r / radius))  # außen kleiner
        if r > radius or any((p - q).length < (s + t) * 0.8 for q, t, *_ in out): continue
        rot = Euler((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 6.28)))
        out.append((p, s, rot, rnd.randint(1000, 9999)))
    return out

def build_rubble(mat, origin, layout):
    """Alle Brocken in ein Objekt (ein Draw-Call im Spiel)."""
    bm = bmesh.new()
    for p, s, rot, seed in layout:
        rb = rock_shape(seed, subdiv=4)
        m = rot.to_matrix().to_4x4()
        for v in rb.verts:
            v.co = m @ (v.co * s) + p + Vector((0, 0, -s * 0.25))  # leicht eingesunken
        tmp = bpy.data.meshes.new("tmp"); rb.to_mesh(tmp); rb.free()
        bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new("schutt"); bm.to_mesh(me); bm.free()
    for f in me.polygons: f.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new("schutt", me); bpy.context.scene.collection.objects.link(ob)
    ob.location = origin
    return ob

if __name__ == "__main__":
    out = sys.argv[-1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    layout = rubble_layout()
    labels = []
    for i, (name, t) in enumerate(TIERS.items()):
        t = dict(t); t.pop("crystals", None)
        t["pattern_scale"] = 3.5                       # Erzmuster feiner, damit es auf kleinen Steinen sichtbar ist
        if t["kind"] == "spots": t["amount"] += 0.1    # mehr Erzanteil
        else: t["width"] *= 1.6
        px, py = (i % 3 - 1) * 3.4, (0.5 - i // 3) * 3.6
        build_rubble(ore_material(name + "_schutt", **t), (px, py, 0), layout)
        labels.append((Vector((px, py - 1.45, 0)), name))
    fl = bpy.data.meshes.new("boden"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60); bm.to_mesh(fl)
    fo = bpy.data.objects.new("boden", fl); sc.collection.objects.link(fo)
    fm = bpy.data.materials.new("bm"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.07, 0.06, 0.045, 1); fl.materials.append(fm)
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.55, 0.7, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.35; sc.world = w
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3.5; sun.data.color = (1, 0.93, 0.82); sun.data.angle = 0.05
    sun.rotation_euler = (math.radians(55), 0, math.radians(-35))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 10.5; cam.location = (0, -14, 13)
    cam.rotation_euler = (Vector((0, -0.2, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.render.resolution_x, sc.render.resolution_y = 2200, 1500
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(out).convert("RGB"); d = ImageDraw.Draw(img)
    f = ImageFont.truetype("DejaVuSans-Bold.ttf", 38); Wd, Hd = img.size
    for p, tx in labels:
        q = world_to_camera_view(sc, cam, p)
        d.text((q.x * Wd, (1 - q.y) * Hd), tx, font=f, fill=(255, 230, 160), stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
    img.save(out)
