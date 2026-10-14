"""Fichte (jung/alt) + Baumstumpf als .glb für Godot.
Material-Slots: rinde, nadeln, kern, schnitt (werden in Godot per Name ersetzt).
Aufruf: python fichte.py -- <zielordner/modelle>"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise

# höhe, stamm_d, krone_breit, krone_ab, ast_schichten, stumpf_höhe   (siehe groessen.py)
FICHTE = {"jung": (5.6, 0.18, 2.1, 2.2, 11, 0.35),
          "alt":  (12.6, 0.42, 4.2, 3.5, 17, 0.5),
          "uralt": (20.0, 0.8, 6.2, 13.3, 13, 0.6)}   # untere 2/3 kahl

def stamm_radius(z, H, r0):
    """konisch + Wurzelanlauf unten"""
    return r0 * (1 - 0.9 * z / H) + r0 * 0.45 * math.exp(-z / (0.25 + r0))

class Bau:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
    def face(self, verts, uvs, mat):
        f = self.bm.faces.new([self.bm.verts.new(v) if not isinstance(v, bmesh.types.BMVert) else v for v in verts])
        f.material_index = mat
        for l, uv in zip(f.loops, uvs): l[self.uv].uv = uv
        return f

    def stamm(self, H, r0, z_bis, seg, seed, mat=0, deckel_mat=None, achse=lambda z: Vector(),
              mat_oben=None, grenze=0.0):
        """Röhre von z=0 bis z_bis. UV: u = Umfang, v = Höhe (gleiches Seitenverhältnis)."""
        umfang = 2 * math.pi * r0
        ringe = max(2, int(z_bis / 0.4) + 1)
        zs = [z_bis * i / (ringe - 1) for i in range(ringe)]
        off = Vector((seed * 3.7, seed * 1.3, 0))
        rows = []
        for z in zs:
            r = stamm_radius(z, H, r0)
            row = []
            for i in range(seg + 1):
                a = 2 * math.pi * i / seg
                wob = 1 + 0.08 * noise.noise(Vector((math.cos(a), math.sin(a), z * 0.6)) * 1.5 + off)
                row.append(Vector((math.cos(a) * r * wob, math.sin(a) * r * wob, z)) + achse(z))
            rows.append(row)
        vrows = [[self.bm.verts.new(p) for p in row] for row in rows]
        zrnd = random.Random(seed * 31)
        zacken = [grenze + zrnd.uniform(-0.6, 0.6) for _ in range(seg)]
        for j in range(ringe - 1):
            for i in range(seg):
                f = self.bm.faces.new((vrows[j][i], vrows[j][i + 1], vrows[j + 1][i + 1], vrows[j + 1][i]))
                f.material_index = mat_oben if (mat_oben is not None and zs[j] > zacken[i]) else mat
                for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    l[self.uv].uv = (ii / seg * max(1, round(umfang / 0.8)), zs[jj] / 0.8)
        top = vrows[-1]
        if deckel_mat is None:                    # Spitze schließen
            tip = self.bm.verts.new(Vector((0, 0, z_bis + r0 * 0.5)) + achse(z_bis))
            for i in range(seg):
                f = self.bm.faces.new((top[i], top[i + 1], tip)); f.material_index = mat
                for l, uv in zip(f.loops, ((i / seg, 0), ((i + 1) / seg, 0), (0.5, 1))): l[self.uv].uv = uv
        else:                                     # Schnittfläche (Stumpf), leicht schräg
            rmax = max(p.xy.length for p in rows[-1])
            for i, v in enumerate(top): v.co.z += v.co.x * 0.12
            f = self.bm.faces.new(top[:-1]); f.material_index = deckel_mat
            for l in f.loops: l[self.uv].uv = (0.5 + l.vert.co.x / rmax * 0.48, 0.5 + l.vert.co.y / rmax * 0.48)

    def ast(self, basis, richtung, L, breite, haengen, verdrehung, mat):
        """Zweig-Karte aus 3 Segmenten, hängt durch. u = Länge, v = Breite."""
        d = richtung.normalized()
        seite = d.cross(Vector((0, 0, 1))).normalized()
        quer = Matrix.Rotation(verdrehung, 3, d) @ seite
        pts = []
        for k in range(4):
            s = k / 3
            c = basis + d * L * s + Vector((0, 0, -haengen * L * s ** 1.6 + 0.08 * L * max(0, s - 0.75)))
            pts.append((c - quer * breite / 2, c + quer * breite / 2, s))
        for k in range(3):
            (a1, b1, s1), (a2, b2, s2) = pts[k], pts[k + 1]
            self.face((a1, b1, b2, a2), ((s1, 0), (s1, 1), (s2, 1), (s2, 0)), mat)

    def kegel(self, z0, z1, r0, seg, mat, stufen=4, achse=lambda z: Vector()):
        """Innenkegel in Stufen, UV: Nadeltextur gekachelt (u = Umfang, v = Höhe)."""
        rows = []
        for k in range(stufen + 1):
            t = k / stufen; z = z0 + (z1 - z0) * t; r = r0 * (1 - t)
            rows.append([self.bm.verts.new(Vector((math.cos(2 * math.pi * i / seg) * r, math.sin(2 * math.pi * i / seg) * r, z)) + achse(z)) for i in range(seg + 1)])
        for k in range(stufen):
            for i in range(seg):
                f = self.bm.faces.new((rows[k][i], rows[k][i + 1], rows[k + 1][i + 1], rows[k + 1][i])); f.material_index = mat
                for l, (ii, kk) in zip(f.loops, ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1))):
                    l[self.uv].uv = (ii / seg * 3, kk / stufen * (z1 - z0) / 1.2)

def fichte(alter, seed=1):
    """seed = Variante. Unregelmäßig: krumme Achse, schiefe Krone, Lücken, unterschiedliche Astlängen."""
    H, d, kb, ka, schichten, _ = FICHTE[alter]
    rnd = random.Random(seed * 7919)
    r0 = d / 2; R = kb / 2
    # leicht schiefer Wuchs + kleine Wellen im Stamm
    neig_dir = rnd.uniform(0, 2 * math.pi); neig = rnd.uniform(0.04, 0.09) * H
    noff = Vector((seed * 5.3, seed * 2.1, 0))
    def achse(z):
        t = z / H
        return Vector((math.cos(neig_dir), math.sin(neig_dir), 0)) * neig * t * t \
            + Vector((noise.noise(Vector((z * 0.35, 0, 0)) + noff), noise.noise(Vector((0, z * 0.35, 0)) + noff), 0)) * r0 * 0.6
    # Krone auf einer Seite voller (Licht), auf der anderen schwächer
    asym_dir = rnd.uniform(0, 2 * math.pi); asym = rnd.uniform(0.12, 0.25)
    b = Bau()
    b.stamm(H, r0, H * 0.96, 10 if alter == "jung" else 14, seed, mat=0, achse=achse)
    b.kegel(ka + 0.3, H * 0.92, R * 0.42, 10, mat=2, achse=achse)
    if alter == "uralt":                                     # untere zwei Drittel: nur kahle Äste
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from kiefer import kahle_aeste
        kahle_aeste(b, H, r0, achse, 1.8, ka - 0.2, rnd, laenge=(0.9, 2.8))
    abstand = (H * 0.9 - ka) / (schichten - 1)
    for i in range(schichten):
        t = i / (schichten - 1)                              # 0 = unten, 1 = oben
        z = ka + (H * 0.9 - ka) * t ** 0.92 + rnd.uniform(-0.35, 0.35) * abstand
        r_ast = R * (1 - t) ** 0.85 * rnd.uniform(0.8, 1.1) + 0.25
        anzahl = max(4, round(5 + 4 * (1 - t)) + rnd.randint(-1, 1))
        duenn = rnd.random() < 0.12                          # gelegentlich eine lichte Etage
        start = rnd.uniform(0, 2 * math.pi)
        for j in range(anzahl):
            if rnd.random() < (0.45 if duenn else 0.12):     # fehlender Ast -> Lücke
                continue
            a = start + 2 * math.pi * j / anzahl + rnd.uniform(-0.35, 0.35)
            richt = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.08, 0.15)))
            L = r_ast * rnd.uniform(0.75, 1.15) * (1 + asym * math.cos(a - asym_dir))
            if rnd.random() < 0.06: L *= 1.3                 # einzelner langer Ast
            zz = z + rnd.uniform(-0.12, 0.12) * abstand
            basis = Vector((0, 0, zz)) + achse(zz) + richt.normalized() * stamm_radius(zz, H, r0) * 0.5
            haengen = (0.38 * (1 - t) + 0.12) * rnd.uniform(0.75, 1.25)
            # gekreuzte Karten: flach (von oben/unten sichtbar) + steil (von der Seite sichtbar)
            b.ast(basis, richt, L, L * 0.62, haengen, rnd.uniform(-0.35, 0.35), mat=1)
            b.ast(basis, richt, L * 0.95, L * 0.5, haengen, math.radians(rnd.choice((-1, 1)) * rnd.uniform(55, 80)), mat=1)
    # Spitze: zwei gekreuzte, leicht schiefe Karten
    spitze = (Vector((0, 0, 1)) + Vector((math.cos(neig_dir), math.sin(neig_dir), 0)) * rnd.uniform(0.05, 0.2)).normalized()
    for rot in (0, math.pi / 2):
        b.ast(Vector((0, 0, H * 0.86)) + achse(H * 0.86), spitze, H * 0.14 + 0.2, 0.5 + R * 0.15, 0, rot, mat=1)
    return b.bm

def stumpf(alter, seed=1):
    H, d, *_ , h_stumpf = FICHTE[alter]
    b = Bau()
    b.stamm(H, d / 2, h_stumpf, 10 if alter == "jung" else 14, seed, mat=0, deckel_mat=3)
    return b.bm

MATS = ["rinde", "nadeln", "kern", "schnitt", "rinde_oben"]

def export(name, bm, out):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in MATS:
        me.materials.append(bpy.data.materials.get(m) or bpy.data.materials.new(m))
    for p in me.polygons: p.use_smooth = p.material_index in (0, 2, 4)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + ".glb"), export_format="GLB",
                              use_selection=True, export_materials="EXPORT")
    print(f"  {name}.glb: {sum(len(p.vertices) - 2 for p in me.polygons)} Dreiecke")

if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for alter in FICHTE:
        for v in (1, 2, 3):
            export(f"fichte_{alter}_{v}", fichte(alter, seed=v), out)
        export(f"fichte_stumpf_{alter}", stumpf(alter), out)
