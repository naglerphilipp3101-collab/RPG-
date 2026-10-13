"""Lookdev der 6 Erz-Tiers (Material + optionale Kristalle).
Aufruf: python tiers.py -- <ausgabe.png>"""
import bpy, bmesh, math, sys, random, os
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formen import rock_shape

# Katalog-Nr -> Seed: Nr n = Seed 99+n.  Größe 1..5 = Formen 1,4,7,13,8
SIZES = [(1, 0.55), (4, 0.75), (7, 1.0), (13, 1.3), (8, 1.65)]

TIERS = {
    "T1 Iron": dict(
        base=((0.018, 0.018, 0.018), (0.12, 0.115, 0.11)), base_metal=0.0, base_rough=0.85,
        kind="spots", amount=0.5, soft=0.14,
        halo=(0.09, 0.045, 0.025),                     # rostbrauner Übergang
        ore=(0.11, 0.025, 0.012), ore_metal=0.55, ore_rough=0.5),
    "T2 Palladium": dict(
        base=((0.45, 0.45, 0.46), (0.75, 0.75, 0.77)), base_metal=1.0, base_rough=0.18,
        kind="spots", amount=0.55, soft=0.06,
        ore=(0.33, 0.33, 0.34), ore_metal=0.7, ore_rough=0.7),  # Flecken matt
    "T3 Mithril": dict(
        base=((0.02, 0.035, 0.08), (0.08, 0.13, 0.26)), base_metal=0.0, base_rough=0.75,
        kind="veins", width=0.024,
        ore=(0.6, 0.8, 1.0), ore_metal=1.0, ore_rough=0.15, emit=((0.35, 0.65, 1.0), 2.5)),
    "T4 Glacialore": dict(
        base=((0.04, 0.06, 0.08), (0.2, 0.25, 0.3)), base_metal=0.0, base_rough=0.6,
        kind="veins", width=0.02,
        ore=(0.5, 0.85, 1.0), ore_metal=0.0, ore_rough=0.05, emit=((0.3, 0.8, 1.0), 1.5),
        crystals=dict(col=(0.55, 0.88, 1.0), emit=((0.3, 0.8, 1.0), 0.6), transmission=0.8)),
    "T5 Sungold": dict(
        base=((0.8, 0.5, 0.12), (1.0, 0.75, 0.3)), base_metal=1.0, base_rough=0.25,
        kind="veins", width=0.024,
        ore=(0.9, 0.12, 0.01), ore_metal=0.3, ore_rough=0.4, emit=((1.0, 0.2, 0.01), 2.5)),
    "T6 Darksteel": dict(
        base=((0.006, 0.006, 0.008), (0.025, 0.024, 0.03)), base_metal=0.6, base_rough=0.35,
        kind="veins", width=0.022,
        ore=(0.45, 0.05, 0.8), ore_metal=0.0, ore_rough=0.3, emit=((0.6, 0.08, 1.0), 4.0),
        crystals=dict(col=(0.002, 0.005, 0.035), emit=((0.01, 0.025, 0.3), 0.5), transmission=0.0)),
}

class Graph:
    """kleine Helfer zum Bauen von Shader-Nodes"""
    def __init__(self, mat, pattern_scale=1.0):
        self.N, self.L = mat.node_tree.nodes, mat.node_tree.links
        self.pos = self.N.new("ShaderNodeNewGeometry").outputs["Position"]  # Weltkoordinaten
        if pattern_scale != 1.0:
            vm = self.N.new("ShaderNodeVectorMath"); vm.operation = "SCALE"
            vm.inputs["Scale"].default_value = pattern_scale
            self.L.new(self.pos, vm.inputs[0]); self.pos = vm.outputs[0]
    def link(self, val, sock):
        if isinstance(val, (int, float)): sock.default_value = val
        elif isinstance(val, tuple): sock.default_value = val if len(val) == 4 else (*val, 1)
        else: self.L.new(val, sock)
    def noise(self, scale, detail=6, rough=0.55):
        n = self.N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
        self.L.new(self.pos, n.inputs["Vector"]); return n
    def ramp(self, inp, stops):
        r = self.N.new("ShaderNodeValToRGB"); e = r.color_ramp.elements
        while len(e) < len(stops): e.new(0.5)
        for el, (p, c) in zip(e, stops):
            el.position = p; el.color = c if len(c) == 4 else (*c, 1)
        self.link(inp, r.inputs["Fac"]); return r.outputs["Color"]
    def mix(self, fac, a, b, mode="MIX"):
        x = self.N.new("ShaderNodeMix"); x.data_type = "RGBA"; x.blend_type = mode
        self.link(fac, x.inputs["Factor"]); self.link(a, x.inputs[6]); self.link(b, x.inputs[7]); return x.outputs[2]
    def math(self, op, a, b=0.0):
        x = self.N.new("ShaderNodeMath"); x.operation = op
        self.link(a, x.inputs[0]); self.link(b, x.inputs[1]); return x.outputs[0]
    def lerp(self, fac, a, b):
        x = self.N.new("ShaderNodeMapRange"); self.link(fac, x.inputs["Value"])
        x.inputs["To Min"].default_value, x.inputs["To Max"].default_value = a, b; return x.outputs["Result"]

W, B = (1, 1, 1, 1), (0, 0, 0, 1)

def ore_material(name, base, base_metal, base_rough, kind, ore, ore_metal, ore_rough,
                 amount=0.5, soft=0.06, width=0.022, halo=None, emit=None, crystals=None, pattern_scale=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    g = Graph(m, pattern_scale); bsdf = g.N["Principled BSDF"]
    # Grundfläche: feine Körnung x großflächige Helligkeitsvariation
    grain = g.ramp(g.noise(2.5, 10).outputs["Fac"], [(0.3, base[0]), (0.7, base[1])])
    tone = g.ramp(g.noise(0.6, 3).outputs["Fac"], [(0.35, (0.45, 0.45, 0.45)), (0.65, W)])
    surf = g.mix(1.0, grain, tone, "MULTIPLY")
    # Erzmaske
    if kind == "spots":
        v = g.N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 3.5
        warp = g.noise(1.5, 2)
        w = g.N.new("ShaderNodeMix"); w.data_type = "VECTOR"; w.inputs["Factor"].default_value = 0.4
        g.L.new(g.pos, w.inputs[4]); g.L.new(warp.outputs["Color"], w.inputs[5]); g.L.new(w.outputs[1], v.inputs["Vector"])
        # Rand mit Noise zerfransen, damit Übergänge natürlich wirken
        d = g.math("ADD", v.outputs["Distance"], g.math("MULTIPLY", g.math("SUBTRACT", g.noise(8, 4).outputs["Fac"], 0.5), 0.12))
        mask = g.ramp(d, [(amount - soft - 0.04, W), (amount - 0.04, B)])
        if halo:
            hmask = g.ramp(d, [(amount - 0.04, W), (amount + 0.12, B)])
            surf = g.mix(hmask, surf, halo)
    else:
        n = g.noise(1.6, 2, 0.5)
        dd = g.math("ABSOLUTE", g.math("SUBTRACT", n.outputs["Fac"], 0.5))
        mask = g.ramp(dd, [(width * 0.45, W), (width, B)])
        # zweites, feineres Adernetz
        n2 = g.noise(3.5, 2, 0.5)
        dd2 = g.math("ABSOLUTE", g.math("SUBTRACT", n2.outputs["Fac"], 0.5))
        m2 = g.ramp(dd2, [(width * 0.12, W), (width * 0.28, B)])
        mask = g.mix(1.0, mask, m2, "LIGHTEN")
    var = g.noise(12, 4).outputs["Fac"]
    orec = g.mix(var, tuple(c * 0.65 for c in ore), tuple(min(1, c * 1.25) for c in ore))
    col = g.mix(mask, surf, orec)
    ao = g.N.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.2
    col = g.mix(0.55, col, ao.outputs["AO"], "MULTIPLY")
    g.link(col, bsdf.inputs["Base Color"])
    g.link(g.lerp(mask, base_metal, ore_metal), bsdf.inputs["Metallic"])
    rough_var = g.lerp(g.noise(6, 3).outputs["Fac"], base_rough * 0.8, min(1, base_rough * 1.25))
    rr = g.N.new("ShaderNodeMapRange"); g.link(mask, rr.inputs["Value"]); g.link(rough_var, rr.inputs["To Min"])
    rr.inputs["To Max"].default_value = ore_rough
    g.link(rr.outputs["Result"], bsdf.inputs["Roughness"])
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit[0], 1)
        g.link(g.math("MULTIPLY", mask, emit[1]), bsdf.inputs["Emission Strength"])
    h = g.math("ADD", g.noise(30, 6).outputs["Fac"], g.math("MULTIPLY", mask, 0.5))
    bump = g.N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.03
    g.link(h, bump.inputs["Height"]); g.L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def crystal_material(name, col, emit, transmission):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = 0.08
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = 1.45
    b.inputs["Emission Color"].default_value = (*emit[0], 1)
    b.inputs["Emission Strength"].default_value = emit[1]
    return m

def crystal_cluster(rock_ob, seed, clusters=2):
    """Sechseckige Kristalle, per Raycast auf die Steinoberfläche gesetzt (lokale Koordinaten)."""
    rnd = random.Random(seed * 7 + 1)
    bpy.context.view_layer.update()
    bm = bmesh.new()
    bb = [Vector(c) for c in rock_ob.bound_box]
    lo = Vector((min(c.x for c in bb), min(c.y for c in bb), 0)); hi = Vector((max(c.x for c in bb), max(c.y for c in bb), 0))
    placed = 0; tries = 0
    while placed < clusters and tries < 50:
        tries += 1
        o = Vector((rnd.uniform(lo.x, hi.x) * 0.6, rnd.uniform(lo.y, hi.y) * 0.6, 5))
        hit, p, nrm, _ = rock_ob.ray_cast(o, Vector((0, 0, -1)))
        if not hit or nrm.z < 0.3: continue
        placed += 1
        for _ in range(rnd.randint(4, 7)):
            r = rnd.uniform(0.05, 0.11); h = rnd.uniform(0.3, 0.85) * (r / 0.08)
            d = (nrm * 0.5 + Vector((0, 0, 0.5)) + Vector([rnd.gauss(0, 0.35) for _ in range(3)])).normalized()
            base = p + Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 0)) - d * 0.1
            q = Vector((0, 0, 1)).rotation_difference(d)
            rot = rnd.uniform(0, 1)
            ring0, ring1 = [], []
            for k in range(6):
                a = rot + k * math.pi / 3
                ring0.append(bm.verts.new(base + q @ Vector((math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, 0))))
                ring1.append(bm.verts.new(base + q @ Vector((math.cos(a) * r, math.sin(a) * r, h))))
            tip = bm.verts.new(base + q @ Vector((rnd.uniform(-0.3, 0.3) * r, 0, h + r * rnd.uniform(1.0, 1.8))))
            for k in range(6):
                k2 = (k + 1) % 6
                bm.faces.new((ring0[k], ring0[k2], ring1[k2], ring1[k]))
                bm.faces.new((ring1[k], ring1[k2], tip))
            bm.faces.new(list(reversed(ring0)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(rock_ob.name + "_kristalle"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(ob)
    ob.parent = rock_ob
    return ob

def add_rock(form_nr, scale, mat, loc, rot, crystal_mat=None):
    seed = 99 + form_nr
    me = bpy.data.meshes.new(f"form{form_nr}"); rock_shape(seed).to_mesh(me)
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(ob)
    ob.location, ob.scale, ob.rotation_euler.z = loc, (scale,) * 3, rot
    if crystal_mat:
        c = crystal_cluster(ob, seed, clusters=2 if scale < 1.2 else 3)
        c.data.materials.append(crystal_mat)
    return ob

if __name__ == "__main__":
    out = sys.argv[-1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    labels = []
    for i, (name, t) in enumerate(TIERS.items()):
        cm = crystal_material(name + "_kr", **t["crystals"]) if "crystals" in t else None
        px, py = (i % 3 - 1) * 4.6, (0.5 - i // 3) * 6.0
        add_rock(7, 1.25, ore_material(name, **t), (px, py, 0), 0.6, cm)
        labels.append((Vector((px, py - 2.1, 0)), name))
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
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 15; cam.location = (0, -20, 15)
    cam.rotation_euler = (Vector((0, 0.2, 0.3)) - cam.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.render.resolution_x, sc.render.resolution_y = 2200, 1700
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(out).convert("RGB"); d = ImageDraw.Draw(img)
    f = ImageFont.truetype("DejaVuSans-Bold.ttf", 38); Wd, Hd = img.size
    for p, t in labels:
        q = world_to_camera_view(sc, cam, p)
        d.text((q.x * Wd, (1 - q.y) * Hd), t, font=f, fill=(255, 230, 160), stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
    img.save(out)
