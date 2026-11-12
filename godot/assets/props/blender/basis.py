"""Bausteine für die Prop-Modelle: Bretter, Balken, Rundhölzer, Rohre, Drehkörper, Tuch.
Jedes Teil wird im eigenen Koordinatensystem gebaut (Länge entlang x), bekommt dort seine UVs in Metern
(Holz: u entlang der Faser) und wird dann mit einer Matrix an seinen Platz gesetzt.
Ein Modell sammelt alle Teile in einem bmesh, Materialien als Slots mit festen Namen (siehe MATERIALIEN).
Maße in Metern, Boden bei z = 0, y = vorne/hinten, x = links/rechts."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, noise
from texturen import KACHEL

MATERIALIEN = ["holz", "holz_alt", "holz_verkohlt", "eisen", "stoff", "seil", "stein", "putz", "schindeln",
               "dielen", "glut", "glas", "asche"]
## Kachelgrößen der Materialien ohne eigene Textur
KACHEL_EXTRA = {"glas": (1.0, 1.0), "asche": (1.0, 1.0)}


def kachel(mat):
    return KACHEL.get(mat, KACHEL_EXTRA.get(mat, (1.0, 1.0)))


def M(pos=(0, 0, 0), rot=(0, 0, 0), skal=1.0):
    """Matrix aus Position, Drehung in Grad (x, y, z) und Skalierung."""
    r = Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()
    s = Matrix.Diagonal(Vector((skal, skal, skal, 1.0)) if not isinstance(skal, (tuple, list))
                        else Vector((*skal, 1.0)))
    return Matrix.Translation(Vector(pos)) @ r @ s


def ausrichten(a, b, oben=None):
    """Matrix, die ein Teil mit Länge entlang x von Punkt a nach Punkt b legt (Ursprung des Teils = Mitte).
    oben: Richtung, in die die lokale z-Achse (Dicke) ungefähr zeigen soll."""
    a, b = Vector(a), Vector(b)
    x = (b - a).normalized()
    if oben is None:
        oben = Vector((0, 0, 1)) if abs(x.z) < 0.95 else Vector((0, -1, 0))
    z = Vector(oben) - x * x.dot(Vector(oben))
    if z.length < 1e-6:
        z = x.orthogonal()
    z.normalize()
    y = z.cross(x)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    return Matrix.Translation((a + b) * 0.5) @ rot


# ---------------------------------------------------------------- Grundformen (lokal, Länge entlang x)

def quader(lx, ly, lz, nx=1, ny=1, nz=1, fase=0.0):
    """Quader um den Ursprung, unterteilt (nx, ny, nz), Kanten optional gefast."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if nx > 1 or ny > 1 or nz > 1:
        _unterteilen(bm, nx, ny, nz)
    for v in bm.verts:
        v.co = Vector((v.co.x * lx, v.co.y * ly, v.co.z * lz))
    if fase > 0:
        kanten = [e for e in bm.edges if _ist_aussenkante(e)]
        bmesh.ops.bevel(bm, geom=kanten, offset=min(fase, 0.45 * min(lx, ly, lz)), segments=1,
                        affect="EDGES", profile=0.5)
    return bm


def _ist_aussenkante(e):
    if len(e.link_faces) != 2:
        return False
    return e.link_faces[0].normal.dot(e.link_faces[1].normal) < 0.5


def _unterteilen(bm, nx, ny, nz):
    """Schneidet den Einheitswürfel mit Ebenen (bisect), damit lange Teile sich biegen lassen."""
    for achse, n in ((0, nx), (1, ny), (2, nz)):
        for i in range(1, n):
            t = -0.5 + i / n
            no = Vector((1 if achse == 0 else 0, 1 if achse == 1 else 0, 1 if achse == 2 else 0))
            co = no * t
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no)


def rundholz(r, l, seg=10, nx=1, r2=None, kappen=True):
    """Zylinder entlang x von -l/2 bis l/2, Radius r (an einem Ende r2 für verjüngte Stämme)."""
    r2 = r if r2 is None else r2
    bm = bmesh.new()
    ringe = []
    for i in range(nx + 1):
        t = i / nx; x = -l / 2 + l * t; rr = r + (r2 - r) * t
        ringe.append([bm.verts.new((x, rr * math.cos(2 * math.pi * k / seg), rr * math.sin(2 * math.pi * k / seg)))
                      for k in range(seg)])
    for a, b in zip(ringe, ringe[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if kappen:
        bm.faces.new(list(reversed(ringe[0])))
        bm.faces.new(ringe[-1])
    bm.normal_update()
    return bm


def drehkoerper(profil, seg=16, oben_zu=True, unten_zu=True, winkel=(0.0, 360.0)):
    """Drehkörper um die z-Achse aus Profilpunkten (radius, z), von unten nach oben."""
    bm = bmesh.new()
    voll = abs(winkel[1] - winkel[0]) >= 359.9
    n = seg if voll else seg + 1
    ringe = []
    for r, z in profil:
        ring = []
        for k in range(n):
            a = math.radians(winkel[0] + (winkel[1] - winkel[0]) * k / seg)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        ringe.append(ring)
    for a, b in zip(ringe, ringe[1:]):
        for k in range(seg):
            k2 = (k + 1) % n if voll else k + 1
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if voll:
        if unten_zu and profil[0][0] > 1e-4:
            bm.faces.new(list(reversed(ringe[0])))
        if oben_zu and profil[-1][0] > 1e-4:
            bm.faces.new(ringe[-1])
    bm.normal_update()
    return bm


def rohr(punkte, r, seg=6, kappen=True, r_ende=None):
    """Rohr entlang eines Polygonzugs (Seil, Bügel, Kette). Ringe mit Parallel-Transport ausgerichtet."""
    pts = [Vector(p) for p in punkte]
    bm = bmesh.new()
    tang = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        tang.append((b - a).normalized())
    hilf = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    n = tang[0].cross(hilf).normalized()
    ringe = []
    for i, p in enumerate(pts):
        if i > 0:
            n = (n - tang[i] * n.dot(tang[i])).normalized()
        bn = tang[i].cross(n)
        rr = r if r_ende is None else r + (r_ende - r) * i / (len(pts) - 1)
        ringe.append([bm.verts.new(p + (n * math.cos(2 * math.pi * k / seg) + bn * math.sin(2 * math.pi * k / seg)) * rr)
                      for k in range(seg)])
    for a, b in zip(ringe, ringe[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if kappen:
        bm.faces.new(list(reversed(ringe[0])))
        bm.faces.new(ringe[-1])
    bm.normal_update()
    return bm


def flaeche(punkte_gitter, dicke=0.0, loch=None):
    """Fläche aus einem Gitter von Punkten [zeile][spalte] (Tuch, Plane), optional mit Dicke.
    loch(i, j) -> True: an dieser Zelle fehlt das Tuch (Risse)."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in zeile] for zeile in punkte_gitter]
    for i in range(len(vs) - 1):
        for j in range(len(vs[0]) - 1):
            if loch and loch(i, j):
                continue
            bm.faces.new((vs[i][j], vs[i][j + 1], vs[i + 1][j + 1], vs[i + 1][j]))
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bm.normal_update()
    if dicke > 0:
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=dicke)
        bm.normal_update()
    return bm


def brocken(rnd, gx, gy, gz, rauh=0.18, unterteilung=2):
    """Unregelmäßiger Feldstein (Icosphere mit Noise), Maße als Halbachsen."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=unterteilung, radius=1.0)
    o = Vector([rnd.uniform(-40, 40) for _ in range(3)])
    for v in bm.verts:
        n = v.co.normalized()
        f = 1 + rauh * noise.noise(n * 1.3 + o) + rauh * 0.5 * noise.noise(n * 3.1 + o) \
            + rauh * 0.25 * abs(noise.noise(n * 7.0 + o))
        v.co = Vector((n.x * gx, n.y * gy, n.z * gz)) * f
    bm.normal_update()
    return bm


def klotz(rnd, lx, ly, lz, fase=0.02, rauh=0.008, abgeschlagen=0.0):
    """Behauener Steinblock. abgeschlagen > 0: Kanten und Ecken bröckeln (Ruinen)."""
    bm = quader(lx, ly, lz, 3, 2, 2, fase=fase)
    verbiegen(bm, rnd, rauh, 0.25)
    verbiegen(bm, rnd, rauh * 0.6, 0.07)
    if abgeschlagen > 0:
        o = Vector([rnd.uniform(-40, 40) for _ in range(3)])
        for v in bm.verts:
            rel = Vector((abs(v.co.x) / (lx / 2), abs(v.co.y) / (ly / 2), abs(v.co.z) / (lz / 2)))
            ecke = max(0.0, min(rel) - 0.5) * 2               # nur an Kanten/Ecken
            n = noise.noise(v.co * 6 + o) * 0.5 + 0.5
            v.co *= 1 - abgeschlagen * ecke * n * 0.22
    bm.normal_update()
    return bm


# ---------------------------------------------------------------- Verformung

def verbiegen(bm, rnd, staerke, groesse=0.8, achsen=(1, 1, 1)):
    """Leichte, weiche Unregelmäßigkeit (kein CAD-Look): verschiebt Punkte mit niederfrequentem Noise."""
    o = Vector([rnd.uniform(-50, 50) for _ in range(3)])
    for v in bm.verts:
        p = v.co / groesse + o
        d = Vector((noise.noise(p), noise.noise(p + Vector((17.1, 0, 0))), noise.noise(p + Vector((0, 31.7, 0)))))
        v.co += Vector((d.x * achsen[0], d.y * achsen[1], d.z * achsen[2])) * staerke


def bruchkante(bm, rnd, seite=1, tiefe=0.08, spitzen=0.5):
    """Bricht ein Teil am Ende (seite +1 = +x, -1 = -x) zackig ab: die Endpunkte werden unterschiedlich weit
    zurückgezogen, einige bleiben als Splitter stehen. Das Teil braucht dafür Unterteilung quer (ny/nz)."""
    xs = [v.co.x for v in bm.verts]
    ende = max(xs) if seite > 0 else min(xs)
    for v in bm.verts:
        if abs(v.co.x - ende) < 1e-4:
            z = rnd.random()
            rueck = tiefe * (z ** 0.5) if z > spitzen * 0.4 else -tiefe * 0.5 * rnd.random()
            v.co.x -= seite * rueck
            v.co.y *= rnd.uniform(0.7, 1.0); v.co.z *= rnd.uniform(0.7, 1.0)


# ---------------------------------------------------------------- UVs

def uv_box(bm, mat, versatz=(0.0, 0.0), faser=0):
    """Box-Projektion in lokalen Koordinaten, Meter durch Kachelgröße. Seitenflächen: u entlang der Faser-Achse
    (0 = x, 2 = z, z. B. für Fassdauben)."""
    ku, kv = kachel(mat)
    uv = bm.loops.layers.uv.verify()
    perm = (0, 1, 2) if faser == 0 else ((2, 0, 1) if faser == 2 else (1, 2, 0))
    for f in bm.faces:
        n = Vector([f.normal[i] for i in perm])
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = Vector([l.vert.co[i] for i in perm])
            if ax == 0:
                u, v = c.y, c.z
            elif ax == 1:
                u, v = c.x, c.z
            else:
                u, v = c.x, c.y
            l[uv].uv = (u / ku + versatz[0], v / kv + versatz[1])


def uv_zylinder(bm, mat, r, versatz=(0.0, 0.0), achse=0):
    """Zylinder-Projektion um die x- (achse 0) oder z-Achse (achse 2): u entlang der Achse, v = Bogenlänge.
    Kappen bekommen eine ebene Projektion."""
    ku, kv = kachel(mat)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        kappe = abs(n[achse]) > 0.8
        us = []
        for l in f.loops:
            c = l.vert.co
            if achse == 0:
                lang, q1, q2 = c.x, c.y, c.z
            else:
                lang, q1, q2 = c.z, c.x, c.y
            if kappe:
                us.append((q1 / ku, q2 / kv))
            else:
                a = math.atan2(q2, q1)
                us.append((lang / ku, a * r / kv))
        if not kappe:   # Naht: Sprung über ±pi glätten
            vs = [u[1] for u in us]
            if max(vs) - min(vs) > math.pi * r / kv:
                us = [(u, v + 2 * math.pi * r / kv if v < 0 else v) for u, v in us]
        for l, (u, v) in zip(f.loops, us):
            l[uv].uv = (u + versatz[0], v + versatz[1])


def uv_rohr(bm, mat, seg, r):
    """UVs für rohr(): u = Länge entlang des Rohrs, v = Umfang."""
    ku, kv = kachel(mat)
    uv = bm.loops.layers.uv.verify()
    verts = bm.verts[:]
    n_ringe = len(verts) // seg
    laenge = [0.0]
    for i in range(1, n_ringe):
        laenge.append(laenge[-1] + (verts[i * seg].co - verts[(i - 1) * seg].co).length)
    for f in bm.faces:
        if len(f.verts) != 4:
            for l in f.loops:
                l[uv].uv = (l.vert.co.x / ku, l.vert.co.y / kv)
            continue
        ks = [l.vert.index % seg for l in f.loops]
        nahtsprung = max(ks) - min(ks) > 1
        for l in f.loops:
            i = l.vert.index // seg; k = l.vert.index % seg
            if nahtsprung and k == 0:
                k = seg
            l[uv].uv = (laenge[i] / ku, k / seg * 2 * math.pi * r / kv)


# ---------------------------------------------------------------- Modell

class Modell:
    """Sammelt Teile zu einem Mesh-Objekt mit Material-Slots."""

    def __init__(self, name, saat=1):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.verify()
        self.mats = []
        self.rnd = random.Random(saat)
        self.G = None          # optionale Matrix für alle folgenden Teile (z. B. umgekipptes Modell)

    def _mat_index(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def teil(self, bm, mat, matrix=None, uv="box", r=0.0, seg=6, versatz=None):
        """Fügt ein lokal gebautes Teil hinzu. uv: 'box', 'boxz' (Faser entlang z), 'zyl' (Achse x),
        'zylz' (Achse z), 'rohr', None."""
        bm.verts.ensure_lookup_table(); bm.verts.index_update(); bm.normal_update()
        if versatz is None:
            versatz = (self.rnd.random(), self.rnd.random())
        if uv == "box":
            uv_box(bm, mat, versatz)
        elif uv == "boxz":
            uv_box(bm, mat, versatz, faser=2)
        elif uv == "zyl":
            uv_zylinder(bm, mat, r, versatz, 0)
        elif uv == "zylz":
            uv_zylinder(bm, mat, r, versatz, 2)
        elif uv == "rohr":
            uv_rohr(bm, mat, seg, r)
        idx = self._mat_index(mat)
        for f in bm.faces:
            f.material_index = idx
        if matrix is not None:
            bm.transform(matrix)
        if self.G is not None:
            bm.transform(self.G)
        me = bpy.data.meshes.new("tmp")
        bm.to_mesh(me); bm.free()
        self.bm.from_mesh(me)
        bpy.data.meshes.remove(me)

    # Kurzformen ------------------------------------------------------------
    def brett(self, l, b, d, matrix, mat="holz", nx=None, fase=0.006, biegen=0.006, bruch=0, bruch_tiefe=0.08):
        """Brett/Balken: Länge l entlang x, Breite b (y), Dicke d (z). bruch = +1/-1: Ende abgebrochen."""
        nx = nx or max(1, int(l / 0.3))
        ny = 4 if bruch else 1
        bm = quader(l, b, d, nx, ny, 2 if bruch else 1, fase=0 if bruch else fase)
        if bruch:
            bruchkante(bm, self.rnd, bruch, bruch_tiefe)
        if biegen:
            verbiegen(bm, self.rnd, biegen, 0.6)
        self.teil(bm, mat, matrix)

    def stab(self, a, b, r, mat="holz", seg=8, r2=None, biegen=0.004, kappen=True, uvmodus="zyl"):
        """Rundholz/Stange von Punkt a nach Punkt b."""
        l = (Vector(b) - Vector(a)).length
        bm = rundholz(r, l, seg, max(1, int(l / 0.35)), r2, kappen)
        if biegen:
            verbiegen(bm, self.rnd, biegen, 0.5)
        self.teil(bm, mat, ausrichten(a, b), uv=uvmodus, r=r)

    def kantholz(self, a, b, b_, d, mat="holz", oben=None, fase=0.008, bruch=0, biegen=0.004):
        """Kantholz (Breite b_ quer, Dicke d) zwischen zwei Punkten; die Dicke zeigt in Richtung oben."""
        l = (Vector(b) - Vector(a)).length
        m = ausrichten(a, b, oben)
        self.brett(l, b_, d, m, mat, fase=fase, biegen=biegen, bruch=bruch)

    def seil(self, punkte, r=0.012, seg=6, mat="seil"):
        bm = rohr(punkte, r, seg)
        self.teil(bm, mat, None, uv="rohr", r=r, seg=seg)

    def fertig(self, glatt_winkel=40.0):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts[:], dist=1e-5)
        self.bm.normal_update()
        self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        for m in self.mats:
            ob.data.materials.append(material(m))
        for p in me.polygons:
            p.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(glatt_winkel))
        return ob


# ---------------------------------------------------------------- Materialien (Blender, für Vorschau und glTF-Namen)

TEXTUR_ORDNER = None   # wird von den Erzeuger-Skripten gesetzt
GRUNDFARBE = {"holz": (0.33, 0.21, 0.11), "holz_alt": (0.38, 0.34, 0.29), "holz_verkohlt": (0.03, 0.03, 0.03),
              "eisen": (0.13, 0.12, 0.12), "stoff": (0.58, 0.52, 0.39), "seil": (0.45, 0.37, 0.24),
              "stein": (0.47, 0.45, 0.41), "putz": (0.74, 0.70, 0.61), "schindeln": (0.32, 0.26, 0.20),
              "dielen": (0.38, 0.26, 0.15), "glut": (0.9, 0.3, 0.05), "glas": (0.75, 0.62, 0.38),
              "asche": (0.22, 0.21, 0.20)}


def material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    import os
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    c = GRUNDFARBE.get(name, (0.5, 0.5, 0.5))
    bsdf.inputs["Base Color"].default_value = (*[x ** 2.2 for x in c], 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    if name == "eisen":
        bsdf.inputs["Metallic"].default_value = 0.65
    if name == "glas":
        bsdf.inputs["Roughness"].default_value = 0.15
        bsdf.inputs["Transmission Weight"].default_value = 0.9
        bsdf.inputs["Alpha"].default_value = 0.45
    if name == "glut":
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.3, 0.05, 1)
    pfad = lambda art: os.path.join(TEXTUR_ORDNER or "", f"{name}_{art}.jpg")
    if TEXTUR_ORDNER and os.path.exists(pfad("farbe")):
        uvk = nt.nodes.new("ShaderNodeUVMap")
        def bild(art, nicht_farbe):
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = bpy.data.images.load(pfad(art), check_existing=True)
            if nicht_farbe:
                n.image.colorspace_settings.name = "Non-Color"
            nt.links.new(uvk.outputs["UV"], n.inputs["Vector"])
            return n
        f = bild("farbe", False); nt.links.new(f.outputs["Color"], bsdf.inputs["Base Color"])
        r = bild("rauheit", True); nt.links.new(r.outputs["Color"], bsdf.inputs["Roughness"])
        nm = bild("normal", True)
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 1.0
        nt.links.new(nm.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        if name == "glut":
            nt.links.new(f.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 6.0
    return m
