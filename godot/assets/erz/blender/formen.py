"""Erzbrocken-Generator: erzeugt Steinformen per Seed und rendert einen Katalog.
Aufruf: python formen.py -- <ausgabe.png> <seed_start> <anzahl>"""
import bpy, bmesh, math, random, sys
from mathutils import Vector, noise
from bpy_extras.object_utils import world_to_camera_view

def rock_shape(seed, subdiv=7):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector([rnd.uniform(-99, 99) for _ in range(3)])
    # grobe Form (mehrere Noise-Oktaven)
    for v in bm.verts:
        n = v.co.normalized()
        v.co = n * (1.0 + noise.fractal(n * 1.1 + off, 0.6, 2.1, 4) * 0.2)
    # Bruchflächen: Ebenen schneiden ab, leicht gewellt damit sie nicht CAD-glatt wirken
    for k in range(rnd.randint(8, 13)):
        pn = Vector([rnd.gauss(0, 1) for _ in range(3)]).normalized()
        o = rnd.uniform(0.55, 0.85)
        po = off + Vector((k * 3.1, k * 1.7, k * 2.3))
        for v in bm.verts:
            h = v.co.dot(pn)
            oo = o + noise.noise(v.co * 2.5 + po) * 0.03
            if h > oo:
                v.co -= (h - oo) * pn * 0.95
    # Feindetail: Ridged-Noise ergibt rissige, kantige Struktur
    for v in bm.verts:
        n = v.co.normalized()
        d = noise.fractal(v.co * 2.0 + off, 0.5, 2.3, 4) * 0.022
        d += abs(noise.noise(v.co * 9 + off)) * -0.006
        v.co += n * d
    s = Vector((rnd.uniform(0.9, 1.35), rnd.uniform(0.75, 1.05), rnd.uniform(0.75, 1.0)))
    for v in bm.verts:
        v.co = Vector((v.co.x * s.x, v.co.y * s.y, v.co.z * s.z))
    # unten abschneiden + Boden schließen
    cut = rnd.uniform(-0.4, -0.25)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                 plane_co=(0, 0, cut), plane_no=(0, 0, 1), clear_inner=True)
    bmesh.ops.edgeloop_fill(bm, edges=[e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
    for v in bm.verts:
        v.co.z -= cut
    return bm

def stone_material():
    m = bpy.data.materials.new("stein"); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 4; n1.inputs["Detail"].default_value = 10
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 40; n2.inputs["Detail"].default_value = 6
    for n in (n1, n2): L.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.033, 0.03, 1)
    ramp.color_ramp.elements[1].color = (0.13, 0.12, 0.105, 1)
    L.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    # Kantenabrieb: Pointiness (Cycles) hellt Kanten auf
    geo = N.new("ShaderNodeNewGeometry")
    pr = N.new("ShaderNodeMapRange"); pr.inputs["From Min"].default_value = 0.54; pr.inputs["From Max"].default_value = 0.62
    L.new(geo.outputs["Pointiness"], pr.inputs["Value"])
    edge = N.new("ShaderNodeMix"); edge.data_type = "RGBA"
    edge.inputs[7].default_value = (0.19, 0.18, 0.165, 1)
    L.new(pr.outputs["Result"], edge.inputs["Factor"]); L.new(ramp.outputs["Color"], edge.inputs[6])
    # Hohlräume dunkler (AO)
    ao = N.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.15
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 0.7
    L.new(edge.outputs[2], mul.inputs[6]); L.new(ao.outputs["AO"], mul.inputs[7])
    L.new(mul.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15; bump.inputs["Distance"].default_value = 0.02
    L.new(n2.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

if __name__ == "__main__":
    out, start, count = sys.argv[-3], int(sys.argv[-2]), int(sys.argv[-1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    mat = stone_material()
    cols = 5; rows = math.ceil(count / cols); sp = 3.3
    rocks = []
    for i in range(count):
        seed = start + i
        me = bpy.data.meshes.new(f"fels_{seed}"); rock_shape(seed).to_mesh(me)
        ob = bpy.data.objects.new(me.name, me); sc.collection.objects.link(ob)
        for p in me.polygons: p.use_smooth = True
        me.materials.append(mat)
        ob.location = ((i % cols - (cols - 1) / 2) * sp, ((rows - 1) / 2 - i // cols) * sp * 1.3, 0)
        ob.rotation_euler.z = random.Random(seed).uniform(0, 6.28)
        rocks.append((i + 1, seed, ob))
    floor = bpy.data.meshes.new("boden"); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60); bm.to_mesh(floor)
    fo = bpy.data.objects.new("boden", floor); sc.collection.objects.link(fo)
    fm = bpy.data.materials.new("bm"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.075, 0.055, 1)
    floor.materials.append(fm)
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.6, 0.75, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    sc.world = w
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 4.5; sun.data.color = (1, 0.95, 0.85); sun.data.angle = 0.05
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = cols * sp + 0.6
    cam.location = (0, -20, 14)
    cam.rotation_euler = (Vector((0, 0.2, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 2000, int(2000 * 0.78 * rows / 4)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    # Nummern einzeichnen
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(out).convert("RGB"); d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
    except OSError: f = ImageFont.load_default(44)
    W, H = img.size
    for num, seed, ob in rocks:
        p = world_to_camera_view(sc, cam, ob.location + Vector((0, -1.45, 0)))
        x, y = p.x * W, (1 - p.y) * H
        d.text((x, y), str(num), font=f, fill=(255, 230, 160), stroke_width=4, stroke_fill=(0, 0, 0), anchor="mm")
    img.save(out)
    print("seeds:", [(n, s) for n, s, _ in rocks])
