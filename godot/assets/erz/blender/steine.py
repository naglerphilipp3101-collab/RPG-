"""Steine und Felsbrocken: 5 Größen × 7 Varianten aus einer Icosphere mit 9 Noise-Schichten je Punkt.
Aufruf: python steine.py -- <zielordner/modelle> [vorschau.png]
Ergebnis: stein_<größe>_<variante>.glb (Größe 1–5, Variante 1–7), Boden bei z = 0, Mitte im Ursprung.

Jeder Punkt der Icosphere wird entlang seiner Richtung verschoben. Die Verschiebung ist die Summe aus 9 Schichten:
  1 Grundform    grobes fBm, macht aus der Kugel einen unregelmäßigen Klumpen
  2 Buckel       mittelgroße weiche Beulen
  3 Bruchflächen schräge Ebenen schneiden den Stein ab, ihre Lage schwankt mit Noise (keine glatten CAD-Flächen)
  4 Schichtung   Bänder entlang einer schrägen Achse ergeben Gesteinslagen mit kleinen Absätzen
  5 Großrisse    ein bis zwei tiefe Spalten quer durch den Stein, ihr Verlauf schwankt mit Noise
  6 Kerben       kantige Einschnitte an den Bruchkanten
  7 Körnung      unruhige Oberfläche
  8 Haarrisse    feine Risse
  9 Rauheit      kleinste Unebenheiten
Schichten 1–5 sind relativ zur Steingröße, 6–9 in Metern: die Körnung ist bei jeder Größe gleich fein.
Die Varianten gewichten die Schichten verschieden (rund, kantig, plattig, gespalten, hoch, liegend, zerklüftet).
In der Vertexfarbe steht eine Höhlen-Abdunklung (Spalten dunkel, Kanten hell); der Godot-Shader nutzt sie."""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, noise

## Breite in Metern je Größe 1–5 und Ziel-Dreiecke (Godot erzeugt beim Import LOD-Stufen)
BREITE = [0.6, 1.0, 1.6, 2.4, 3.4]
DREIECKE = [700, 1300, 2200, 3400, 4800]
## Name, Gewichte der 9 Schichten, Streckung (x, y, z), Anzahl Bruchflächen
VARIANTEN = [
    ("rund",       [0.6, 0.9, 0.0, 0.0, 0.1, 0.3, 0.6, 0.1, 0.6], (1.15, 0.95, 0.72), (0, 2)),
    ("kantig",     [1.0, 0.5, 1.0, 0.0, 0.4, 1.0, 1.0, 0.7, 1.0], (1.10, 0.95, 0.85), (9, 12)),
    ("plattig",    [0.6, 0.4, 0.6, 1.0, 0.3, 0.8, 1.0, 0.6, 1.0], (1.30, 1.00, 0.55), (4, 6)),
    ("gespalten",  [0.9, 0.5, 0.6, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0], (1.00, 0.90, 0.90), (5, 7)),
    ("hoch",       [1.0, 0.6, 0.8, 0.3, 0.5, 1.0, 1.0, 0.6, 1.0], (0.80, 0.75, 1.25), (6, 8)),
    ("liegend",    [0.7, 0.7, 0.3, 0.0, 0.2, 0.8, 1.0, 0.4, 1.0], (1.40, 1.15, 0.58), (2, 4)),
    ("zerkluftet", [1.2, 1.0, 0.8, 0.5, 1.0, 1.2, 1.2, 1.0, 1.0], (1.05, 1.00, 0.95), (9, 12)),
]


def _rand_vec(rnd, s=99.0):
    return Vector([rnd.uniform(-s, s) for _ in range(3)])


def _ridge(v, exp):
    """0 überall, 1 genau auf den Nulllinien des Noise -> schmale Risse"""
    return (1.0 - abs(noise.noise(v))) ** exp


def stein_form(groesse, variante, subdiv=6):
    name, w, streck, (cmin, cmax) = VARIANTEN[variante - 1]
    rnd = random.Random(1000 * groesse + 37 * variante)
    r_m = BREITE[groesse - 1] * 0.5                  # Radius in Metern (vor der Streckung)
    detail = min(1.0, 0.45 + 0.35 * r_m)             # kleine Steine: Meter-Schichten etwas schwächer
    off = [_rand_vec(rnd) for _ in range(9)]
    strata_achse = Vector((rnd.gauss(0, 0.4), rnd.gauss(0, 0.4), 1.0)).normalized()
    strata_freq = rnd.uniform(5.0, 7.0)
    ebenen = []
    for _ in range(rnd.randint(cmin, cmax)):
        pn = Vector([rnd.gauss(0, 1) for _ in range(3)])
        pn.z = abs(pn.z) * 0.6 + pn.z * 0.4          # eher seitliche und obere Flächen
        ebenen.append((pn.normalized(), rnd.uniform(0.55, 0.85), _rand_vec(rnd)))

    # Großrisse: schmale V-Spalten entlang leicht gewellter Ebenen quer durch den Stein
    risse = [(Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.3))).normalized(), rnd.uniform(-0.3, 0.3))
             for _ in range(round(w[4] * 2))]
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in bm.verts:
        n = v.co.normalized()
        pm = n * r_m                                 # Position in Metern für die feinen Schichten
        d = 0.0
        d += noise.fractal(n * 0.9 + off[0], 0.7, 2.0, 3) * 0.26 * w[0]                     # 1 Grundform
        d += noise.noise(n * 2.3 + off[1]) * 0.10 * w[1]                                      # 2 Buckel
        s = n.dot(strata_achse) * strata_freq + noise.noise(n * 1.5 + off[3]) * 0.6         # 4 Schichtung
        t = s - math.floor(s)
        d -= (0.035 * (1.0 - min(1.0, t / 0.18))) * w[3]
        for ra, ro in risse:                                                                  # 5 Großrisse
            a = n.dot(ra) - ro + noise.noise(n * 3.0 + off[4]) * 0.07
            d -= max(0.0, 1.0 - abs(a) / 0.07) ** 1.5 * 0.16 * w[4]
        r = 1.0 + d
        p = n * r
        for pn, o, po in ebenen:                                                              # 3 Bruchflächen
            h = p.dot(pn)
            oo = o + noise.noise(p * 2.2 + po) * 0.035
            if h > oo:
                p -= (h - oo) * pn * 0.94 * min(1.0, w[2] + 0.3)
        dm = 0.0
        dm -= noise.ridged_multi_fractal(pm * 1.3 + off[5], 1.0, 2.0, 3, 1.0, 2.0) * 0.012 * w[5]  # 6 Kerben
        dm += noise.fractal(pm * 4.0 + off[6], 0.6, 2.1, 3) * 0.012 * w[6]                   # 7 Körnung
        dm -= _ridge(pm * 7.0 + off[7], 9) * 0.014 * w[7]                                    # 8 Haarrisse
        dm += noise.noise(pm * 19.0 + off[8]) * 0.003 * w[8]                                 # 9 Rauheit
        v.co = p * r_m + n * dm * detail
    for v in bm.verts:
        v.co = Vector((v.co.x * streck[0], v.co.y * streck[1], v.co.z * streck[2]))
    # unten abschneiden, Boden schließen, auf z = 0 stellen (etwas Fuß bleibt für das Einsinken im Gelände)
    zmin = min(v.co.z for v in bm.verts)
    cut = zmin + (max(v.co.z for v in bm.verts) - zmin) * rnd.uniform(0.18, 0.28)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                 plane_co=(0, 0, cut), plane_no=(0, 0, 1), clear_inner=True)
    bmesh.ops.edgeloop_fill(bm, edges=[e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
    for v in bm.verts:
        v.co.z -= cut
    return bm


def hoehlen_farbe(ob):
    """Vertexfarbe: Spalten dunkel, Kanten hell (Krümmung aus den Nachbarpunkten), zweimal geglättet"""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    bm.normal_update()
    werte = []
    for v in bm.verts:
        nb = [e.other_vert(v).co for e in v.link_edges]
        if not nb:
            werte.append(0.0); continue
        mitte = sum(nb, Vector()) / len(nb)
        laenge = sum((q - v.co).length for q in nb) / len(nb) + 1e-6
        werte.append((mitte - v.co).dot(v.normal) / laenge)  # > 0: Mulde
    for _ in range(2):
        werte = [(werte[v.index] + sum(werte[e.other_vert(v).index] for e in v.link_edges)) / (1 + len(v.link_edges))
                 for v in bm.verts]
    hell = [max(0.0, min(1.0, 0.72 - c * 2.2)) for c in werte]
    # Unterseite dunkler (liegt im Gelände)
    hell = [h * (0.55 + 0.45 * min(1.0, v.co.z / 0.25)) for h, v in zip(hell, bm.verts)]
    bm.free()
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for i, h in enumerate(hell):
        attr.data[i].color = (h, h, h, 1.0)
    me.color_attributes.active_color = attr


def baue(groesse, variante):
    name = f"stein_{groesse}_{variante}"
    bm = stein_form(groesse, variante, subdiv=6 if groesse <= 2 else 7)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    cur = len(me.polygons)
    m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = min(1.0, DREIECKE[groesse - 1] / cur)
    dg = bpy.context.evaluated_depsgraph_get()
    neu = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); ob.data = neu; bpy.data.meshes.remove(me); neu.name = name
    for p in neu.polygons:
        p.use_smooth = True
    neu.set_sharp_from_angle(angle=math.radians(48))
    hoehlen_farbe(ob)
    return ob


def exportieren(ob, pfad):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=pfad, export_format="GLB", use_selection=True, export_materials="NONE",
                              export_vertex_color="ACTIVE", export_apply=True)


def vorschau_material():
    """Wie im Spiel: Felstextur von drei Seiten projiziert, mal Höhlen-Abdunklung aus der Vertexfarbe"""
    tex = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../welt/texturen/fels_albedo_hoehe.png")
    m = bpy.data.materials.new("fels"); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.4, 0.4, 0.4)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    img = N.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.abspath(tex))
    img.projection = "BOX"; img.projection_blend = 0.3
    L.new(mp.outputs["Vector"], img.inputs["Vector"])
    vc = N.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    L.new(img.outputs["Color"], mul.inputs[6])
    sk = N.new("ShaderNodeMath"); sk.operation = "MULTIPLY"; sk.inputs[1].default_value = 1.0 / 0.72
    L.new(vc.outputs["Color"], sk.inputs[0])
    L.new(sk.outputs[0], mul.inputs[7])
    L.new(mul.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.3
    L.new(img.outputs["Alpha"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def vorschau(steine, pfad):
    sc = bpy.context.scene
    mat = vorschau_material()
    sp = 4.2
    for (g, v), ob in steine.items():
        ob.data.materials.append(mat)
        ob.location = ((v - 4) * sp, [11.0, 8.6, 5.6, 1.6, -3.6][g - 1], 0)
        ob.rotation_euler.z = 0.6
    floor = bpy.data.meshes.new("boden"); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=80); bm.to_mesh(floor)
    fo = bpy.data.objects.new("boden", floor); sc.collection.objects.link(fo)
    fm = bpy.data.materials.new("bm"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.14, 0.1, 1)
    floor.materials.append(fm)
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True
    wd.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.6, 0.75, 1)
    wd.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sc.world = wd
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 4.0; sun.data.angle = 0.05; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 7 * sp + 1.0
    cam.location = (0, -30, 24)
    cam.rotation_euler = (Vector((0, 0.5, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1500
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = args[0]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    steine = {}
    for g in range(1, 6):
        for v in range(1, 8):
            ob = baue(g, v)
            exportieren(ob, os.path.join(out, f"{ob.name}.glb"))
            print(f"  {ob.name}: {len(ob.data.polygons)} Dreiecke, {ob.dimensions.x:.2f} × {ob.dimensions.y:.2f} × {ob.dimensions.z:.2f} m")
            steine[(g, v)] = ob
    if len(args) > 1:
        vorschau(steine, args[1])
