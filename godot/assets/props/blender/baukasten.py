"""Haus-Baukasten im 1-m-Raster, jedes Teil heil und kaputt. Die Stockwerkshöhe legt Philipp beim Bauen selbst fest.
Aufruf: python baukasten.py -- <zielordner/modelle> [--nur wand,balken_2m] [--vorschau <ordner>]

Grundregeln (Skizze: /mnt/project-files/bilder/props/raster_skizze.png):
  - Wände (10 cm) und Balken (20 x 20 cm) liegen MITTIG auf den Rasterlinien.
  - Ursprung jedes Teils ist sein Anfangspunkt auf einem Rasterpunkt; das Teil läuft von dort 1 oder 2 m entlang +x.
    Gedreht wird immer um diesen Punkt.
  - Alle Stoßflächen sind eben und liegen genau im Raster (für Blueprints und das spätere Backen).
  - In Blender zeigt die Vorderseite nach -y (in Godot nach +z).

Teile:
  wand          massive Wand 2 x 2 m (x 0..2, z 0..2), 0.10 m dick (y -0.05..0.05), Putz auf beiden Seiten.
  wand_2x1      2 m breit, 1 m hoch (hochkant gedreht: 1 m breit, 2 m hoch).
  wand_1x1      1 x 1 m.
  balken_2m     Balken 20 x 20 cm für 2 m (bzw. 1 m) von Rasterpunkt zu Rasterpunkt, steht an beiden Enden 10 cm über:
  balken_1m     x -0.1..2.1 (2,2 m lang). Mitte auf der Rasterlinie (y, z um 0). Waagerecht auf eine Wandkante legen,
                als Ständer um 90° hochkant drehen. An jedem Rasterpunkt reicht ein Balken damit genau so weit wie ein
                querliegender, Ecken sind ohne Stufe geschlossen.
  strebe_2m     Schräge über eine 2 x 2-Wand: Mittellinie von (0|0) nach (2|2), Enden waagerecht abgeschnitten.

Vorrang bei Überlappung (welche Fläche sichtbar ist) regelt das Material in Godot (materialien/balken.gdshader):
je waagerechter, desto höher. Die Teile sind dafür alle gleich dick und nicht verbogen."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basis
from basis import Modell, M, quader, flaeche, bruchkante, klotz, drehkoerper, verbiegen
import props

RASTER = 2.0
WAND_D = 0.10                    # Wanddicke
BALKEN = 0.20                    # Balkenquerschnitt 20 x 20 cm, Mitte auf der Rasterlinie
UEBERSTAND = BALKEN / 2           # Balken stehen je Ende 10 cm über den Rasterpunkt (2 m Raster -> 2,2 m lang)


def mitte_y(bm):
    """Schiebt die aufgedickte Wand mittig auf die Rasterlinie (y -0,05..0,05), egal in welche Richtung solidify ging."""
    ys = [v.co.y for v in bm.verts]
    d = (min(ys) + max(ys)) / 2
    for v in bm.verts:
        v.co.y -= d


def wand_flaeche(m, kaputt, breite, hoehe):
    """Massive Wand breite x hoehe (x 0..breite, z 0..hoehe). Kaputt: ausgebrochenes Loch,
    abgebröckelte Oberkante (Schutt kommt später als eigene Module). Alle Außenkanten, die stehen bleiben, liegen im Raster."""
    m.G = Matrix.Translation((breite / 2, 0, 0))         # gebaut um die Mitte, Ursprung aber am Anfangspunkt
    if not kaputt:
        m.teil(quader(breite, WAND_D, hoehe, int(breite * 2), 1, int(hoehe * 2)), "putz", M((0, 0, hoehe / 2)),
               versatz=(0, 0))
        m.G = None
        return
    # Gitter aus 5-cm-Zellen: Zellen im Loch und über der Bruchkante fehlen, dann auf Wanddicke aufgedickt
    z = 0.05
    nx, nz = round(breite / z), round(hoehe / z)
    sx, sz = breite / 2, hoehe / 2                       # Maßstab gegenüber der 2 x 2-Wand
    def fehlt(i, j):                                     # i = Zeile (Höhe), j = Spalte (x)
        x = -breite / 2 + (j + 0.5) * z; h = (i + 0.5) * z
        xr = x / sx; hr = h / sz                         # auf 2 x 2 m umgerechnet
        kante = 1.75 - 0.45 * max(0.0, xr + 0.2) + 0.12 * noise.noise(Vector((xr * 4, 0.3, 1.1)))
        r = 0.38 + 0.1 * noise.noise(Vector((xr * 5, hr * 5, 2.7)))
        return hr > kante or ((xr + 0.35) ** 2 + ((hr - 1.0) * 1.2) ** 2) ** 0.5 < r
    gitter = [[(-breite / 2 + j * z, -WAND_D / 2, i * z) for j in range(nx + 1)] for i in range(nz + 1)]
    bm = flaeche(gitter, 0.0, fehlt)
    # Bruchränder zackig verschieben, damit keine Treppenstufen bleiben (Außenkanten bleiben im Raster)
    for v in bm.verts:
        if any(len(e.link_faces) < 2 for e in v.link_edges) and v.co.z > 1e-4 and abs(abs(v.co.x) - breite / 2) > 1e-4:
            v.co.x += m.rnd.uniform(-0.02, 0.02); v.co.z += m.rnd.uniform(-0.025, 0.02)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=-WAND_D)
    mitte_y(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # Außenflächen zeigen nach außen (sonst sieht man die Rückseite)
    bm.normal_update()
    m.teil(bm, "putz", None)
    m.G = None


def wand(m, kaputt):
    wand_flaeche(m, kaputt, 2.0, 2.0)


def wand_2x1(m, kaputt):
    wand_flaeche(m, kaputt, 2.0, 1.0)


def wand_1x1(m, kaputt):
    wand_flaeche(m, kaputt, 1.0, 1.0)


def balken(m, kaputt, raster):
    """Balken 20 x 20 cm über raster Meter (Rasterpunkt 0 bis raster), je Ende UEBERSTAND länger.
    Mitte auf der Rasterlinie (y und z um 0)."""
    laenge = raster + 2 * UEBERSTAND
    if not kaputt:
        bm = quader(laenge, BALKEN, BALKEN, max(1, int(laenge / 0.5)), 1, 1)
        m.teil(bm, "holz", M((raster / 2, 0, 0)))
        return
    # Kaputt: verkohlt, das hintere Ende abgebrochen (nur die Bruchstelle ist uneben)
    rest = laenge * 0.62
    bm = quader(rest, BALKEN, BALKEN, max(1, int(rest / 0.3)), 4, 4)
    bruchkante(bm, m.rnd, 1, 0.16)
    m.teil(bm, "holz_verkohlt", M((rest / 2 - UEBERSTAND, 0, 0)))


def balken_2m(m, kaputt):
    balken(m, kaputt, 2.0)


def balken_1m(m, kaputt):
    balken(m, kaputt, 1.0)


def strebe_2m(m, kaputt):
    """Schräge Strebe: Mittellinie vom Rasterpunkt (0|0) zum Rasterpunkt (2|2), Enden waagerecht abgeschnitten
    (sie stecken in den waagerechten Balken)."""
    d = BALKEN / 2 * math.sqrt(2)            # halbe Breite, waagerecht gemessen
    h = 2.0 if not kaputt else 1.1           # kaputt: bei 55 % der Höhe abgebrochen
    pts = [(-d, 0.0), (d, 0.0), (h + d, h), (h - d, h)]
    bm = bmesh.new()
    a = [bm.verts.new((x, -BALKEN / 2, z)) for x, z in pts]
    b = [bm.verts.new((x, BALKEN / 2, z)) for x, z in pts]
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(4):
        bm.faces.new((a[i], b[i], b[(i + 1) % 4], a[(i + 1) % 4]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if kaputt:
        oben = [e for e in bm.edges if all(v.co.z > h - 1e-4 for v in e.verts)]
        bmesh.ops.subdivide_edges(bm, edges=oben, cuts=3, use_grid_fill=True)
        for v in bm.verts:
            if v.co.z > h - 1e-4:
                v.co.z += m.rnd.uniform(-0.1, 0.06)
    # UVs entlang der Schräge: Teil zum Rechnen so drehen, dass die Strebe entlang x liegt
    rot = Matrix.Rotation(math.radians(45), 4, "Y")
    bm.transform(rot)
    m.teil(bm, "holz" if not kaputt else "holz_verkohlt", rot.inverted())


# ======================================================================== Wände mit Öffnung (12.11.)
# Öffnungen als (x0, x1, z0, z1) in der Wand. Die Wand selbst ist eine Fläche mit Löchern, auf 10 cm aufgedickt:
# alle Außenkanten bleiben eben und im Raster, nur in der Öffnung sitzt eine Zarge bzw. ein Fensterrahmen.

TUER = (0.55, 1.45, 0.0, 1.9)          # Öffnung in wand_tuer: 0,9 x 1,9 m, darüber liegt der Balken (Unterkante 1,9 m)
TUER_ZARGE = 0.05                      # Zarge 5 cm: lichte Weite 0,8 x 1,85 m, Türblatt genau so groß
FENSTER = {"wand_fenster": (2.0, 2.0, (0.6, 1.4, 0.8, 1.6)),
           "wand_fenster_2x1": (2.0, 1.0, (0.5, 1.5, 0.2, 0.8)),
           "wand_fenster_1x1": (1.0, 1.0, (0.2, 0.8, 0.2, 0.8))}


def wand_loecher(m, breite, hoehe, oeffnungen, kaputt):
    """Wand breite x hoehe mit rechteckigen Öffnungen. Heil: Gitter genau an den Öffnungskanten (wenige Flächen).
    Kaputt: 5-cm-Gitter mit ausgebrochenem Loch und abgebröckelter Oberkante wie wand_flaeche()."""
    if kaputt:
        z = 0.05
        nx, nz = round(breite / z), round(hoehe / z)
        sx, sz = breite / 2, hoehe / 2
        def fehlt(i, j):
            x = (j + 0.5) * z; h = (i + 0.5) * z
            if any(o[0] <= x <= o[1] and o[2] <= h <= o[3] for o in oeffnungen):
                return True
            xr = (x - breite / 2) / sx; hr = h / sz
            kante = 1.8 - 0.4 * max(0.0, xr + 0.1) + 0.12 * noise.noise(Vector((xr * 4, 0.3, 1.1)))
            r = 0.3 + 0.08 * noise.noise(Vector((xr * 5, hr * 5, 2.7)))
            return hr > kante or ((xr - 0.6) ** 2 + ((hr - 0.55) * 1.2) ** 2) ** 0.5 < r
        xs = [j * z for j in range(nx + 1)]; zs = [i * z for i in range(nz + 1)]
    else:
        xs = sorted({0.0, breite, *[o[0] for o in oeffnungen], *[o[1] for o in oeffnungen]})
        zs = sorted({0.0, hoehe, *[o[2] for o in oeffnungen], *[o[3] for o in oeffnungen]})
        def fehlt(i, j):
            x = (xs[j] + xs[j + 1]) / 2; h = (zs[i] + zs[i + 1]) / 2
            return any(o[0] <= x <= o[1] and o[2] <= h <= o[3] for o in oeffnungen)
    gitter = [[(x, -WAND_D / 2, h) for x in xs] for h in zs]
    bm = flaeche(gitter, 0.0, fehlt)
    if kaputt:
        for v in bm.verts:
            rand = any(len(e.link_faces) < 2 for e in v.link_edges)
            aussen = v.co.z < 1e-4 or abs(v.co.x) < 1e-4 or abs(v.co.x - breite) < 1e-4
            in_oeffnung = any(o[0] - 1e-4 <= v.co.x <= o[1] + 1e-4 and o[2] - 1e-4 <= v.co.z <= o[3] + 1e-4
                              for o in oeffnungen)
            if rand and not aussen and not in_oeffnung:
                v.co.x += m.rnd.uniform(-0.02, 0.02); v.co.z += m.rnd.uniform(-0.025, 0.02)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=-WAND_D)
    mitte_y(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # Außenflächen zeigen nach außen (sonst sieht man die Rückseite)
    bm.normal_update()
    m.teil(bm, "putz", None, versatz=(0, 0))


EINBETTEN = 0.01   # Rahmen stecken 1 cm in der Wand: keine Fläche liegt genau auf der Laibung (sonst flackert es)


def rahmen(m, o, b, tiefe, mat="holz", unten=True, bruch=()):
    """Rahmen aus Kanthölzern innen an der Öffnung o = (x0, x1, z0, z1): Breite b in der Wandebene, Tiefe quer.
    Der Rahmen ist rundum EINBETTEN größer als die Öffnung, damit seine Außenflächen in der Wand verschwinden.
    bruch: Seiten ('l', 'r', 'o', 'u'), die abgebrochen sind."""
    e = EINBETTEN
    x0, x1, z0, z1 = o[0] - e, o[1] + e, o[2] - (e if unten else 0.0), o[3] + e
    seiten = {"l": ((x0 + b / 2, 0, z0), (x0 + b / 2, 0, z1), (1, 0, 0)),
              "r": ((x1 - b / 2, 0, z0), (x1 - b / 2, 0, z1), (1, 0, 0)),
              "o": ((x0 + b, 0, z1 - b / 2), (x1 - b, 0, z1 - b / 2), (0, 0, 1))}
    if unten:
        seiten["u"] = ((x0 + b, 0, z0 + b / 2), (x1 - b, 0, z0 + b / 2), (0, 0, 1))
    for k, (a, e, oben) in seiten.items():
        # Kantholz: Breite quer zur Wand (tiefe), Dicke in Richtung "oben" (= b, in der Wandebene)
        m.kantholz(a, e, tiefe, b, mat, oben=oben, fase=0.004, biegen=0.0, bruch=1 if k in bruch else 0)


def wand_tuer(m, kaputt):
    """2 x 2-Wand mit Türöffnung 0,9 x 1,9 m in der Mitte (x 0,55..1,45) und Zarge. Das Türblatt ist ein
    eigenes Modell (tuer) mit demselben Ursprung."""
    wand_loecher(m, 2.0, 2.0, [TUER], kaputt)
    rahmen(m, TUER, TUER_ZARGE, WAND_D + 0.04, "holz" if not kaputt else "holz_alt", unten=False,
           bruch=("r",) if kaputt else ())
    # Schwelle aus Stein, bündig mit dem Balken darunter (Oberkante 0,1 m wie der Boden)
    x0, x1 = TUER[0], TUER[1]
    m.teil(klotz(m.rnd, x1 - x0 + 2 * EINBETTEN, WAND_D + 0.1, 0.1, 0.01, 0.003, 0.6 if kaputt else 0.0), "stein",
           M(((x0 + x1) / 2, 0, 0.05)))


def tuer(m, kaputt, holz="holz"):
    """Brettertür für wand_tuer: Ursprung wie die Wand (Rasterpunkt), Angel bei x = 0,6, Blatt 0,8 x 1,85 m in der
    Wandebene (y -0,02..0,02). Zum Öffnen um die senkrechte Achse durch (0,6 | 0) drehen."""
    x0 = TUER[0] + TUER_ZARGE; b = TUER[1] - TUER[0] - 2 * TUER_ZARGE; h = TUER[3] - TUER_ZARGE
    z0 = 0.1
    h = h - z0
    if kaputt:   # obere Angel ausgerissen: hängt schräg nach außen
        m.G = M((x0, 0, z0)) @ M(rot=(0, 0, -40)) @ M(rot=(0, -6, 0))
    else:
        m.G = M((x0, 0, z0))
    n = 5
    for i in range(n):
        x = b / n * (i + 0.5)
        if kaputt and i in (3, 4):
            laenge = (0.95, 1.25)[i - 3]
            m.brett(laenge, b / n - 0.004, 0.035, M((x, 0, laenge / 2), (0, -90, 0)) @ M(rot=(90, 0, 0)), holz,
                    bruch=-1, bruch_tiefe=0.15)
            continue
        m.brett(h, b / n - 0.004, 0.035, M((x, 0, h / 2), (0, -90, 0)) @ M(rot=(90, 0, 0)), holz)
    for z in (0.25, h - 0.25):
        m.kantholz((0.03, 0.03, z), (b - 0.03, 0.03, z), 0.12, 0.025, holz, oben=(0, 1, 0))
        m.teil(quader(b * 0.7, 0.006, 0.045, fase=0.002), "eisen", M((b * 0.35, -0.021, z)))
    m.kantholz((0.08, 0.03, 0.3), (b - 0.08, 0.03, h - 0.32), 0.1, 0.025, holz, oben=(0, 1, 0))
    m.seil([(b - 0.1, -0.02, 0.95), (b - 0.1, -0.06, 0.97), (b - 0.1, -0.06, 1.09), (b - 0.1, -0.02, 1.11)],
           0.008, 5, "eisen")
    m.G = None


def fenster_wand(m, kaputt, name):
    breite, hoehe, o = FENSTER[name]
    wand_loecher(m, breite, hoehe, [o], kaputt)
    x0, x1, z0, z1 = o
    rb = 0.05
    rahmen(m, o, rb, WAND_D + 0.03, "holz", bruch=("o",) if kaputt else ())
    # Fensterkreuz und Glas (in der Wandmitte)
    xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
    if not kaputt:
        m.kantholz((xm, 0, z0 + rb), (xm, 0, z1 - rb), 0.04, 0.035, "holz", oben=(1, 0, 0), biegen=0.0)
        m.kantholz((x0 + rb, 0, zm), (x1 - rb, 0, zm), 0.04, 0.035, "holz", oben=(0, 0, 1), biegen=0.0)
        m.teil(quader(x1 - x0 - 2 * rb, 0.006, z1 - z0 - 2 * rb), "glas", M((xm, 0, zm)))
    else:
        m.kantholz((xm, 0, z0 + rb), (xm, 0, zm + 0.08), 0.04, 0.035, "holz", oben=(1, 0, 0), bruch=1, biegen=0.0)
        # Glasscherben im Rahmen unten links
        bm = bmesh.new()
        pts = [(x0 + rb, z0 + rb), (xm - 0.02, z0 + rb), (xm - 0.05, z0 + rb + 0.12), (x0 + rb + 0.12, zm - 0.05),
               (x0 + rb, zm - 0.02)]
        bm.faces.new([bm.verts.new((x, 0, z)) for x, z in pts])
        m.teil(bm, "glas", None)
    # Fensterbank außen (vorne = -y)
    m.brett(x1 - x0 + 0.12, 0.09, 0.03, M((xm, -WAND_D / 2 - 0.035, z0 - 0.015)), "holz_alt", biegen=0.0)


def wand_fenster(m, kaputt):
    fenster_wand(m, kaputt, "wand_fenster")


def wand_fenster_2x1(m, kaputt):
    fenster_wand(m, kaputt, "wand_fenster_2x1")


def wand_fenster_1x1(m, kaputt):
    fenster_wand(m, kaputt, "wand_fenster_1x1")


def dreieck(m, kaputt, b):
    """Giebel-Dreieck b x b: Ecken (0|0), (b|0), (b|b), die Schräge liegt auf der Diagonale wie strebe_2m.
    Für die andere Giebelseite um 180° drehen (y) und um b verschieben."""
    umriss = [(0.0, 0.0), (b, 0.0), (b, b)]
    if kaputt:   # obere Spitze abgebrochen: zackige Bruchlinie von der Schräge bis zur senkrechten Kante
        za, ze = b * 0.45, b * 0.62
        punkte = []
        n = 7
        for k in range(n + 1):
            t = k / n
            x = za + (b - za) * t
            z = za + (ze - za) * t + (m.rnd.uniform(-0.06, 0.06) if 0 < k < n else 0.0)
            punkte.append((x, min(z, x)))
        umriss = [(0.0, 0.0), (b, 0.0), (b, ze)] + list(reversed(punkte))
    bm = bmesh.new()
    vorne = [bm.verts.new((x, -WAND_D / 2, z)) for x, z in umriss]
    hinten = [bm.verts.new((x, WAND_D / 2, z)) for x, z in umriss]
    bm.faces.new(vorne); bm.faces.new(list(reversed(hinten)))
    for i in range(len(umriss)):
        bm.faces.new((vorne[i], hinten[i], hinten[(i + 1) % len(umriss)], vorne[(i + 1) % len(umriss)]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m.teil(bm, "putz", None, versatz=(0, 0))


def wand_dreieck(m, kaputt):
    dreieck(m, kaputt, 2.0)


def wand_dreieck_1x1(m, kaputt):
    dreieck(m, kaputt, 1.0)


# ======================================================================== Boden, Dach, Treppe
# Tiefe läuft in Blender entlang +y (in Godot nach -z, also "nach hinten" von der Wandvorderseite weg).

BODEN_OBEN = BALKEN / 2       # Dielen liegen bündig auf der Oberkante der Balken (0,1 m über der Rasterlinie)
DIELE = 0.04


def boden_flaeche(m, kaputt, b):
    """Dielenboden b x b (x 0..b, y 0..b), Oberkante 0,1 m über dem Rasterpunkt (auf den Balken)."""
    z = BODEN_OBEN - DIELE / 2
    if not kaputt:
        m.teil(quader(b, b, DIELE, int(b * 2), int(b * 2), 1), "dielen", M((b / 2, b / 2, z)), versatz=(0, 0))
        return
    n = round(b / 0.2)
    for i in range(n):
        x = 0.1 + i * 0.2
        mitte = n // 2
        if abs(i - mitte + 0.5) < 1.6:
            for s in (0, 1):
                l = m.rnd.uniform(0.3, 0.42) * b
                y = l / 2 if s == 0 else b - l / 2
                m.brett(l, 0.196, DIELE, M((x, y, z), (0, 0, 90)), "dielen", bruch=1 if s == 0 else -1,
                        bruch_tiefe=0.12, biegen=0.0)
        else:
            m.brett(b, 0.196, DIELE, M((x, b / 2, z), (0, 0, 90)), "dielen", nx=int(b * 3), biegen=0.0)
    m.brett(0.6 * b, 0.196, DIELE, M((b * 0.45, b * 0.5, z - 0.25), (18, 0, 70)), "holz_verkohlt", bruch=1)


def boden_2x2(m, kaputt):
    boden_flaeche(m, kaputt, 2.0)


def boden_1x1(m, kaputt):
    boden_flaeche(m, kaputt, 1.0)


DACH_ABSTAND = BALKEN / 2 * math.sqrt(2)   # Unterseite der Dachhaut liegt senkrecht gemessen auf den Balkenkanten
DACH_DICKE = 0.08                          # Schalung + Schindeln


def dach_platte(m, kaputt, b, lauf, y_von=None, x_von=0.0):
    """Dachfläche 45°: Traufe am Rasterpunkt (y 0 | z 0), steigt bis (y lauf | z lauf), b breit entlang x.
    Die Haut liegt auf den Balken (Unterseite 0,1 m senkrecht über der Diagonale), Enden senkrecht im Raster
    abgeschnitten: zwei Seiten treffen sich am First genau, die Traufe endet über der Wandmitte."""
    y0 = 0.0 if y_von is None else y_von
    s2 = math.sqrt(2)
    unten = DACH_ABSTAND * s2                 # senkrechter Versatz der Unterseite über der Diagonale
    oben = (DACH_ABSTAND + DACH_DICKE) * s2
    nx, ny = max(2, int(b * 4)), max(2, int((lauf - y0) * 4))
    def gitter(dz):
        return [[(x_von + b * j / nx, y0 + (lauf - y0) * i / ny, y0 + (lauf - y0) * i / ny + dz) for j in range(nx + 1)]
                for i in range(ny + 1)]
    loch = None
    if kaputt and b >= 1.0 and lauf - y0 >= 1.0:
        loch = lambda i, j: ((i - ny * 0.45) / ny * 4) ** 2 + ((j - nx * 0.4) / nx * 3.2) ** 2 < 1.2 + \
            0.6 * noise.noise(Vector((i * 0.6, j * 0.6, 0.3)))
    # Ober- und Unterseite einzeln, Ränder als senkrechte bzw. seitliche Stirnflächen
    bm = bmesh.new()
    go = [[bm.verts.new(p) for p in zeile] for zeile in gitter(oben)]
    gu = [[bm.verts.new(p) for p in zeile] for zeile in gitter(unten)]
    offen = lambda i, j: loch is not None and loch(i, j)
    for i in range(ny):
        for j in range(nx):
            if offen(i, j):
                continue
            bm.faces.new((go[i][j], go[i][j + 1], go[i + 1][j + 1], go[i + 1][j]))
            bm.faces.new((gu[i][j], gu[i + 1][j], gu[i + 1][j + 1], gu[i][j + 1]))
    # Stirnflächen: überall, wo eine Zelle an den Rand oder an ein Loch grenzt
    def zelle(i, j):
        return 0 <= i < ny and 0 <= j < nx and not offen(i, j)
    for i in range(ny):
        for j in range(nx):
            if not zelle(i, j):
                continue
            if not zelle(i - 1, j):
                bm.faces.new((go[i][j], gu[i][j], gu[i][j + 1], go[i][j + 1]))
            if not zelle(i + 1, j):
                bm.faces.new((go[i + 1][j + 1], gu[i + 1][j + 1], gu[i + 1][j], go[i + 1][j]))
            if not zelle(i, j - 1):
                bm.faces.new((go[i + 1][j], gu[i + 1][j], gu[i][j], go[i][j]))
            if not zelle(i, j + 1):
                bm.faces.new((go[i][j + 1], gu[i][j + 1], gu[i + 1][j + 1], go[i + 1][j + 1]))
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # UV in Dachrichtung: u entlang x, v die Schräge hinauf
    ku, kv = basis.kachel("schindeln")
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (p.x / ku, p.y)   # eine Kachel je Meter Lauf: Stöße zwischen Dachteilen im Raster passen genau
    m.teil(bm, "schindeln", None, uv=None)
    if loch:   # verkohlte Sparren im Loch
        for x in (b * 0.3, b * 0.65):
            a = Vector((x, y0 + 0.05, y0 + 0.05 + unten - 0.06)); e = Vector((x, lauf - 0.05, lauf - 0.05 + unten - 0.06))
            m.kantholz(a, a + (e - a) * m.rnd.uniform(0.55, 0.8), 0.08, 0.1, "holz_verkohlt", oben=(0, -1, 1), bruch=1)


def dach_2x2(m, kaputt):
    dach_platte(m, kaputt, 2.0, 2.0)


def dach_2x1(m, kaputt):
    dach_platte(m, kaputt, 2.0, 1.0)


def dach_1x2(m, kaputt):
    dach_platte(m, kaputt, 1.0, 2.0)


def dach_1x1(m, kaputt):
    dach_platte(m, kaputt, 1.0, 1.0)


def dach_traufe(m, kaputt):
    """Dachüberstand 2 m breit: setzt die Dachfläche an der Traufe 0,5 m nach außen (y -0,5..0) fort.
    Gleicher Ursprung wie dach_*: am Traufpunkt einfach dazusetzen."""
    dach_platte(m, False, 2.0 if not kaputt else 1.2, 0.0, y_von=-0.5)



# ---------------------------------------------------------------- Eckdächer: Kehle (Innenecke) und Grat (Außenecke)
# Beide liegen auf einer Rasterzelle b x b. Die Dachhaut folgt einer Höhenfunktion: Kehle z = max(x, y), Grat
# z = min(x, y). Ursprung ist die Traufecke (z 0); bei (b | b) liegt der Punkt, an dem sich die Firste treffen.
# Spiegeln ist nicht nötig: max und min sind in x und y gleich, eine Drehung um 90° reicht.

def dach_form(m, kaputt, f, x0, x1, y0, y1):
    """Dachhaut über einer Höhenfunktion f(x, y), gleiche Dicke und gleicher Abstand wie dach_platte (senkrecht
    gemessen), damit sie an normale Dachteile genau anschließt. Jede Zelle ist entlang der Diagonale geteilt,
    die Kehl-/Gratlinie liegt damit genau auf Kanten."""
    s2 = math.sqrt(2)
    unten = DACH_ABSTAND * s2
    oben = (DACH_ABSTAND + DACH_DICKE) * s2
    nx, ny = max(2, round((x1 - x0) * 4)), max(2, round((y1 - y0) * 4))
    loch = None
    if kaputt and x1 - x0 >= 1.0 and y1 - y0 >= 1.0:
        loch = lambda i, j: ((i / ny - 0.5) * 4) ** 2 + ((j / nx - 0.42) * 3.4) ** 2 < 1.1 + \
            0.6 * noise.noise(Vector((i * 0.6, j * 0.6, 0.7)))
    bm = bmesh.new()
    go, gu = [], []
    for i in range(ny + 1):
        zo, zu = [], []
        for j in range(nx + 1):
            x = x0 + (x1 - x0) * j / nx; y = y0 + (y1 - y0) * i / ny; z = f(x, y)
            zo.append(bm.verts.new((x, y, z + oben))); zu.append(bm.verts.new((x, y, z + unten)))
        go.append(zo); gu.append(zu)
    unter = {go[i][j]: gu[i][j] for i in range(ny + 1) for j in range(nx + 1)}
    for i in range(ny):
        for j in range(nx):
            if loch and loch(i, j):
                continue
            for g, umgekehrt in ((go, False), (gu, True)):
                a, b_, c, d = g[i][j], g[i][j + 1], g[i + 1][j + 1], g[i + 1][j]
                for tri in ((a, b_, c), (a, c, d)):
                    bm.faces.new(tri[::-1] if umgekehrt else tri)
    for e in [e for e in bm.edges if e.verts[0] in unter and e.is_boundary]:
        v1, v2 = e.verts
        bm.faces.new((v1, v2, unter[v2], unter[v1]))
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # Schindeln: v immer die Schräge hinauf, u entlang der Traufe (am Raster verankert wie bei dach_platte)
    ku, kv = basis.kachel("schindeln")
    uv = bm.loops.layers.uv.verify()
    for fl in bm.faces:
        entlang_x = abs(fl.normal.y) >= abs(fl.normal.x)
        for l in fl.loops:
            p = l.vert.co
            l[uv].uv = (p.x / ku, p.y) if entlang_x else (-p.y / ku, p.x)
    m.teil(bm, "schindeln", None, uv=None)


def gratbrett(m, kaputt, t0, t1, b=None):
    """Zwei Bretter über der Gratlinie (x = y = z) von t0 bis t1, wie die Firstabdeckung: jedes liegt auf einer
    Dachseite und reicht 1 cm über den Grat. Mit b werden sie oben an den senkrechten Ebenen x = b und y = b
    abgeschnitten (Gehrung): dort stoßen das Brett des Nachbargrats bzw. die Firstbretter genau an, nichts
    überlappt (sonst flackern Bretter, die in derselben Dachebene liegen)."""
    oben = (DACH_ABSTAND + DACH_DICKE) * math.sqrt(2)
    d = Vector((1, 1, 1)).normalized()
    t1_lang = t1 + (0.25 if b is not None else 0.0)        # über die Spitze hinaus, die Schnitte kürzen es
    laenge = (t1_lang - t0) * math.sqrt(3)
    mitte = Vector(((t0 + t1_lang) / 2,) * 3) + Vector((0, 0, oben))
    for k, (n, seite) in enumerate(((Vector((-1, 0, 1)), Vector((-1, 1, 0))), (Vector((0, -1, 1)), Vector((1, -1, 0))))):
        n = n.normalized()
        w = n.cross(d)
        quer = w if w.dot(seite) > 0 else -w
        c = mitte + n * (0.015 + 0.003) + quer * (0.12 - 0.01)
        rot = Matrix.Translation(c) @ Matrix((d, w, n)).transposed().to_4x4()
        if kaputt and k == 1:
            m.brett((t1 - t0) * math.sqrt(3) * 0.5, 0.24, 0.03,
                    Matrix.Translation(Vector(((t0 + t1) / 2,) * 3) - mitte) @ rot @ M((-laenge * 0.2, 0, 0)),
                    "holz_verkohlt", bruch=1, biegen=0.0)
            continue
        bm = quader(laenge, 0.24, 0.03, max(1, int(laenge / 0.3)))
        if b is not None:
            inv = rot.inverted()
            for normale in (Vector((1, 0, 0)), Vector((0, 1, 0))):
                geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
                erg = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=inv @ Vector((b, b, b)),
                                             plane_no=(inv.to_3x3() @ normale).normalized(), clear_outer=True)
                rand = [e for e in bm.edges if e.is_boundary]
                if rand:
                    bmesh.ops.holes_fill(bm, edges=rand, sides=0)
        m.teil(bm, "holz_alt", rot)


def kehle(m, kaputt, b):
    """Kehle (Innenecke eines L-Hauses): Ursprung an der inneren Traufecke, die Fläche steigt nach +x und +y zu den
    beiden Firsten. Die Kehllinie läuft von (0|0|0) nach (b|b|b)."""
    dach_form(m, kaputt, lambda x, y: max(x, y), 0.0, b, 0.0, b)


def dach_kehle_2x2(m, kaputt):
    kehle(m, kaputt, 2.0)


def dach_kehle_1x1(m, kaputt):
    kehle(m, kaputt, 1.0)


def grat(m, kaputt, b):
    """Grat (Außenecke, Walmdach): Ursprung an der äußeren Traufecke, die Fläche steigt nach +x und +y."""
    dach_form(m, kaputt, lambda x, y: min(x, y), 0.0, b, 0.0, b)
    gratbrett(m, kaputt, 0.0, b, b)


def dach_grat_2x2(m, kaputt):
    grat(m, kaputt, 2.0)


def dach_grat_1x1(m, kaputt):
    grat(m, kaputt, 1.0)


def dach_grat_traufe(m, kaputt):
    """Überstand an der Gratecke (0,5 x 0,5 m vor der Traufecke) mit Gratbrett. Gleicher Ursprung wie dach_grat_*,
    die beiden dach_traufe-Teile daneben schließen genau an. An der Kehle braucht es nichts: die zwei
    Traufüberstände kreuzen sich dort von selbst zur Kehle."""
    dach_form(m, False, lambda x, y: min(x, y), -0.5, 0.0, -0.5, 0.0)
    gratbrett(m, kaputt, -0.5, 0.0)



BRETT_D = 0.025        # Dicke von Windbrett und Giebelzier
BRETT_H = 0.24         # Höhe (quer zur Schräge)


def profil_brett(m, punkte, xa, xb, mat):
    """Brett aus einem Umriss in der y-z-Ebene (Punkte (y, z), gegen den Uhrzeigersinn egal), zwischen x = xa und xb.
    UVs hängen an der Lage (u = (y + z) / 2 entlang der Schräge), damit die Maserung über Stöße durchläuft."""
    bm = bmesh.new()
    va = [bm.verts.new((xa, y, z)) for y, z in punkte]
    vb = [bm.verts.new((xb, y, z)) for y, z in punkte]
    bm.faces.new(va); bm.faces.new(list(reversed(vb)))
    n = len(punkte)
    for i in range(n):
        bm.faces.new((va[i], vb[i], vb[(i + 1) % n], va[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    ku, kv = basis.kachel(mat)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            u = (p.y + p.z) / 2.0 if abs(f.normal.x) > 0.5 else (p.y + p.z) / 2.0
            v = ((p.z - p.y) / math.sqrt(2) + (p.x if abs(f.normal.x) < 0.5 else 0.0)) / kv
            l[uv].uv = (u, v)
    m.teil(bm, mat, None, uv=None)


def brett_linien():
    """Unter- und Oberkante des Windbretts als senkrechter Abstand über der Diagonale z = y."""
    c = (DACH_ABSTAND + DACH_DICKE / 2) * math.sqrt(2) - 0.07
    h = BRETT_H / 2 * math.sqrt(2)
    return c - h, c + h


def windbrett(m, x, y_von, y_bis, kaputt):
    """Windbrett an der Außenkante des Ortgangs, folgt der Schräge, beide Enden SENKRECHT im Raster abgeschnitten:
    am First stoßen die Bretter beider Dachseiten genau aneinander statt sich zu überlappen (kein Flackern),
    an der Traufe passt die Ecke bündig an. Sitzt außen vor der Dachkante (x ist die Mitte des Bretts)."""
    d1, d2 = brett_linien()
    mat = "holz_alt" if not kaputt else "holz_verkohlt"
    if kaputt:
        y_bis = y_von + (y_bis - y_von) * 0.55
    punkte = [(y_von, y_von + d1), (y_bis, y_bis + d1), (y_bis, y_bis + d2), (y_von, y_von + d2)]
    if kaputt:   # zackige Bruchkante oben
        punkte[2:2] = [(y_bis - 0.05, y_bis + (d1 + d2) / 2 + 0.03)]
    profil_brett(m, punkte, x - BRETT_D / 2, x + BRETT_D / 2, mat)


ORTGANG = 0.5          # seitlicher Dachüberstand


def ortgang(m, kaputt, lauf, seite):
    """Seitlicher Dachüberstand (Ortgang) 0,5 m: setzt die Dachfläche über die Giebelwand hinaus fort.
    seite -1 (links): x -0,5..0, seite +1 (rechts): x 0..0,5. Ursprung wie das Dach (Traufpunkt am Giebel)."""
    x0 = -ORTGANG if seite < 0 else 0.0
    bis = lauf if not kaputt else lauf * 0.6
    dach_platte(m, False, ORTGANG, bis, x_von=x0)
    windbrett(m, seite * (ORTGANG + 0.0125), 0.0, lauf, kaputt)


def dach_ortgang_l(m, kaputt):
    ortgang(m, kaputt, 2.0, -1)


def dach_ortgang_r(m, kaputt):
    ortgang(m, kaputt, 2.0, 1)


def dach_ortgang_1m_l(m, kaputt):
    ortgang(m, kaputt, 1.0, -1)


def dach_ortgang_1m_r(m, kaputt):
    ortgang(m, kaputt, 1.0, 1)


def dach_ecke(m, kaputt, seite):
    """Ecke zwischen Traufe und Ortgang (0,5 x 0,5 m, außen vor dem Traufpunkt)."""
    x0 = -ORTGANG if seite < 0 else 0.0
    dach_platte(m, False, ORTGANG, 0.0, y_von=-0.5, x_von=x0)   # auch kaputt: sonst schwebt das Brett allein
    windbrett(m, seite * (ORTGANG + 0.0125), -0.5, 0.0, kaputt)


def dach_ecke_l(m, kaputt):
    dach_ecke(m, kaputt, -1)


def dach_ecke_r(m, kaputt):
    dach_ecke(m, kaputt, 1)


def zier_umriss(laenge_unten=0.4, kopf=True):
    """Umriss eines Zierbretts der vorderen Dachseite (steigt nach +y) am First (y 0 = First): beginnt
    laenge_unten vor dem First, läuft über den First hinaus und endet in einem runden Kopf mit Kerbe."""
    d1, d2 = brett_linien()
    c = (d1 + d2) / 2
    y0 = -laenge_unten
    if not kopf:   # abgebrochen
        return [(y0, y0 + d1), (0.08, 0.08 + d1), (0.02, 0.1 + c), (0.05, 0.05 + d2), (y0, y0 + d2)]
    pkt = [(y0, y0 + d1), (0.28, 0.28 + d1)]
    # runder Kopf: Halbkreis um das Brettende, quer zur Schräge
    mitte = Vector((0.36, 0.36 + c))
    r = (d2 - d1) / 2 / math.sqrt(2) * 1.25          # etwas breiter als das Brett
    rich = Vector((1, 1)).normalized(); quer = Vector((-1, 1)).normalized()
    for k in range(9):
        w = math.radians(-100 + 200 * k / 8)
        q = mitte + rich * (math.sin(w) * r * 1.2) + quer * (-math.cos(w) * r)
        pkt.append((q.x, q.y))
    # Kerbe in der Oberkante
    pkt += [(0.2, 0.2 + d2), (0.14, 0.14 + d2 - 0.06), (0.08, 0.08 + d2), (y0, y0 + d2)]
    return pkt


def giebelzier(m, kaputt, seite):
    """Giebelzier am First über dem Ortgang: zwei gekreuzte Zierbretter, die über den First hinausragen, und eine
    Firstkappe über dem 0,5-m-Überstand. Ursprung am First-Rasterpunkt wie dach_first; seite -1 links (x < 0),
    +1 rechts. Die Bretter liegen in zwei Lagen außen vor den Windbrettern (keine gemeinsame Fläche)."""
    mat = "holz_alt" if not kaputt else "holz_verkohlt"
    x1 = seite * (ORTGANG + BRETT_D * 1.5)     # Lage 1: Zierbrett der vorderen Dachseite
    x2 = seite * (ORTGANG + BRETT_D * 2.5)     # Lage 2: hintere Dachseite (gespiegelt)
    profil_brett(m, zier_umriss(), x1 - BRETT_D / 2, x1 + BRETT_D / 2, mat)
    hinten = [(-y, z) for y, z in zier_umriss(kopf=not kaputt)]
    profil_brett(m, hinten, x2 - BRETT_D / 2, x2 + BRETT_D / 2, mat)
    # Firstkappe über dem Überstand (wie dach_first, 0,5 m)
    spitze = (DACH_ABSTAND + DACH_DICKE) * math.sqrt(2)
    xm = seite * ORTGANG / 2
    for s_ in (-1, 1):
        rot = M(rot=(-s_ * 45, 0, 0))
        m.brett(ORTGANG, 0.24, 0.03, M((xm, 0, spitze + 0.01)) @ rot @ M((0, s_ * 0.11, 0)), "holz_alt", biegen=0.0)


def dach_zier_l(m, kaputt):
    giebelzier(m, kaputt, -1)


def dach_zier_r(m, kaputt):
    giebelzier(m, kaputt, 1)


def dach_first(m, kaputt):
    """Firstabdeckung 2 m: zwei Bretter über dem First. Ursprung am First-Rasterpunkt (y 0 | z 0 = Spitze der
    Diagonalen); die Dachflächen beider Seiten treffen sich darüber."""
    spitze = (DACH_ABSTAND + DACH_DICKE) * math.sqrt(2)
    for s in (-1, 1):
        rot = M(rot=(-s * 45, 0, 0))
        if kaputt and s > 0:
            m.brett(1.1, 0.24, 0.03, M((0.55, 0, spitze + 0.01)) @ rot @ M((0, s * 0.11, 0)), "holz_verkohlt", bruch=1)
            continue
        m.brett(2.0, 0.24, 0.03, M((1.0, 0, spitze + 0.01)) @ rot @ M((0, s * 0.11, 0)), "holz_alt")


STUFEN = 5                    # Treppe: 1 m hoch auf 2 m Lauf, Stufen 20 cm hoch, 40 cm tief


def treppe_holz(m, kaputt):
    """Holztreppe 1 m breit (x 0..1), läuft von y 0 nach y 2 und steigt um 1 m: vom Boden (0,1) bis zum Boden
    des nächsten Meters (1,1). Stapelbar für höhere Stockwerke (eine Stufe = 20 cm)."""
    h = 0.2; t = 0.4
    for x in (0.03, 0.97):
        a = Vector((x, 0.0, BODEN_OBEN)); e = Vector((x, 2.0, 1.0 + BODEN_OBEN))
        m.kantholz(a + Vector((0, 0.05, -0.08)), e + Vector((0, 0, -0.12)), 0.06, 0.26, "holz", oben=(0, -1, 2),
                   bruch=1 if kaputt and x > 0.5 else 0)
    for i in range(STUFEN):
        y = (i + 0.5) * t; z = BODEN_OBEN + (i + 1) * h
        if kaputt and i in (1, 3):
            if i == 3:
                m.brett(0.4, t - 0.02, 0.04, M((0.25, y, z - 0.02)), "holz", bruch=1)
            continue
        m.brett(0.94, t - 0.004, 0.04, M((0.5, y, z - 0.02)), "holz" if not (kaputt and i == 4) else "holz_verkohlt",
                biegen=0.0)
        if not (kaputt and i == 2):
            m.brett(0.94, h - 0.04, 0.02, M((0.5, y - t / 2 + 0.012, z - h / 2 - 0.02), (90, 0, 0)), "holz", biegen=0.0)


def treppe_stein(m, kaputt):
    """Massive Steintreppe, gleiche Maße wie treppe_holz (1 m breit, 2 m Lauf, 1 m Steigung), Blöcke bis zum Boden."""
    h = 0.2; t = 0.4
    for i in range(STUFEN):
        z1 = BODEN_OBEN + (i + 1) * h; y0 = i * t
        if kaputt and i == 4:   # oberste Stufe fehlt (Schutt kommt später als eigene Module)
            continue
        hoch = z1 if i == 0 else h
        m.teil(klotz(m.rnd, 1.0, t if i < STUFEN - 1 else t, hoch, 0.012, 0.003, 0.5 if kaputt else 0.0), "stein",
               M((0.5, y0 + t / 2, z1 - hoch / 2)))
        if i > 0:   # Unterbau bis zum Boden
            m.teil(klotz(m.rnd, 1.0, t, z1 - h, 0.01, 0.002, 0.0), "stein", M((0.5, y0 + t / 2, (z1 - h) / 2)))



# ================================================================ Variante „Bretter“: alt, windig, für verlassene Gebäude
# Gleiche Maße und Ursprünge wie die Putzwände (mittig auf der Rasterlinie, y -0,05..0,05): austauschbar.
# Senkrechte Bretter mit Lücken außen (vorne = -y), innen zwei Querlatten.

BRETT_AUSSEN = (-0.045, -0.02)     # Dicke der Wandbretter (y)
LATTE_INNEN = (-0.02, 0.03)        # Querlatten dahinter


def prisma(m, umriss, y0, y1, mat, uv="boxz", versatz=None):
    """Senkrechtes Teil aus einem Umriss in der x-z-Ebene (Punkte gegen den Uhrzeigersinn), Dicke y0..y1."""
    bm = bmesh.new()
    vo = [bm.verts.new((x, y0, z)) for x, z in umriss]
    hi = [bm.verts.new((x, y1, z)) for x, z in umriss]
    bm.faces.new(vo); bm.faces.new(list(reversed(hi)))
    n = len(umriss)
    for i in range(n):
        bm.faces.new((vo[i], hi[i], hi[(i + 1) % n], vo[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m.teil(bm, mat, None, uv=uv, versatz=versatz)


def bretter_reihe(m, kaputt, xa, xb, unten, oben, schraeg=False):
    """Füllt xa..xb mit senkrechten Brettern von unten(x) bis oben(x) (Funktionen), mit Lücken."""
    x = xa
    while xb - x > 0.04:
        w = m.rnd.uniform(0.15, 0.25)
        if xb - x - w < 0.1:
            w = xb - x
        x0, x1 = x + 0.004, x + w - m.rnd.uniform(0.008, 0.028)
        x = x + w
        if x1 - x0 < 0.05:
            continue
        z0 = unten(x0) + m.rnd.uniform(0.0, 0.025)
        zl, zr = oben(x0), oben(x1)
        if not schraeg:
            zl = zr = min(zl, zr) - m.rnd.uniform(0.0, 0.03)
        mat = "holz_alt"
        if kaputt:
            r = m.rnd.random()
            if r < 0.22:
                continue                                    # Brett fehlt
            if r < 0.5:                                     # abgebrochen, oben zackig
                h = z0 + (min(zl, zr) - z0) * m.rnd.uniform(0.35, 0.8)
                prisma(m, [(x0, z0), (x1, z0), (x1, h + m.rnd.uniform(-0.06, 0.06)), ((x0 + x1) / 2, h + 0.05),
                           (x0, h)], *BRETT_AUSSEN, "holz_verkohlt" if m.rnd.random() < 0.4 else mat)
                continue
        if zl - z0 < 0.02 and zr - z0 < 0.02:
            continue
        pts = [(x0, z0), (x1, z0), (x1, zr), (x0, zl)] if zl > z0 + 0.005 else [(x0, z0), (x1, z0), (x1, zr)]
        prisma(m, pts, *BRETT_AUSSEN, mat)


def latten(m, kaputt, breite, hoehe, oeffnungen=(), dreieck=False):
    """Querlatten innen (8 x 5 cm), unterbrochen an Öffnungen; beim Giebel nur, wo das Dreieck hoch genug ist."""
    for z in ((0.3, hoehe - 0.35) if hoehe > 1.2 else (hoehe / 2,)):
        stuecke = [(0.03, breite - 0.03)]
        if dreieck:
            stuecke = [(z + 0.12, breite - 0.03)]
        for o in oeffnungen:
            if o[2] - 0.05 < z < o[3] + 0.05:
                stuecke = [s for a, b in stuecke for s in ((a, o[0] - 0.02), (o[1] + 0.02, b)) if s[1] - s[0] > 0.1]
        for a, b in stuecke:
            if kaputt and m.rnd.random() < 0.3:
                b = a + (b - a) * m.rnd.uniform(0.3, 0.6)
            prisma(m, [(a, z - 0.04), (b, z - 0.04), (b, z + 0.04), (a, z + 0.04)], *LATTE_INNEN, "holz_alt", uv="box")


def bretterwand(m, kaputt, breite, hoehe, oeffnungen=()):
    grenzen = [0.0]
    for o in oeffnungen:
        grenzen += [o[0], o[1]]
    grenzen.append(breite)
    for xa, xb in zip(grenzen[::2], grenzen[1::2]):           # volle Felder zwischen den Öffnungen
        bretter_reihe(m, kaputt, xa, xb, lambda x: 0.0, lambda x: hoehe)
    for o in oeffnungen:                                       # unter und über der Öffnung
        if o[2] > 0.05:
            bretter_reihe(m, kaputt, o[0], o[1], lambda x: 0.0, lambda x, z=o[2]: z)
        if hoehe - o[3] > 0.05:
            bretter_reihe(m, kaputt, o[0], o[1], lambda x, z=o[3]: z, lambda x: hoehe)
    latten(m, kaputt, breite, hoehe, oeffnungen)


def bretter_2x2(m, kaputt):
    bretterwand(m, kaputt, 2.0, 2.0)


def bretter_2x1(m, kaputt):
    bretterwand(m, kaputt, 2.0, 1.0)


def bretter_1x1(m, kaputt):
    bretterwand(m, kaputt, 1.0, 1.0)


def bretter_tuer(m, kaputt):
    """Bretterwand mit derselben Türöffnung wie wand_tuer: das Türblatt tuer passt hinein."""
    bretterwand(m, kaputt, 2.0, 2.0, [TUER])
    rahmen(m, TUER, TUER_ZARGE, WAND_D, "holz_alt" if not kaputt else "holz_verkohlt", unten=False,
           bruch=("r",) if kaputt else ())


def tuer_alt(m, kaputt):
    """Türblatt wie tuer, aus verwittertem Holz (passt zu bretter_tuer und steinwand_tuer)."""
    tuer(m, kaputt, "holz_alt")


def bretter_fenster(m, kaputt):
    """Bretterwand mit Fensterloch 0,8 x 0,8 (wie wand_fenster), grober Rahmen, ein offener Fensterladen außen."""
    o = FENSTER["wand_fenster"][2]
    bretterwand(m, kaputt, 2.0, 2.0, [o])
    rahmen(m, o, 0.05, WAND_D, "holz_alt", bruch=("o",) if kaputt else ())
    x0, x1, z0, z1 = o
    # Laden: 3 Bretter, an der linken Kante angeschlagen, nach außen aufgeklappt (hängt bei kaputt schief)
    hh = z1 - z0
    g = M((x0 - 0.03, -0.07, z0)) @ M(rot=(0, -6 if kaputt else 0, -105))
    for i in range(3):
        bx = 0.01 + i * 0.135
        lang = hh - (0.15 if kaputt and i == 2 else 0.0)
        m.brett(lang, 0.13, 0.025, g @ M((bx + 0.065, 0, lang / 2), (0, -90, 0)) @ M(rot=(90, 0, 0)), "holz_alt",
                biegen=0.004, bruch=1 if kaputt and i == 2 else 0)
    for zq in (0.15, hh - 0.15):
        m.brett(0.38, 0.08, 0.02, g @ M((0.2, 0.023, zq)) @ M(rot=(90, 0, 0)), "holz_alt", biegen=0.0)


def bretter_dreieck_b(m, kaputt, b):
    """Giebel aus Brettern: Dreieck (0|0), (b|0), (b|b) wie wand_dreieck, Bretter oben schräg abgeschnitten."""
    bretter_reihe(m, kaputt, 0.0, b, lambda x: 0.0, lambda x: x, schraeg=True)
    latten(m, kaputt, b, b, dreieck=True)


def bretter_dreieck(m, kaputt):
    bretter_dreieck_b(m, kaputt, 2.0)


def bretter_dreieck_1x1(m, kaputt):
    bretter_dreieck_b(m, kaputt, 1.0)


def bretterdach(m, kaputt, b, lauf):
    """Bretterdach 45° statt Schindeln: Bretter laufen die Schräge hinauf (mit Lücken), darunter Querlatten.
    Gleiche Lage wie dach_*: Oberkante wie die Schindeln, Unterkante auf den Balken."""
    s2 = math.sqrt(2)
    unten = DACH_ABSTAND * s2
    oben = (DACH_ABSTAND + DACH_DICKE) * s2
    brett = 0.025 * s2
    def schraeg(x0, x1, y0, y1, d0, d1, mat, uvlang):
        bm = bmesh.new()
        v = {}
        for i, x in enumerate((x0, x1)):
            for j, y in enumerate((y0, y1)):
                for k, d in enumerate((d0, d1)):
                    v[i, j, k] = bm.verts.new((x, y, y + d))
        for f in (((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), ((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1)),
                  ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)), ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),
                  ((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)), ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0))):
            bm.faces.new([v[k] for k in f])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ku, kv = basis.kachel(mat)
        uv = bm.loops.layers.uv.verify()
        o = m.rnd.random()
        for fl in bm.faces:
            for l in fl.loops:
                p = l.vert.co
                l[uv].uv = ((p.y if uvlang else p.x) / ku + o, (p.x if uvlang else p.y + p.z) / kv)
        m.teil(bm, mat, None, uv=None)
    # Latten quer (unter den Brettern)
    for y in ([0.15, lauf - 0.25] if lauf > 1.2 else [lauf / 2 - 0.05]):
        x1 = b if not (kaputt and m.rnd.random() < 0.5) else b * m.rnd.uniform(0.4, 0.7)
        schraeg(0.0, x1, y, y + 0.1, unten, oben - brett, "holz_alt", False)
    # Bretter
    x = 0.0
    while b - x > 0.04:
        w = m.rnd.uniform(0.17, 0.25)
        if b - x - w < 0.1:
            w = b - x
        x0, x1 = x + 0.003, x + w - m.rnd.uniform(0.006, 0.02)
        x += w
        y1 = lauf
        if kaputt:
            r = m.rnd.random()
            if r < 0.25:
                continue
            if r < 0.5:
                y1 = lauf * m.rnd.uniform(0.3, 0.7)
        schraeg(x0, x1, 0.0, y1, oben - brett, oben, "holz_alt" if not (kaputt and m.rnd.random() < 0.3)
                else "holz_verkohlt", True)


def dach_bretter_2x2(m, kaputt):
    bretterdach(m, kaputt, 2.0, 2.0)


def dach_bretter_2x1(m, kaputt):
    bretterdach(m, kaputt, 2.0, 1.0)


def dach_bretter_1x2(m, kaputt):
    bretterdach(m, kaputt, 1.0, 2.0)


def dach_bretter_1x1(m, kaputt):
    bretterdach(m, kaputt, 1.0, 1.0)


# ================================================================ Variante „Stein“: Keller, Fundamente, Sockel
# Bruchsteinmauer 0,30 m dick, mittig auf der Rasterlinie (y -0,15..0,15). Die Wand füllt NUR das Feld zwischen
# zwei Rasterpunkten (x 0,15..b-0,15); an jeden Rasterpunkt gehört ein Steinpfeiler (0,3 x 0,3, gleiche Steinlagen).
# So stoßen Wand und Pfeiler genau aneinander, nichts überlappt (kein Flackern), Ecken und Stöße sind geschlossen –
# wie die Ständer beim Fachwerk. Lagenhöhe 0,25 m, damit die Lagen von Wand und Pfeiler durchlaufen.

STEIN_D = 0.30
LAGE = 0.25
FUGE = 0.014
KELLERFENSTER = (0.7, 1.3, 0.35, 0.75)     # in steinwand_2x1


def lagen_grenzen(hoehe, oeffnungen=()):
    g = [round(i * LAGE, 4) for i in range(int(round(hoehe / LAGE)) + 1)]
    for o in oeffnungen:
        for z in (o[2], o[3]):
            if 0.0 < z < hoehe:
                g.append(z)
    g = sorted(g)
    erg = [g[0]]
    for z in g[1:]:
        if z - erg[-1] < 0.1:
            if z in [o[2] for o in oeffnungen] + [o[3] for o in oeffnungen]:
                erg[-1] = z
            continue
        erg.append(z)
    if erg[-1] != hoehe:
        erg[-1] = hoehe
    return erg


def kaputt_hoehe(m, x, hoehe, saat):
    """Abgebrochene Oberkante: Höhe, bis zu der die Steine bei x noch stehen."""
    return hoehe * (0.55 + 0.25 * noise.noise(Vector((x * 1.4, saat, 0.5)))) + 0.15 * math.sin(x * 2.1 + saat)


def block(m, lx, ly, lz, fase, rauh, abgeschlagen):
    """Steinblock; mit m.leicht (Befestigung, lange Mauern) ohne Unterteilung: etwa ein Viertel der Dreiecke."""
    if getattr(m, "leicht", False):
        bm = quader(lx, ly, lz, fase=fase)
        verbiegen(bm, m.rnd, rauh, 0.25)
        bm.normal_update()
        return bm
    return klotz(m.rnd, lx, ly, lz, fase, rauh, abgeschlagen)


def stein(m, x0, x1, z0, z1, kaputt, tiefe=STEIN_D, teilen=True, yc=0.0):
    """Bruchstein: unregelmäßig behauen, manchmal zwei flache Steine übereinander (kein Ziegel-Look)."""
    if teilen and z1 - z0 > 0.2 and x1 - x0 < 0.45 and m.rnd.random() < 0.3:
        zm = z0 + (z1 - z0) * m.rnd.uniform(0.4, 0.6)
        stein(m, x0, x1, z0, zm, kaputt, tiefe, False, yc); stein(m, x0, x1, zm, z1, kaputt, tiefe, False, yc)
        return
    bm = block(m, x1 - x0 - FUGE, tiefe - m.rnd.uniform(0.0, 0.03), z1 - z0 - FUGE, 0.03, 0.018,
               0.8 if kaputt else 0.45)
    m.teil(bm, "stein", M(((x0 + x1) / 2, yc + m.rnd.uniform(-0.008, 0.008), (z0 + z1) / 2),
                          (m.rnd.uniform(-1.5, 1.5), 0, m.rnd.uniform(-1, 1))))


def kern(m, x0, x1, z0, z1, tiefe=STEIN_D - 0.035):
    """Mörtel hinter den Steinen (sieht man in den Fugen)."""
    if x1 - x0 > 0.01 and z1 - z0 > 0.01:
        z1 = z1 - 0.03 if z1 > z0 + 0.1 else z1              # oben unter den Steinen versteckt
        m.teil(quader(x1 - x0, tiefe, z1 - z0), "stein", M(((x0 + x1) / 2, 0, (z0 + z1) / 2)))


def steinwand(m, kaputt, breite, hoehe, oeffnungen=()):
    xa, xb = STEIN_D / 2, breite - STEIN_D / 2
    saat = m.rnd.uniform(0, 50)
    lagen = lagen_grenzen(hoehe, oeffnungen)
    unterste_luecke = hoehe
    for j, (z0, z1) in enumerate(zip(lagen, lagen[1:])):
        stuecke = [(xa, xb)]
        sturz = None
        for o in oeffnungen:
            if z0 < o[3] - 1e-6 and z1 > o[2] + 1e-6:
                stuecke = [s for a, b in stuecke for s in ((a, o[0]), (o[1], b)) if s[1] - s[0] > 0.02]
            elif abs(z0 - o[3]) < 1e-6:
                sturz = (max(xa, o[0] - 0.18), min(xb, o[1] + 0.18))
        for a, b in stuecke:
            # Fugen versetzt: jede zweite Lage beginnt mit einem halben Stein
            kanten = [a]
            x = a + (m.rnd.uniform(0.15, 0.25) if j % 2 else m.rnd.uniform(0.28, 0.5))
            while x < b - 0.18:
                if sturz and sturz[0] < x < sturz[1]:
                    x = sturz[1]
                    if x >= b - 0.05:
                        break
                kanten.append(x)
                x += m.rnd.uniform(0.22, 0.6)
            if sturz and a < sturz[0] < b and sturz[0] - a > 0.12 and sturz[0] not in kanten:
                kanten = sorted([k for k in kanten if not sturz[0] < k < sturz[1]] + [sturz[0]])
            kanten.append(b)
            for s0, s1 in zip(kanten, kanten[1:]):
                if kaputt and z1 > kaputt_hoehe(m, (s0 + s1) / 2, hoehe, saat):
                    unterste_luecke = min(unterste_luecke, z0)
                    continue
                stein(m, s0, s1, z0, z1, kaputt)
    # Mörtelkern: ohne Öffnungen, bei kaputt nur bis zur niedrigsten Bruchstelle
    top = hoehe if not kaputt else unterste_luecke
    if not oeffnungen:
        kern(m, xa, xb, 0.0, top)
    else:
        o = oeffnungen[0]
        kern(m, xa, o[0], 0.0, top); kern(m, o[1], xb, 0.0, top)
        kern(m, o[0], o[1], 0.0, min(o[2], top)); kern(m, o[0], o[1], o[3], top)


def steinwand_2x2(m, kaputt):
    steinwand(m, kaputt, 2.0, 2.0)


def steinwand_2x1(m, kaputt):
    steinwand(m, kaputt, 2.0, 1.0)


def steinwand_1x1(m, kaputt):
    steinwand(m, kaputt, 1.0, 1.0)


def steinwand_tuer(m, kaputt):
    """Steinwand 2 x 2 mit derselben Türöffnung wie wand_tuer (Türblatt tuer passt), Sturz aus einem langen Stein."""
    steinwand(m, kaputt, 2.0, 2.0, [TUER])
    rahmen(m, TUER, TUER_ZARGE, STEIN_D - 0.04, "holz" if not kaputt else "holz_alt", unten=False,
           bruch=("r",) if kaputt else ())


def steinwand_fenster(m, kaputt):
    """Steinwand 2 x 1 mit vergittertem Kellerfenster 0,6 x 0,4 m."""
    steinwand(m, kaputt, 2.0, 1.0, [KELLERFENSTER])
    x0, x1, z0, z1 = KELLERFENSTER
    for i in range(4):
        if kaputt and i == 2:
            continue
        x = x0 + (x1 - x0) * (i + 0.5) / 4
        m.stab((x, -0.06, z0 - 0.02), (x, -0.06, z1 + 0.02), 0.012, "eisen", seg=6, biegen=0.006 if kaputt else 0.0)
    m.stab((x0 - 0.02, -0.06, (z0 + z1) / 2), (x1 + 0.02, -0.06, (z0 + z1) / 2), 0.01, "eisen", seg=6, biegen=0.0)


def steinpfeiler(m, kaputt, hoehe):
    """Pfeiler 0,3 x 0,3 an einem Rasterpunkt (x, y -0,15..0,15), Steinlagen wie die Steinwand."""
    lagen = lagen_grenzen(hoehe)
    h = STEIN_D / 2
    for j, (z0, z1) in enumerate(zip(lagen, lagen[1:])):
        if kaputt and z1 > hoehe * 0.62 + (0.25 if j % 2 else 0.0):
            continue
        bm = klotz(m.rnd, STEIN_D - FUGE, STEIN_D - FUGE, z1 - z0 - FUGE, 0.03, 0.018, 0.8 if kaputt else 0.45)
        m.teil(bm, "stein", M((0, 0, (z0 + z1) / 2), (0, 0, 90 * (j % 2))))
    top = hoehe if not kaputt else min(z for z in lagen if z >= hoehe * 0.62 - 1e-6)
    m.teil(quader(STEIN_D - 0.035, STEIN_D - 0.035, max(0.05, (top - 0.25 if kaputt else top) - 0.03)), "stein",
           M((0, 0, ((top - 0.25 if kaputt else top) - 0.03) / 2)))


def steinpfeiler_2m(m, kaputt):
    steinpfeiler(m, kaputt, 2.0)


def steinpfeiler_1m(m, kaputt):
    steinpfeiler(m, kaputt, 1.0)


def steinboden(m, kaputt, b):
    """Steinplatten b x b (x 0..b, y 0..b) wie der Dielenboden: Oberkante 0,1 m über dem Rasterpunkt, 0,1 m dick."""
    n = max(2, round(b / 0.5))
    for i in range(n):
        versatz = 0.25 if i % 2 else 0.0
        kanten = [0.0] + [k for k in (j * 0.5 + versatz for j in range(1, int(b / 0.5) + 1)) if k < b - 0.1] + [b]
        y0, y1 = b * i / n, b * (i + 1) / n
        for x0, x1 in zip(kanten, kanten[1:]):
            if kaputt and noise.noise(Vector((x0 * 2.1, y0 * 2.1, 3.0))) > 0.25:
                continue
            bm = klotz(m.rnd, x1 - x0 - 0.012, y1 - y0 - 0.012, 0.1, 0.012, 0.004, 0.6 if kaputt else 0.05)
            m.teil(bm, "stein", M(((x0 + x1) / 2, (y0 + y1) / 2, 0.05 - m.rnd.uniform(0, 0.006))))
    m.teil(quader(b, b, 0.06), "stein", M((b / 2, b / 2, 0.03)))


def steinboden_2x2(m, kaputt):
    steinboden(m, kaputt, 2.0)


def steinboden_1x1(m, kaputt):
    steinboden(m, kaputt, 1.0)


VARIANTEN = {"bretter_2x2": bretter_2x2, "bretter_2x1": bretter_2x1, "bretter_1x1": bretter_1x1,
             "bretter_tuer": bretter_tuer, "tuer_alt": tuer_alt, "bretter_fenster": bretter_fenster, "bretter_dreieck": bretter_dreieck,
             "bretter_dreieck_1x1": bretter_dreieck_1x1, "dach_bretter_2x2": dach_bretter_2x2,
             "dach_bretter_2x1": dach_bretter_2x1, "dach_bretter_1x2": dach_bretter_1x2,
             "dach_bretter_1x1": dach_bretter_1x1,
             "steinwand_2x2": steinwand_2x2, "steinwand_2x1": steinwand_2x1, "steinwand_1x1": steinwand_1x1,
             "steinwand_tuer": steinwand_tuer, "steinwand_fenster": steinwand_fenster,
             "steinpfeiler_2m": steinpfeiler_2m, "steinpfeiler_1m": steinpfeiler_1m,
             "steinboden_2x2": steinboden_2x2, "steinboden_1x1": steinboden_1x1}



# ================================================================ Befestigung: Wehrmauern 3 m hoch, 1 m dick, Brüstungen
# Wehrmauer: belegt eine ganze Rasterreihe wie ein Boden: x 0..L, Tiefe y 0..1 (in Godot z 0..-1), z 0..3.
# Vorderseite (außen) bei y 0 – in Godot zeigt sie wie bei den Wänden nach +z. Oben ein begehbarer Wehrgang (Oberkante 3 m).
# Ecken: ein 1-m-Stück füllt die Eckzelle; alle Seiten sind verkleidet, Stücke stoßen nur aneinander.
# Brüstung: steht oben auf der Mauer an der Außenkante (y 0..0,3), 0,5 / 1 / 1,5 m hoch, 2 oder 1 m lang.
# Innen als Absturzsicherung: um 180° gedreht und eine Zelle weiter setzen (wie beim Boden).

FESTUNG_H = 3.0
FESTUNG_D = 1.0
SCHALE = 0.35          # Tiefe der Mauersteine außen und innen
BRUESTUNG_D = 0.3


def lage_steine(m, kaputt, xa, xb, z0, z1, j, tiefe, yc, steht=None):
    """Eine Steinlage von xa bis xb mit versetzten Fugen."""
    kanten = [xa]
    x = xa + (m.rnd.uniform(0.15, 0.3) if j % 2 else m.rnd.uniform(0.3, 0.5))
    while x < xb - 0.18:
        kanten.append(x); x += m.rnd.uniform(0.25, 0.6)
    kanten.append(xb)
    for s0, s1 in zip(kanten, kanten[1:]):
        if steht and not steht((s0 + s1) / 2, z1):
            continue
        stein(m, s0, s1, z0, z1, kaputt, tiefe, True, yc)


def platten(m, kaputt, x0, x1, y0, y1, oben, dicke=0.1, steht=None):
    """Abdeckplatten (Wehrgang, Mauerkrone) mit Oberkante oben."""
    nx = max(1, round((x1 - x0) / 0.5)); ny = max(1, round((y1 - y0) / 0.5))
    for i in range(ny):
        for k in range(nx):
            a = x0 + (x1 - x0) * k / nx; b = x0 + (x1 - x0) * (k + 1) / nx
            if i % 2 and nx > 1:
                a = max(x0, a - 0.25 * (x1 - x0) / nx); b = min(x1, b - 0.25 * (x1 - x0) / nx) if k < nx - 1 else x1
            c = y0 + (y1 - y0) * i / ny; d = y0 + (y1 - y0) * (i + 1) / ny
            if steht and not steht((a + b) / 2, oben):
                continue
            bm = block(m, b - a - 0.012, d - c - 0.012, dicke, 0.012, 0.005, 0.6 if kaputt else 0.1)
            m.teil(bm, "stein", M(((a + b) / 2, (c + d) / 2, oben - dicke / 2 - m.rnd.uniform(0, 0.005))))


def festung_stein(m, kaputt, L, H=FESTUNG_H, D=FESTUNG_D):
    m.leicht = True
    saat = m.rnd.uniform(0, 50)
    grenze = lambda x: H * (0.62 + 0.18 * noise.noise(Vector((x * 1.3, saat, 0.5)))) + 0.2 * math.sin(x * 2.3 + saat)
    steht = (lambda x, z: z <= grenze(x)) if kaputt else None
    lagen = lagen_grenzen(H - 0.1)
    for j, (z0, z1) in enumerate(zip(lagen, lagen[1:])):
        for yc in (SCHALE / 2, D - SCHALE / 2):                     # Außen- und Innenschale
            lage_steine(m, kaputt, 0.0, L, z0, z1, j + (1 if yc > 0.5 else 0), SCHALE, yc, steht)
        for xa, xb in ((0.0, 0.3), (L - 0.3, L)):                    # Stirnseiten (Ecken, offene Enden)
            if steht and not steht((xa + xb) / 2, z1):
                continue
            bm = block(m, D - 2 * SCHALE - FUGE, xb - xa - FUGE, z1 - z0 - FUGE, 0.03, 0.018, 0.8 if kaputt else 0.45)
            m.teil(bm, "stein", M(((xa + xb) / 2, D / 2, (z0 + z1) / 2), (0, 0, 90)))
    top = H - 0.12 if not kaputt else min(grenze(x / 10 * L) for x in range(11)) - 0.3
    m.teil(quader(L - 0.04, D - 0.06, max(0.2, top)), "stein", M((L / 2, D / 2, max(0.2, top) / 2)))
    if not kaputt:
        platten(m, kaputt, 0.0, L, 0.0, D, H)


def podest_stein(m, kaputt):
    """Steinpodest 1 x 1 (x 0..1, Tiefe nach -z wie ein Boden), Oberkante 1,1 m: bündig mit der obersten Stufe von
    treppe_stein/treppe_holz und dem Boden eines 1 m hohen Sockels. Treppe seitlich anbauen, Podest vor die Tür."""
    festung_stein(m, kaputt, 1.0, H=1.0 + BODEN_OBEN, D=1.0)


def podest_holz(m, kaputt):
    """Holzplattform 1 x 1 x 0,2 m: Rahmen aus Kanthölzern, Bohlen darauf, Oberkante 0,1 m über dem Rasterpunkt wie der
    Boden (auf Höhe 1 gesetzt also 1,1 m, wie die oberste Stufe). Stützen: balken_1m hochkant an die Ecken."""
    u, o = BODEN_OBEN - 0.2, BODEN_OBEN
    rahmen_h = 0.2 - 0.04
    for a, b in (((0.0, 0.05), (1.0, 0.05)), ((0.0, 0.95), (1.0, 0.95)), ((0.05, 0.1), (0.05, 0.9)), ((0.95, 0.1), (0.95, 0.9))):
        zm = u + rahmen_h / 2
        m.kantholz((a[0], a[1], zm), (b[0], b[1], zm), 0.1, rahmen_h, "holz" if not kaputt else "holz_alt",
                   oben=(0, 0, 1), biegen=0.0, bruch=1 if kaputt and a == (0.95, 0.1) else 0)
    m.kantholz((0.5, 0.1, u + rahmen_h / 2), (0.5, 0.9, u + rahmen_h / 2), 0.08, rahmen_h - 0.02, "holz",
               oben=(0, 0, 1), biegen=0.0)
    for i in range(5):
        if kaputt and i in (1, 3):
            if i == 3:
                m.brett(0.45, 0.196, 0.04, M((0.225, 0.1 + i * 0.2, o - 0.02)), "holz_verkohlt", bruch=1, biegen=0.0)
            continue
        m.brett(1.0, 0.196, 0.04, M((0.5, 0.1 + i * 0.2, o - 0.02)), "holz", biegen=0.0, fase=0.004)


def festung_stein_2m(m, kaputt):
    festung_stein(m, kaputt, 2.0)


def festung_stein_1m(m, kaputt):
    festung_stein(m, kaputt, 1.0)


def stamm(m, x, y, h, r, mat="holz_alt", spitz=False, kaputt=False):
    """Senkrechter Stamm bei (x, y) von 0 bis h, oben gerade abgesägt oder angespitzt."""
    if kaputt:
        h *= m.rnd.uniform(0.35, 0.75); spitz = False
    prof = [(r, 0.0), (r * 1.01, h * 0.5)]
    prof += [(r * 0.97, h - 0.35), (r * 0.45, h - 0.15), (0.012, h)] if spitz else [(r * 0.98, h)]
    bm = drehkoerper(prof, 10, True, True)
    if kaputt:
        oben = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            if abs(v.co.z - oben) < 1e-4:
                v.co.z += m.rnd.uniform(-0.1, 0.12)
    verbiegen(bm, m.rnd, 0.008, 0.5)
    m.teil(bm, mat, M((x, y, 0), (m.rnd.uniform(-0.8, 0.8), m.rnd.uniform(-0.8, 0.8), m.rnd.uniform(0, 360))),
           uv="zylz", r=r)


def festung_holz(m, kaputt, L):
    """Holz-Erde-Mauer: Stämme außen und innen (je 0,25 m), Stirnseiten aus Stämmen, oben Bohlen als Wehrgang."""
    H, D, r = FESTUNG_H, FESTUNG_D, 0.125
    def mat():
        return "holz_verkohlt" if kaputt and m.rnd.random() < 0.25 else "holz_alt"
    n = round(L / (2 * r))
    for i in range(n):
        x = r + i * 2 * r
        for y in (r, D - r):
            if kaputt and m.rnd.random() < 0.12:
                continue
            stamm(m, x, y, H - 0.06, r * m.rnd.uniform(0.94, 1.0), mat(), kaputt=kaputt and m.rnd.random() < 0.4)
    for x in (r, L - r):
        for y in (3 * r, 5 * r):
            stamm(m, x, y, H - 0.06, r * 0.98, mat(), kaputt=kaputt and m.rnd.random() < 0.4)
    # Füllung (Erde/Steine), unsichtbar zwischen den Stämmen
    m.teil(quader(L - 2 * r, D - 4 * r, H - 0.3), "stein", M((L / 2, D / 2, (H - 0.3) / 2)))
    # Wehrgang: Bohlen quer
    k = round(L / 0.2)
    for i in range(k):
        if kaputt and m.rnd.random() < 0.45:
            continue
        x = 0.1 + i * 0.2
        m.brett(D, 0.196, 0.05, M((x, D / 2, H - 0.025), (0, 0, 90)), "holz" if not kaputt else mat(), biegen=0.0,
                fase=0.004)


def festung_holz_2m(m, kaputt):
    festung_holz(m, kaputt, 2.0)


def festung_holz_1m(m, kaputt):
    festung_holz(m, kaputt, 1.0)


def bruestung_stein(m, kaputt, L, h):
    """Steinbrüstung 0,3 m dick an der Außenkante (y 0..0,3) mit Abdeckplatten. 1,5 m: unten 1 m geschlossen, darüber
    Zinnen (0,6 m breit, 0,4 m Lücke, im 1-m-Takt: setzen sich über die Stöße fort)."""
    m.leicht = True
    saat = m.rnd.uniform(0, 50)
    steht = (lambda x, z: z <= h * (0.55 + 0.3 * noise.noise(Vector((x * 1.7, saat, 0.2))))) if kaputt else None
    voll = h if h < 1.2 else 1.0
    lagen = lagen_grenzen(voll - 0.08)
    for j, (z0, z1) in enumerate(zip(lagen, lagen[1:])):
        lage_steine(m, kaputt, 0.0, L, z0, z1, j, BRUESTUNG_D, BRUESTUNG_D / 2, steht)
    m.teil(quader(L - 0.04, BRUESTUNG_D - 0.06, voll - 0.12), "stein", M((L / 2, BRUESTUNG_D / 2, (voll - 0.12) / 2)))
    if h < 1.2:
        platten(m, kaputt, 0.0, L, -0.02, BRUESTUNG_D + 0.02, h, 0.08, steht)
        return
    platten(m, kaputt, 0.0, L, -0.02, BRUESTUNG_D + 0.02, voll, 0.08, steht)
    for k in range(int(L)):
        a, b = k, k + 0.6
        if steht and not steht(a + 0.3, h):
            continue
        for j, (z0, z1) in enumerate(((voll, voll + 0.21), (voll + 0.21, h - 0.08))):
            lage_steine(m, kaputt, a, b, z0, z1, j, BRUESTUNG_D, BRUESTUNG_D / 2)
        platten(m, kaputt, a, b, -0.02, BRUESTUNG_D + 0.02, h, 0.08)


def bruestung_holz(m, kaputt, L, h):
    """Holzbrüstung: Stämme 0,2 m an der Außenkante, innen ein Riegel. 1,5 m: angespitzt wie eine Palisade."""
    r = 0.1
    for i in range(round(L / (2 * r))):
        if kaputt and m.rnd.random() < 0.2:
            continue
        stamm(m, r + i * 2 * r, r, h + (m.rnd.uniform(-0.04, 0.04) if h > 1.2 else 0.0), r * m.rnd.uniform(0.92, 1.0),
              "holz_verkohlt" if kaputt and m.rnd.random() < 0.3 else "holz_alt", spitz=h > 1.2,
              kaputt=kaputt and m.rnd.random() < 0.4)
    for z in ((h * 0.5,) if h < 0.8 else (0.3, min(h, 1.0) - 0.2)):
        x1 = L if not (kaputt and m.rnd.random() < 0.5) else L * m.rnd.uniform(0.3, 0.6)
        m.stab((0.02, 2 * r + 0.045, z), (x1 - 0.02, 2 * r + 0.045, z), 0.045, "holz_alt", biegen=0.004)


def bruestung_stein_05_2m(m, kaputt):
    bruestung_stein(m, kaputt, 2.0, 0.5)


def bruestung_stein_05_1m(m, kaputt):
    bruestung_stein(m, kaputt, 1.0, 0.5)


def bruestung_stein_10_2m(m, kaputt):
    bruestung_stein(m, kaputt, 2.0, 1.0)


def bruestung_stein_10_1m(m, kaputt):
    bruestung_stein(m, kaputt, 1.0, 1.0)


def bruestung_stein_15_2m(m, kaputt):
    bruestung_stein(m, kaputt, 2.0, 1.5)


def bruestung_stein_15_1m(m, kaputt):
    bruestung_stein(m, kaputt, 1.0, 1.5)


def bruestung_holz_05_2m(m, kaputt):
    bruestung_holz(m, kaputt, 2.0, 0.5)


def bruestung_holz_05_1m(m, kaputt):
    bruestung_holz(m, kaputt, 1.0, 0.5)


def bruestung_holz_10_2m(m, kaputt):
    bruestung_holz(m, kaputt, 2.0, 1.0)


def bruestung_holz_10_1m(m, kaputt):
    bruestung_holz(m, kaputt, 1.0, 1.0)


def bruestung_holz_15_2m(m, kaputt):
    bruestung_holz(m, kaputt, 2.0, 1.5)


def bruestung_holz_15_1m(m, kaputt):
    bruestung_holz(m, kaputt, 1.0, 1.5)


BEFESTIGUNG = {"podest_stein": podest_stein, "podest_holz": podest_holz, "festung_stein_2m": festung_stein_2m, "festung_stein_1m": festung_stein_1m, "festung_holz_2m": festung_holz_2m, "festung_holz_1m": festung_holz_1m, "bruestung_stein_05_2m": bruestung_stein_05_2m, "bruestung_stein_05_1m": bruestung_stein_05_1m, "bruestung_stein_10_2m": bruestung_stein_10_2m, "bruestung_stein_10_1m": bruestung_stein_10_1m, "bruestung_stein_15_2m": bruestung_stein_15_2m, "bruestung_stein_15_1m": bruestung_stein_15_1m, "bruestung_holz_05_2m": bruestung_holz_05_2m, "bruestung_holz_05_1m": bruestung_holz_05_1m, "bruestung_holz_10_2m": bruestung_holz_10_2m, "bruestung_holz_10_1m": bruestung_holz_10_1m, "bruestung_holz_15_2m": bruestung_holz_15_2m, "bruestung_holz_15_1m": bruestung_holz_15_1m}


# ================================================================ Holzgeländer (Philipp 26.11.)
# Geländer und Pfosten getrennt. Das Geländer läuft 0,10 m innen von der Rasterlinie und endet 0,05 m vor den
# Rasterpunkten (x 0,05..0,95, also an der Fläche einer Wand, die quer davor steht: kein Clipping, wirkt angeschraubt).
# gelaender_pfosten: Eckpfosten 10 x 10 cm in der Ecke NEBEN dem Rasterpunkt (x, y 0,05..0,15); Drehen um den
#   Rasterpunkt wählt die Ecke. Für Ecken und freie Enden: beide Geländer schließen bündig an seine Flächen an.
# gelaender_pfosten_mitte: Pfosten mittig auf dem Rasterpunkt (x -0,05..0,05) für Stöße in geraden Läufen.
# Unterkante auf dem Boden (0,1 m über dem Rasterpunkt), Handlauf 1 m über dem Boden.

GEL_INNEN = 0.10              # Mittellinie von Geländer und Pfosten, gemessen von der Rasterlinie
PFOSTEN_B = 0.10
GEL_HOEHE = 1.0


def gelaender_1m(m, kaputt):
    y = GEL_INNEN; x0 = PFOSTEN_B / 2; x1 = 1.0 - x0
    oben = BODEN_OBEN + GEL_HOEHE; unten = BODEN_OBEN + 0.08
    hl_d = 0.045; ul_d = 0.04
    if kaputt:   # Handlauf auf halber Länge abgebrochen und leicht abgesackt
        m.kantholz((x0, y, oben - hl_d / 2), (x0 + 0.5, y, oben - hl_d / 2 - 0.03), 0.07, hl_d, "holz_alt",
                   oben=(0, 0, 1), bruch=1)
    else:
        m.kantholz((x0, y, oben - hl_d / 2), (x1, y, oben - hl_d / 2), 0.07, hl_d, "holz", oben=(0, 0, 1), biegen=0.0)
    m.kantholz((x0, y, unten + ul_d / 2), (x1, y, unten + ul_d / 2), 0.05, ul_d, "holz" if not kaputt else "holz_alt",
               oben=(0, 0, 1), biegen=0.0)
    n = 8; abst = (x1 - x0) / (n + 1)
    for i in range(1, n + 1):
        x = x0 + i * abst
        z0 = unten + ul_d; z1 = oben - hl_d
        if kaputt:
            if i in (5, 8):
                continue
            if i == 7:          # abgebrochene Sprosse
                m.kantholz((x, y, z0), (x, y, z0 + 0.38), 0.03, 0.03, "holz_verkohlt", oben=(0, 1, 0), bruch=1)
                continue
            if x > x0 + 0.5:    # Handlauf fehlt hier: Sprossen abgebrochen, unterschiedlich lang
                m.kantholz((x, y, z0), (x, y, z0 + 0.35 + 0.3 * m.rnd.random()), 0.03, 0.03, "holz_alt",
                           oben=(0, 1, 0), bruch=1)
                continue
        m.kantholz((x, y, z0), (x, y, z1), 0.03, 0.03, "holz", oben=(0, 1, 0), fase=0.004, biegen=0.0)


def pfosten(m, kaputt, cx):
    c = GEL_INNEN; h = GEL_HOEHE + 0.05 if not kaputt else 0.62
    m.kantholz((cx, c, BODEN_OBEN), (cx, c, BODEN_OBEN + h), PFOSTEN_B, PFOSTEN_B, "holz" if not kaputt else "holz_alt",
               oben=(0, 1, 0), biegen=0.0, bruch=1 if kaputt else 0)
    if not kaputt:
        m.brett(0.12, 0.12, 0.025, M((cx, c, BODEN_OBEN + h + 0.0125)), "holz", biegen=0.0, fase=0.008)


def gelaender_pfosten(m, kaputt):
    """Eckpfosten 10 x 10 cm in der Ecke neben dem Rasterpunkt (x, y 0,05..0,15), 1,05 m hoch mit Kappe."""
    pfosten(m, kaputt, GEL_INNEN)


def gelaender_pfosten_mitte(m, kaputt):
    """Pfosten mittig auf dem Rasterpunkt (Stoß zweier Geländer in einer Linie)."""
    pfosten(m, kaputt, 0.0)


MODELLE = {"wand": wand, "wand_2x1": wand_2x1, "wand_1x1": wand_1x1, "balken_2m": balken_2m, "balken_1m": balken_1m,
           "strebe_2m": strebe_2m, "wand_tuer": wand_tuer, "tuer": tuer, "wand_fenster": wand_fenster,
           "wand_fenster_2x1": wand_fenster_2x1, "wand_fenster_1x1": wand_fenster_1x1, "wand_dreieck": wand_dreieck,
           "wand_dreieck_1x1": wand_dreieck_1x1, "boden_2x2": boden_2x2, "boden_1x1": boden_1x1,
           "dach_2x2": dach_2x2, "dach_2x1": dach_2x1, "dach_1x2": dach_1x2, "dach_1x1": dach_1x1,
           "dach_traufe": dach_traufe, "dach_first": dach_first, "dach_ortgang_l": dach_ortgang_l,
           "dach_ortgang_r": dach_ortgang_r, "dach_ortgang_1m_l": dach_ortgang_1m_l, "dach_ortgang_1m_r": dach_ortgang_1m_r,
           "dach_ecke_l": dach_ecke_l, "dach_ecke_r": dach_ecke_r, "dach_zier_l": dach_zier_l, "dach_zier_r": dach_zier_r,
           "dach_kehle_2x2": dach_kehle_2x2, "dach_kehle_1x1": dach_kehle_1x1, "dach_grat_2x2": dach_grat_2x2,
           "dach_grat_1x1": dach_grat_1x1, "dach_grat_traufe": dach_grat_traufe, "treppe_holz": treppe_holz, "treppe_stein": treppe_stein}

MODELLE.update(VARIANTEN)
MODELLE.update(BEFESTIGUNG)
MODELLE.update({"gelaender_1m": gelaender_1m, "gelaender_pfosten": gelaender_pfosten,
                "gelaender_pfosten_mitte": gelaender_pfosten_mitte})


if __name__ == "__main__":
    props.hauptprogramm(MODELLE)
