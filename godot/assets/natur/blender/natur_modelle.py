"""Bodenobjekte und tote Bäume für die Biome (data/biome.json) als .glb für Godot:
  totbaum_1-3     toter, kahler Baum im Moor (6–9 m, krumm, abgebrochene Spitze)
  baumstamm_1-3   umgestürzter Stamm im Wald (4–7 m, ein Ende abgebrochen, Aststummel, Moos oben)
  stock_1-4       herabgefallene Äste/Stöcke im Wald (einzeln oder zu zweit, mit Gabelungen)
  treibholz_1-2   ausgebleichtes Treibholz am Strand
  alge_1-3        Algenbüschel im Flussbett (lange, schmale Bänder)
Material-Slots: rinde, schnitt, moos, treibholz, alge (Godot ersetzt sie in scripts/natur.gd).
Koordinaten: Blender Z oben -> Godot Y oben; Fuß/Unterseite bei z = 0.
Aufruf: python natur_modelle.py -- <zielordner>   (bpy 5.2 als Python-Modul oder blender -b -P …)"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise

MATS = ["rinde", "schnitt", "moos", "treibholz", "alge"]
RINDE, SCHNITT, MOOS, TREIBHOLZ, ALGE = range(5)


class Bau:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def roehre(self, punkte, radien, seiten, mat, deckel=None, moos_ab=None, wackeln=0.0, seed=0):
        """Röhre entlang einer Punktliste. UV: u = Umfang (0,8 m je Einheit), v = Länge.
        deckel: Material für die Endfläche (z. B. Schnittfläche) oder None = spitz zulaufen lassen.
        moos_ab: Flächen, deren Normale weiter als dieser Wert nach oben zeigt, bekommen Moos (liegende Stämme)."""
        ringe = []
        laenge = 0.0
        vs = []
        off = Vector((seed * 2.3, seed * 5.1, seed * 0.7))
        for k, (p, r) in enumerate(zip(punkte, radien)):
            if k > 0:
                laenge += (p - punkte[k - 1]).length
            vs.append(laenge)
            d = (punkte[min(k + 1, len(punkte) - 1)] - punkte[max(k - 1, 0)]).normalized()
            u = d.orthogonal().normalized(); w = d.cross(u)
            ring = []
            for i in range(seiten + 1):
                a = 2 * math.pi * i / seiten
                wob = 1 + wackeln * noise.noise(Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, laenge * 0.8)) + off)
                ring.append(self.bm.verts.new(p + (u * math.cos(a) + w * math.sin(a)) * r * wob))
            ringe.append(ring)
        umfang = max(1, round(2 * math.pi * radien[0] / 0.8))
        for k in range(len(ringe) - 1):
            for i in range(seiten):
                f = self.bm.faces.new((ringe[k][i], ringe[k][i + 1], ringe[k + 1][i + 1], ringe[k + 1][i]))
                f.material_index = mat
                for l, (ii, kk) in zip(f.loops, ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1))):
                    l[self.uv].uv = (ii / seiten * umfang, vs[kk] / 0.8)
                if moos_ab is not None:
                    f.normal_update()
                    if f.normal.z > moos_ab:
                        f.material_index = MOOS
        ende = ringe[-1]
        if deckel is None:
            spitze = self.bm.verts.new(punkte[-1] + (punkte[-1] - punkte[-2]).normalized() * radien[-1] * 1.5)
            for i in range(seiten):
                f = self.bm.faces.new((ende[i], ende[i + 1], spitze)); f.material_index = mat
                for l, uv in zip(f.loops, ((i / seiten, 0), ((i + 1) / seiten, 0), (0.5, 1))): l[self.uv].uv = uv
        else:
            f = self.bm.faces.new(ende[:-1]); f.material_index = deckel
            m = punkte[-1]; r = radien[-1]
            u = (punkte[-1] - punkte[-2]).normalized().orthogonal().normalized()
            w = (punkte[-1] - punkte[-2]).normalized().cross(u)
            for l in f.loops:
                q = l.vert.co - m
                l[self.uv].uv = (0.5 + q.dot(u) / r * 0.48, 0.5 + q.dot(w) / r * 0.48)
        return ringe

    def bruchkante(self, ring, mitte, richtung, r, rnd, mat):
        """abgebrochenes Ende: zackige Splitter statt glatter Schnitt"""
        n = len(ring) - 1
        spitzen = []
        for i in range(n):
            hoehe = r * rnd.uniform(0.2, 1.6) if rnd.random() < 0.6 else r * rnd.uniform(0.0, 0.3)
            spitzen.append(self.bm.verts.new(ring[i].co + richtung * hoehe + (mitte - ring[i].co) * rnd.uniform(0.2, 0.6)))
        kern = self.bm.verts.new(mitte + richtung * r * 0.3)
        for i in range(n):
            j = (i + 1) % n
            f = self.bm.faces.new((ring[i], ring[i + 1] if i + 1 < n else ring[0], spitzen[j], spitzen[i])); f.material_index = mat
            for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): l[self.uv].uv = uv
            f = self.bm.faces.new((spitzen[i], spitzen[j], kern)); f.material_index = SCHNITT
            for l, uv in zip(f.loops, ((0.2, 0.2), (0.8, 0.2), (0.5, 0.5))): l[self.uv].uv = uv

    def band(self, basis, richtung, laenge, breite, schwung, drehung, mat, stufen=5):
        """flaches, sich wiegendes Band (Alge), doppelseitig im Material"""
        d = richtung.normalized()
        quer = Matrix.Rotation(drehung, 3, d) @ d.orthogonal().normalized()
        vorher = None
        for k in range(stufen + 1):
            s = k / stufen
            c = basis + d * laenge * s + quer.cross(d) * schwung * laenge * s * s
            b = breite * (1 - 0.7 * s)
            paar = (self.bm.verts.new(c - quer * b / 2), self.bm.verts.new(c + quer * b / 2), s)
            if vorher:
                f = self.bm.faces.new((vorher[0], vorher[1], paar[1], paar[0])); f.material_index = mat
                for l, uv in zip(f.loops, ((0, vorher[2]), (1, vorher[2]), (1, s), (0, s))): l[self.uv].uv = uv
            vorher = paar


def krumm(start, richtung, laenge, schritte, biegung, rnd):
    """leicht gekrümmte Linie"""
    pts = [start]
    d = richtung.normalized()
    for k in range(schritte):
        d = (d + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * biegung).normalized()
        pts.append(pts[-1] + d * laenge / schritte)
    return pts


def totbaum(seed):
    """toter Baum: krummer Stamm, kahle Äste nach oben dünner, abgebrochene Spitze, Wurzelanlauf"""
    rnd = random.Random(seed * 7121)
    b = Bau()
    H = rnd.uniform(6.0, 9.0); r0 = rnd.uniform(0.2, 0.3)
    neig = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.06
    pts = [Vector((0, 0, -0.3))]
    z = 0.0
    while z < H:
        z += 0.6
        pts.append(Vector((0, 0, z)) + neig * z * z / H + Vector((noise.noise(Vector((z * 0.3, seed, 0))), noise.noise(Vector((0, z * 0.3, seed))), 0)) * r0 * 1.5)
    radien = [r0 * (1.5 if i == 0 else max(0.25, 1 - (p.z / H) ** 1.2)) for i, p in enumerate(pts)]
    ringe = b.roehre(pts, radien, 10, RINDE, deckel=SCHNITT, wackeln=0.12, seed=seed)
    b.bruchkante(ringe[-1], pts[-1], (pts[-1] - pts[-2]).normalized(), radien[-1], rnd, RINDE)
    # Äste: nach oben häufiger, schräg aufwärts, manche abgebrochen, längere mit Seitenzweigen
    z = rnd.uniform(1.6, 2.4)
    while z < H * 0.95:
        a = rnd.uniform(0, 2 * math.pi)
        t = z / H
        d = Vector((math.cos(a), math.sin(a), rnd.uniform(0.2, 0.9))).normalized()
        L = rnd.uniform(0.8, 2.6) * (1.2 - 0.6 * t)
        if rnd.random() < 0.3:
            L *= rnd.uniform(0.15, 0.35)
        k = min(int(z / 0.6) + 1, len(pts) - 1)
        p0 = pts[k] + d * radien[k] * 0.5
        ast = krumm(p0, d, L, 3, 0.35, rnd)
        rr = max(0.02, radien[k] * 0.35)
        b.roehre(ast, [rr, rr * 0.6, rr * 0.35, rr * 0.12], 5, RINDE)
        if L > 1.0:
            for _ in range(rnd.randint(1, 2)):
                q = ast[rnd.randint(1, 2)]
                sd = (d + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 0.8)))).normalized()
                b.roehre(krumm(q, sd, L * rnd.uniform(0.3, 0.5), 2, 0.4, rnd), [rr * 0.4, rr * 0.2, rr * 0.06], 4, RINDE)
        z += rnd.uniform(0.35, 0.9)
    # Wurzelanlauf: 4–5 kurze Wurzeln, die schräg in den Boden laufen
    for i in range(rnd.randint(4, 5)):
        a = 2 * math.pi * i / 5 + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), -0.35)).normalized()
        p0 = Vector((0, 0, 0.35))
        b.roehre([p0, p0 + d * 0.7, p0 + d * 1.3], [r0 * 0.55, r0 * 0.35, r0 * 0.12], 5, RINDE)
    return b.bm


def baumstamm(seed):
    """umgestürzter Stamm entlang X, liegt auf dem Boden (z = 0), oben bemoost; ein Ende gesägt oder abgebrochen"""
    rnd = random.Random(seed * 3301)
    b = Bau()
    L = rnd.uniform(4.0, 7.0); r = rnd.uniform(0.22, 0.38)
    pts = []
    for k in range(int(L / 0.5) + 1):
        x = -L / 2 + k * 0.5
        pts.append(Vector((x, noise.noise(Vector((x * 0.25, seed, 0))) * 0.25, r * 0.85)))
    radien = [r * (1.15 - 0.3 * k / (len(pts) - 1)) for k in range(len(pts))]
    radien[0] *= 1.25 # Stammfuß
    pts.reverse(); radien.reverse() # vom dünnen Ende zum Fuß, damit der Fuß das Ende mit Deckel ist
    ringe = b.roehre(pts, radien, 12, RINDE, deckel=SCHNITT, moos_ab=0.55, wackeln=0.1, seed=seed)
    if seed % 2 == 1: # Fuß abgebrochen statt gesägt
        b.bruchkante(ringe[-1], pts[-1], (pts[-1] - pts[-2]).normalized(), radien[-1], rnd, RINDE)
    # dünnes Ende: abgebrochene Spitze
    d0 = (pts[0] - pts[1]).normalized()
    spitze = b.roehre([pts[0], pts[0] + d0 * 0.4], [radien[0], radien[0] * 0.6], 12, RINDE, deckel=SCHNITT)
    b.bruchkante(spitze[-1], pts[0] + d0 * 0.4, d0, radien[0] * 0.6, rnd, RINDE)
    # Aststummel, teils in den Boden gedrückt
    for _ in range(rnd.randint(3, 6)):
        k = rnd.randint(1, len(pts) - 3)
        a = rnd.uniform(0, 2 * math.pi)
        d = Vector((rnd.uniform(-0.3, 0.3), math.cos(a), math.sin(a))).normalized()
        if d.z < -0.3:
            continue
        p0 = pts[k] + d * radien[k] * 0.7
        lang = rnd.uniform(0.15, 0.5) if rnd.random() < 0.7 else rnd.uniform(0.8, 1.6)
        rr = radien[k] * 0.22
        b.roehre(krumm(p0, d, lang, 2, 0.3, rnd), [rr, rr * 0.6, rr * 0.2], 5, RINDE, deckel=SCHNITT if lang < 0.5 else None)
    return b.bm


def stock(seed):
    """1–2 herabgefallene Äste mit Gabelungen, liegen flach (z = Radius)"""
    rnd = random.Random(seed * 1777)
    b = Bau()
    for n in range(1 if seed % 2 else 2):
        L = rnd.uniform(0.7, 1.8); r = rnd.uniform(0.018, 0.04)
        a = rnd.uniform(0, math.pi)
        start = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), r))
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = krumm(start, d, L, 4, 0.25, rnd)
        for p in pts:
            p.z = r * rnd.uniform(0.8, 1.2)
        b.roehre(pts, [r, r * 0.85, r * 0.7, r * 0.5, r * 0.25], 5, RINDE, deckel=SCHNITT)
        for _ in range(rnd.randint(1, 3)):
            q = pts[rnd.randint(1, 3)].copy()
            sd = (d + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.9).normalized()
            zweig = krumm(q, sd, L * rnd.uniform(0.25, 0.5), 2, 0.3, rnd)
            for p in zweig:
                p.z = max(p.z, r * 0.6)
            b.roehre(zweig, [r * 0.55, r * 0.35, r * 0.1], 4, RINDE)
    return b.bm


def treibholz(seed):
    """ausgebleichter, glatter Ast/Stamm mit Wurzelresten, liegt am Strand"""
    rnd = random.Random(seed * 919)
    b = Bau()
    L = rnd.uniform(2.0, 3.5); r = rnd.uniform(0.1, 0.17)
    pts = krumm(Vector((-L / 2, 0, r)), Vector((1, 0, 0)), L, 6, 0.15, rnd)
    for p in pts:
        p.z = r * 0.9
    ringe = b.roehre(pts, [r * (1.2 - 0.7 * k / 6) for k in range(7)], 8, TREIBHOLZ, wackeln=0.15, seed=seed)
    # Wurzelreste am dicken Ende
    for i in range(rnd.randint(3, 5)):
        a = rnd.uniform(0, 2 * math.pi)
        d = Vector((-0.6, math.cos(a), math.sin(a) * 0.6)).normalized()
        b.roehre(krumm(pts[0], d, rnd.uniform(0.3, 0.8), 2, 0.4, rnd), [r * 0.4, r * 0.25, r * 0.08], 4, TREIBHOLZ)
    return b.bm


def alge(seed):
    """Büschel aus 10–16 langen Bändern, die im Wasser liegen (leicht aufgerichtet, in Strömungsrichtung +X)"""
    rnd = random.Random(seed * 4243)
    b = Bau()
    for _ in range(rnd.randint(10, 16)):
        p = Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 0))
        d = Vector((1.0, rnd.uniform(-0.6, 0.6), rnd.uniform(0.3, 1.2))).normalized()
        b.band(p, d, rnd.uniform(0.35, 0.9), rnd.uniform(0.03, 0.06), rnd.uniform(-0.4, 0.4), rnd.uniform(0, math.pi), ALGE)
    return b.bm


def export(name, bm, out):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in MATS:
        me.materials.append(bpy.data.materials.get(m) or bpy.data.materials.new(m))
    for p in me.polygons:
        p.use_smooth = p.material_index != SCHNITT
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + ".glb"), export_format="GLB",
                              use_selection=True, export_materials="EXPORT")
    print(f"  {name}.glb: {sum(len(p.vertices) - 2 for p in me.polygons)} Dreiecke")
    bpy.data.objects.remove(ob)


if __name__ == "__main__":
    out = sys.argv[-1]; os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for v in (1, 2, 3):
        export(f"totbaum_{v}", totbaum(v), out)
        export(f"baumstamm_{v}", baumstamm(v), out)
        export(f"alge_{v}", alge(v), out)
    for v in (1, 2, 3, 4):
        export(f"stock_{v}", stock(v), out)
    for v in (1, 2):
        export(f"treibholz_{v}", treibholz(v), out)
